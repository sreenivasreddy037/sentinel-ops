"""FastAPI service. Single worker, serialized SQLite operations, optional bearer auth."""

import asyncio
import logging
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from threading import RLock
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from pydantic import ValidationError

from app.config import Settings
from app.graph.workflow import Workflow
from app.retrieval.hybrid_store import HybridStore
from app.schemas import ApprovalDecision, TicketInput, TriageResult
from app.telemetry import Telemetry
from app.tools.remediation import SimulationExecutor

logger = logging.getLogger(__name__)


class IncidentService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.lock = RLock()
        if settings.checkpoint_path != ":memory:":
            Path(settings.checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(settings.checkpoint_path, check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA busy_timeout=5000")
        self.saver = SqliteSaver(self.connection)
        self.store = HybridStore(settings)
        self.workflow = Workflow(settings, self.store, self.saver, SimulationExecutor(self.connection))
        self.graph = self.workflow.graph
        self.telemetry = Telemetry(settings)

    def close(self):
        self.telemetry.close()
        self.store.close()
        self.connection.close()

    @staticmethod
    def config(thread_id):
        try:
            thread_id = str(UUID(thread_id))
        except ValueError as error:
            raise HTTPException(422, "thread_id must be a UUID") from error
        return {"configurable": {"thread_id": thread_id}, "recursion_limit": 40}

    def inspect(self, thread_id):
        snapshot = self.graph.get_state(self.config(thread_id))
        if not snapshot.values:
            raise HTTPException(404, "Thread not found")
        return snapshot

    def result(self, thread_id):
        snapshot = self.inspect(thread_id)
        state = snapshot.values
        status = "awaiting_approval" if snapshot.next else (
            state["approval_status"] if state["approval_status"] in {"denied", "escalated"} else "completed"
        )
        return TriageResult(
            thread_id=thread_id, status=status, report=state["report"], severity=state["severity"],
            category=state["category"], retry_count=state["retry_count"],
            execution_log=state["execution_log"],
        )

    def run(self, ticket: TicketInput):
        thread_id = ticket.thread_id or str(uuid4())
        config = self.config(thread_id)
        with self.lock:
            if self.graph.get_state(config).values:
                raise HTTPException(409, "Thread already exists; create a new thread or inspect it")
            if not self.store.ready():
                raise HTTPException(409, "Knowledge base is empty; call POST /ingest")
            start = time.monotonic()
            self.graph.invoke(self.workflow.initial_state(thread_id, ticket.text), config)
            result = self.result(thread_id)
            self.telemetry.record(thread_id, result.status, result.retry_count,
                                  (time.monotonic() - start) * 1000)
            return result

    def approve(self, thread_id, decision: ApprovalDecision):
        with self.lock:
            snapshot = self.inspect(thread_id)
            if snapshot.next != ("human_approval_gate",):
                raise HTTPException(409, "Thread is not awaiting approval")
            # Sanitize BEFORE Command(resume=...) is checkpointed, not only in the node.
            from app.guardrails.pii_scrubber import scrub

            decision = decision.model_copy(update={
                "reviewer_note": scrub(decision.reviewer_note, self.settings.use_presidio).text
            })
            self.graph.invoke(Command(resume=decision.model_dump()), self.config(thread_id))
            result = self.result(thread_id)
            self.telemetry.record(thread_id, result.status, result.retry_count, 0.0)
            return result


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(api):
        service = IncidentService(settings or Settings())
        api.state.service = service
        try:
            if service.settings.auto_ingest:
                # Qdrant can need a few seconds after Compose starts its container.
                for attempt in range(service.settings.startup_attempts):
                    try:
                        await asyncio.to_thread(service.store.ingest)
                        break
                    except Exception:
                        if attempt + 1 == service.settings.startup_attempts:
                            raise
                        logger.warning("Knowledge store not ready; retrying startup")
                        await asyncio.sleep(min(2 ** attempt, 5))
            yield
        finally:
            service.close()

    api = FastAPI(title="SentinelOps", version="0.1.0", lifespan=lifespan)
    static_dir = Path(__file__).resolve().parent / "static"
    api.mount("/static", StaticFiles(directory=static_dir), name="static")

    @api.get("/", include_in_schema=False)
    def dashboard():
        return FileResponse(static_dir / "index.html", headers={
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; "
                                       "img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'",
            "X-Content-Type-Options": "nosniff",
        })

    @api.get("/ready")
    def readiness(request: Request):
        svc = request.app.state.service
        with svc.lock:
            try:
                ready = svc.store.ready()
            except Exception:
                ready = False
        return JSONResponse(status_code=200 if ready else 503, content={
            "status": "ready" if ready else "not_ready",
            "execution_mode": "simulation", "mock_llm": svc.settings.mock_llm,
            "retrieval_backend": svc.settings.retrieval_backend,
        })

    @api.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # FastAPI's default validation detail can echo raw credentials in `input`.
        details = [{"loc": error["loc"], "type": error["type"], "msg": "Invalid input"}
                   for error in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": details})

    @api.exception_handler(Exception)
    async def internal_error(request, exc):
        logger.error("Incident processing failed: %s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": "Processing failed; inspect thread or retry later"})

    def service(request: Request):
        svc = request.app.state.service
        token = svc.settings.api_token
        if token and token.get_secret_value():
            supplied = request.headers.get("authorization", "")
            if not secrets.compare_digest(supplied, f"Bearer {token.get_secret_value()}"):
                raise HTTPException(401, "Valid bearer token required", headers={"WWW-Authenticate": "Bearer"})
        return svc

    @api.get("/health")
    def health(request: Request):
        svc = request.app.state.service
        return {"status": "ok", "execution_mode": "simulation", "mock_llm": svc.settings.mock_llm,
                "retrieval_backend": svc.settings.retrieval_backend}

    @api.post("/ingest")
    def ingest(svc=Depends(service)):
        with svc.lock:
            return svc.store.ingest()

    @api.post("/triage", response_model=TriageResult)
    def triage(ticket: TicketInput, svc=Depends(service)):
        try:
            return svc.run(ticket)
        except ValidationError as error:
            raise HTTPException(502, "Model returned an invalid structured report") from error

    @api.post("/approve/{thread_id}", response_model=TriageResult)
    def approve(thread_id: str, decision: ApprovalDecision, svc=Depends(service)):
        return svc.approve(thread_id, decision)

    @api.get("/threads/{thread_id}")
    def inspect(thread_id: str, svc=Depends(service)):
        with svc.lock:
            snapshot = svc.inspect(thread_id)
            return {"thread_id": thread_id, "next": list(snapshot.next), "state": snapshot.values}

    return api


app = create_app()
