"""Reproducible end-to-end API demo with no real infrastructure mutation."""

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# Support the requested `uv run python scripts/demo_run.py` invocation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def show(label, data):
    print(f"\n{label}\n{json.dumps(data, indent=2)}")


def main():
    with TemporaryDirectory(prefix="sentinel-demo-") as directory:
        settings = Settings(
            checkpoint_path=str(Path(directory) / "checkpoints.sqlite"), qdrant_mode="memory",
            api_token=None, langfuse_public_key="", langfuse_secret_key=None,
        )
        with TestClient(create_app(settings)) as client:
            indexed = client.post("/ingest")
            indexed.raise_for_status()
            show("1. Knowledge ingestion", indexed.json())
            response = client.post("/triage", json={
                "text": "Production outage HTTP 502 Bad Gateway after deployment. "
                        "Contact alice@example.test; host 10.10.0.8; password=demo-secret "
                        "AWS key " + "AKIA" + "X" * 16,
            })
            response.raise_for_status()
            paused = response.json()
            thread = paused["thread_id"]
            state = client.get(f"/threads/{thread}").json()["state"]
            show("2. Redacted input (original never checkpointed)", state["scrubbed_ticket"])
            show("3. Cited RCA and planned commands", paused["report"])
            show("4. HITL pause", {"status": paused["status"], "execution_log": paused["execution_log"]})
            assert paused["status"] == "awaiting_approval", paused
            assert paused["execution_log"] == []
            resumed = client.post(f"/approve/{thread}", json={
                "approved": True, "reviewer_note": "Demo operator reviewed the sandbox plan",
            })
            resumed.raise_for_status()
            result = resumed.json()
            show("5. Approved resume: sandbox simulation receipts", result)
            assert result["status"] == "completed"
            assert any(record["mutating"] for record in result["execution_log"])
            print("\nDemo verified: no command ran before approval; no infrastructure changed.")


if __name__ == "__main__":
    main()
