"""Public and model-facing Pydantic v2 contracts."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Severity = Literal["P1", "P2", "P3", "P4"]
Category = Literal["linux", "aws", "network", "kubernetes", "identity", "unknown"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TicketInput(StrictModel):
    text: str = Field(min_length=8, max_length=16000)
    thread_id: str | None = None

    @field_validator("thread_id")
    @classmethod
    def valid_thread_id(cls, value):
        if value is not None:
            return str(UUID(value))
        return value

    @field_validator("text")
    @classmethod
    def non_blank(cls, value):
        if not value.strip():
            raise ValueError("Ticket cannot be blank")
        return value.strip()


class Classification(StrictModel):
    severity: Severity
    category: Category
    search_queries: list[str] = Field(min_length=1, max_length=3)


class RetrievedDocument(StrictModel):
    id: str
    runbook_id: str
    title: str
    text: str
    score: float


class IncidentReport(StrictModel):
    root_cause: str = Field(min_length=5, max_length=6000)
    confidence_score: float = Field(ge=0, le=1)
    cited_runbook_ids: list[str] = Field(max_length=10)
    proposed_commands: list[str] = Field(max_length=8)
    requires_approval: bool


class ApprovalDecision(StrictModel):
    approved: bool
    reviewer_note: str = Field(default="", max_length=2000)


class ExecutionRecord(StrictModel):
    action_id: str
    command: str
    mutating: bool
    mode: Literal["simulation"] = "simulation"
    result: str
    idempotency_key: str


class TriageResult(StrictModel):
    thread_id: str
    status: Literal["completed", "awaiting_approval", "denied", "escalated"]
    report: IncidentReport
    severity: Severity
    category: Category
    retry_count: int
    execution_log: list[ExecutionRecord]
