# SentinelOps technical guide

## System overview

SentinelOps converts incident tickets into structured investigation and remediation plans. Each report includes a likely root cause, confidence score, supporting runbook IDs and a fixed action plan. Mutating plans pause for an operator decision. Approved actions produce durable simulation receipts; rejected plans execute nothing.

For example, an HTTP 502 ticket passes through redaction, classification and retrieval before the agent proposes an upstream-health investigation. The operator can inspect the evidence and plan in the incident console, then approve or reject it. The same pending approval can be resumed after an application restart.

## Incident lifecycle

1. `app/main.py` validates the request and assigns a UUID thread. A service lock serializes graph, approval and indexing operations in the single-worker deployment.
2. `app/guardrails/pii_scrubber.py` removes covered credentials and identifiers before the first checkpoint. The graph checks the sanitized input again; originals are not retained in a reversible map.
3. `app/graph/workflow.py` routes classification and query generation to the fast model. Deterministic demo mode uses explicit test rules instead.
4. `app/retrieval/hybrid_store.py` searches dense and sparse Qdrant vectors, fuses eight candidates and reranks to three. Real retrieval uses FastEmbed, BM25 and FlashRank.
5. The synthesis model returns a Pydantic-validated `IncidentReport`. Code checks that citations come from retrieved evidence and commands belong to the cited runbooks' action registry.
6. Confidence below 0.75 or missing/invalid citations triggers up to two query rewrites. Continued uncertainty ends in escalation with no executable plan.
7. `human_approval_gate` pauses through LangGraph `interrupt()`. SQLite retains the workflow until `/approve/{thread_id}` supplies an explicit approval or rejection.
8. `execute_remediation` records approved simulation actions. A deterministic thread/action key prevents duplicate receipts when execution is replayed.

## Design decisions

### Retrieval preserves operational identifiers

Semantic search handles paraphrased symptoms, while BM25 captures literal identifiers such as `0x80070005`, `OOMKilled` and `HTTP 502`. Reciprocal rank fusion combines those signals, and a cross-encoder reranks the candidates. Markdown header chunks preserve complete diagnostic procedures and include runbook metadata and allowed actions.

### Model routing separates tasks

Classification and query rewriting use `gpt-4o-mini`; report synthesis uses `gpt-4o`. This separates short classification work from evidence-heavy generation. Cost savings depend on measured token usage, retry rates and model pricing.

### Approval is part of execution control

The model cannot waive approval for a mutating action. The action registry determines which commands require review. Approval and execution occupy separate graph nodes because LangGraph replays the interrupting node on resume. No infrastructure effects occur in that replayed node.

### Persistence supports recovery

SQLite checkpoints retain thread state and pending approvals. Execution receipts use an independent SQLite connection so a receipt commit cannot end a background checkpoint transaction. Idempotency reconciles execution-node replay with already-recorded receipts. The default deployment uses one worker; horizontal scaling requires shared persistence and distributed approval claims.

## Components

| Component | Responsibility |
|---|---|
| FastAPI | Validated HTTP contracts, incident console, authentication option and readiness |
| LangGraph | Stateful transitions, bounded correction loop, interruption and resume |
| Qdrant | Named dense/sparse vectors and fused retrieval |
| FastEmbed / FlashRank | Local embeddings, BM25 vectors and reranking |
| Pydantic | Strict ticket, report, approval and execution contracts |
| SQLite | Checkpoints and durable execution receipts |
| Langfuse | Optional transition metadata without incident payloads |
| Docker / uv | Container delivery and locked dependency installation |

## Execution modes

The default launcher uses deterministic generation and test retrieval vectors for a free, reproducible demo. Qdrant storage, workflow persistence, approval and execution-receipt behavior remain active.

`MOCK_LLM=true RETRIEVAL_BACKEND=fastembed` enables real local embedding and reranking models with deterministic generation. `MOCK_LLM=false` enables the configured OpenAI models and requires an API key. All modes use the simulation executor; there is no switch that enables arbitrary shell or cloud mutations.

The knowledge base includes 15 synthetic runbooks and a 20-ticket golden set. Each golden case specifies expected runbook IDs and remediation ground truth.

## Run and inspect a workflow

Start the incident console with `bash start.sh` on Mac/Linux or `start.cmd` on Windows. Select an example, analyze the incident, inspect the redacted ticket and cited report, then approve or reject the proposed simulation.

For terminal output, run:

```bash
MOCK_LLM=true uv run python scripts/demo_run.py
```

The demo prints ingestion results, redacted input, the RCA, an empty execution log at the approval pause and simulation receipts after resume. The API exposes sanitized checkpoint state at `/threads/{thread_id}`.

## Validation and deployment

The offline suite covers redaction, exact-code retrieval, grounding retries, invalid plans, approval/rejection, restart/resume, transaction isolation and replay idempotency. Separate checks exercise real retrieval, the browser console, native startup and the Docker stack. Paid DeepEval metrics are opt-in and have not yet been measured. Detailed results are in [VERIFICATION.md](VERIFICATION.md).

Production integration requires organization-specific authentication, reviewer roles, per-thread authorization, retention controls and reviewed execution adapters. External execution needs scoped credentials, plan-bound approval, provider-side idempotency and recovery verification. Deployment details are in [OPERATIONS.md](OPERATIONS.md).
