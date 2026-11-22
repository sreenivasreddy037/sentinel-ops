import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.retrieval.hybrid_store import HybridStore


@pytest.fixture(autouse=True)
def isolate_settings_environment(monkeypatch):
    # Do not let a developer's server, keys or telemetry settings change offline tests.
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None, mock_llm=True, retrieval_backend="mock", qdrant_mode="memory",
        auto_ingest=False,
        checkpoint_path=str(tmp_path / "checkpoints.sqlite"), use_presidio=False,
        langfuse_public_key="", langfuse_secret_key=None, api_token=None,
    )


@pytest.fixture
def store(settings):
    instance = HybridStore(settings)
    instance.ingest()
    yield instance
    instance.close()


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as instance:
        response = instance.post("/ingest")
        assert response.status_code == 200
        yield instance
