import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.main import create_app

TICKET = "Production outage: HTTP 502 Bad Gateway from alice@example.test at 192.168.1.2 password=private"


def test_pause_approve_resume(client):
    paused = client.post("/triage", json={"text": TICKET})
    assert paused.status_code == 200
    data = paused.json()
    assert data["status"] == "awaiting_approval"
    assert data["report"]["cited_runbook_ids"] == ["RB-NET-002"]
    assert data["execution_log"] == []
    thread = data["thread_id"]
    state = client.get(f"/threads/{thread}").json()
    assert state["next"] == ["human_approval_gate"]
    service = client.app.state.service
    assert service.connection.execute("SELECT count(*) FROM execution_receipts").fetchone()[0] == 0
    resumed = client.post(f"/approve/{thread}", json={"approved": True, "reviewer_note": "Reviewed"})
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "completed"
    assert len(resumed.json()["execution_log"]) == 2
    assert all(record["mode"] == "simulation" for record in resumed.json()["execution_log"])
    assert client.get(f"/threads/{thread}").json()["next"] == []
    assert client.post(f"/approve/{thread}", json={"approved": True}).status_code == 409


def test_denial_executes_nothing(client):
    thread = client.post("/triage", json={"text": TICKET}).json()["thread_id"]
    result = client.post(f"/approve/{thread}", json={"approved": False}).json()
    assert result["status"] == "denied"
    assert result["execution_log"] == []
    count = client.app.state.service.connection.execute("SELECT count(*) FROM execution_receipts").fetchone()[0]
    assert count == 0


def test_all_checkpoints_and_resume_payloads_are_redacted(client):
    thread = client.post("/triage", json={"text": TICKET}).json()["thread_id"]
    client.post(f"/approve/{thread}", json={"approved": True, "reviewer_note": "password=reviewsecret"})
    service = client.app.state.service
    history = [snapshot.values for snapshot in service.graph.get_state_history(service.config(thread))]
    dump = json.dumps(history)
    for forbidden in ["alice@example.test", "192.168.1.2", "password=private", "reviewsecret"]:
        assert forbidden not in dump
    assert "[REDACTED" in dump
    # Includes pending resume writes, not just graph state values.
    database_dump = "\n".join(service.connection.iterdump())
    for secret in ["alice@example.test", "reviewsecret", "password=private"]:
        assert secret.encode().hex() not in database_dump.lower()
        assert secret not in database_dump


def test_restart_retains_pending_approval(settings):
    with TestClient(create_app(settings)) as first:
        first.post("/ingest")
        thread = first.post("/triage", json={"text": TICKET}).json()["thread_id"]
    with TestClient(create_app(settings)) as second:
        assert second.get(f"/threads/{thread}").json()["next"] == ["human_approval_gate"]
        result = second.post(f"/approve/{thread}", json={"approved": True})
        assert result.status_code == 200
        assert result.json()["status"] == "completed"


def test_competing_approvals_cannot_duplicate_actions(client):
    thread = client.post("/triage", json={"text": TICKET}).json()["thread_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(
            lambda _: client.post(f"/approve/{thread}", json={"approved": True}).status_code,
            range(2),
        ))
    assert sorted(responses) == [200, 409]
    service = client.app.state.service
    assert service.connection.execute("SELECT count(*) FROM execution_receipts").fetchone()[0] == 2


def test_validation_and_missing_threads(client):
    assert client.get("/health").json()["execution_mode"] == "simulation"
    assert client.get(f"/threads/{uuid4()}").status_code == 404
    assert client.get("/threads/not-a-uuid").status_code == 422
    assert client.post("/triage", json={"text": "x"}).status_code == 422
    assert client.post("/triage", json={"text": TICKET, "extra": "no"}).status_code == 422
    assert client.post(f"/approve/{uuid4()}", json={"approved": "true"}).status_code == 422
    error = client.post("/triage", json={"text": "password=private", "thread_id": "secret"})
    assert "private" not in error.text
    assert "secret" not in error.text


def test_duplicate_thread_is_conflict(client):
    thread = str(uuid4())
    assert client.post("/triage", json={"text": TICKET, "thread_id": thread}).status_code == 200
    assert client.post("/triage", json={"text": TICKET, "thread_id": thread}).status_code == 409


def test_empty_knowledge_base_requires_ingestion(settings):
    with TestClient(create_app(settings)) as fresh:
        assert fresh.post("/triage", json={"text": TICKET}).status_code == 409


def test_optional_bearer_auth(settings):
    secured = settings.model_copy(update={"api_token": SecretStr("demo-test-token")})
    with TestClient(create_app(secured)) as instance:
        assert instance.get("/health").status_code == 200
        assert instance.post("/ingest").status_code == 401
        assert instance.post("/ingest", headers={"Authorization": "Bearer demo-test-token"}).status_code == 200
