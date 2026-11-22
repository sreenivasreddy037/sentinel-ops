import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.retrieval.hybrid_store import HybridStore
from scripts import start


def test_first_start_is_ready_without_manual_ingestion(settings):
    automatic = settings.model_copy(update={"auto_ingest": True})
    with TestClient(create_app(automatic)) as client:
        assert client.get("/ready").json()["status"] == "ready"
        result = client.post("/triage", json={"text": "Production outage HTTP 502 Bad Gateway"})
        assert result.status_code == 200
        assert result.json()["status"] == "awaiting_approval"


def test_empty_store_is_not_ready(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503


def test_dashboard_and_assets_are_self_contained(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "SentinelOps" in page.text and 'id="approve"' in page.text
    assert "default-src 'self'" in page.headers["content-security-policy"]
    assert client.get("/static/style.css").status_code == 200
    javascript = client.get("/static/app.js")
    assert javascript.status_code == 200
    assert "innerHTML" not in javascript.text
    assert "localStorage" not in javascript.text


def test_auto_ingest_retries_dependency_startup(settings, monkeypatch):
    original = HybridStore.ingest
    attempts = []

    def briefly_unavailable(store):
        attempts.append(1)
        if len(attempts) == 1:
            raise ConnectionError("Qdrant is starting")
        return original(store)

    async def no_wait(seconds):
        return None

    monkeypatch.setattr(HybridStore, "ingest", briefly_unavailable)
    monkeypatch.setattr("app.main.asyncio.sleep", no_wait)
    with TestClient(create_app(settings.model_copy(update={"auto_ingest": True}))) as client:
        assert client.get("/ready").status_code == 200
        assert len(attempts) == 2


def test_launcher_demo_stays_free_and_uses_frozen_dependencies(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-value")
    monkeypatch.setenv("RETRIEVAL_BACKEND", "fastembed")
    monkeypatch.setattr(start, "ROOT", tmp_path)
    monkeypatch.setattr(start, "TOOLS", tmp_path / ".tools")
    monkeypatch.setattr(start, "portable_python", lambda: None)
    monkeypatch.setattr(start, "uv_binary", lambda: "uv")
    monkeypatch.setattr(start, "run", lambda command, env: commands.append((command, env.copy())))
    start.main(["--install-only"])
    assert commands[1][0] == ["uv", "sync", "--frozen", "--no-dev"]
    assert all(env["MOCK_LLM"] == "true" and env["RETRIEVAL_BACKEND"] == "mock"
               and env["OPENAI_API_KEY"] == "" for _, env in commands)
    assert all(env["QDRANT_MODE"] == "local" for _, env in commands)


def test_prepared_runtime_rejects_wrong_platform(monkeypatch, tmp_path):
    tools = tmp_path / ".tools"
    python = tools / "python-runtime/bin/python3.12"
    python.parent.mkdir(parents=True)
    python.touch()
    (tools / "runtime-manifest.json").write_text(json.dumps({"system": "WrongOS", "machine": "wrong"}))
    monkeypatch.setattr(start, "TOOLS", tools)
    with pytest.raises(RuntimeError, match="different OS/CPU"):
        start.portable_python()
