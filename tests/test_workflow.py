from app.schemas import IncidentReport
from app.tools.remediation import BY_COMMAND


LOW = IncidentReport(
    root_cause="Insufficient evidence for a diagnosis", confidence_score=0.4,
    cited_runbook_ids=[], proposed_commands=[], requires_approval=False,
)
TICKET = "Production outage: HTTP 502 Bad Gateway after a backend deployment"


def test_self_correction_can_recover(client, monkeypatch):
    router = client.app.state.service.workflow.router
    original = router.synthesize
    calls = []

    def synthesize(state):
        calls.append(state["retry_count"])
        return LOW.model_copy() if len(calls) < 3 else original(state)

    monkeypatch.setattr(router, "synthesize", synthesize)
    response = client.post("/triage", json={"text": TICKET}).json()
    assert calls == [0, 1, 2]
    assert response["retry_count"] == 2
    assert response["status"] == "awaiting_approval"
    assert response["execution_log"] == []


def test_retry_exhaustion_escalates_without_executing(client, monkeypatch):
    monkeypatch.setattr(client.app.state.service.workflow.router, "synthesize", lambda state: LOW)
    result = client.post("/triage", json={"text": TICKET}).json()
    assert result["status"] == "escalated"
    assert result["retry_count"] == 2
    assert result["execution_log"] == []
    assert result["report"]["proposed_commands"] == []
    assert client.post(f"/approve/{result['thread_id']}", json={"approved": True}).status_code == 409


def test_unknown_issue_escalates(client):
    result = client.post("/triage", json={"text": "The quantum printer flickers purple intermittently"}).json()
    assert result["status"] == "escalated"
    assert result["execution_log"] == []


def test_model_cannot_disable_mutation_approval(client, monkeypatch):
    router = client.app.state.service.workflow.router
    original = router.synthesize

    def false_claim(state):
        return original(state).model_copy(update={"requires_approval": False})

    monkeypatch.setattr(router, "synthesize", false_claim)
    result = client.post("/triage", json={"text": TICKET}).json()
    assert result["status"] == "awaiting_approval"
    assert result["report"]["requires_approval"] is True


def test_unknown_command_is_rejected_even_with_valid_citation(client, monkeypatch):
    report = IncidentReport(
        root_cause="An upstream failed", confidence_score=0.99,
        cited_runbook_ids=["RB-NET-002"], proposed_commands=["rm -rf /"], requires_approval=False,
    )
    monkeypatch.setattr(client.app.state.service.workflow.router, "synthesize", lambda state: report)
    result = client.post("/triage", json={"text": TICKET}).json()
    assert result["status"] == "escalated"
    assert result["report"]["confidence_score"] == 0
    assert not result["execution_log"]


def test_fabricated_citations_escalate(client, monkeypatch):
    report = LOW.model_copy(update={"confidence_score": 0.99, "cited_runbook_ids": ["FAKE-42"]})
    monkeypatch.setattr(client.app.state.service.workflow.router, "synthesize", lambda state: report)
    result = client.post("/triage", json={"text": TICKET}).json()
    assert result["status"] == "escalated"


def test_read_only_plan_completes_without_interrupt(client, monkeypatch):
    diagnostic = next(a for a in BY_COMMAND.values() if a.runbook_id == "RB-NET-002" and not a.mutating)
    report = IncidentReport(
        root_cause="Inspect upstream health before determining root cause", confidence_score=0.9,
        cited_runbook_ids=["RB-NET-002"], proposed_commands=[diagnostic.command], requires_approval=False,
    )
    monkeypatch.setattr(client.app.state.service.workflow.router, "synthesize", lambda state: report)
    result = client.post("/triage", json={"text": TICKET}).json()
    assert result["status"] == "completed"
    assert len(result["execution_log"]) == 1
    assert result["execution_log"][0]["mutating"] is False
