"""stdlib HTTP smoke check against the real API/Qdrant Compose stack."""

import json
import os
import urllib.request

BASE = os.getenv("SENTINEL_URL", "http://127.0.0.1:8000")


def post(path, body):
    headers = {"Content-Type": "application/json"}
    if os.getenv("API_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["API_TOKEN"]
    request = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def main():
    with urllib.request.urlopen(BASE + "/ready", timeout=15) as response:
        assert json.load(response)["status"] == "ready"
    with urllib.request.urlopen(BASE, timeout=15) as response:
        assert "SentinelOps" in response.read().decode()
    assert post("/ingest", {})["runbooks"] == 15
    paused = post("/triage", {"text": "Production outage HTTP 502 Bad Gateway after a release"})
    assert paused["status"] == "awaiting_approval", paused
    assert paused["execution_log"] == []
    completed = post(f"/approve/{paused['thread_id']}", {"approved": True, "reviewer_note": "CI sandbox"})
    assert completed["status"] == "completed", completed
    assert len(completed["execution_log"]) == 2
    print("PASS: container ingestion, real server Qdrant fusion, pause and approval resume")


if __name__ == "__main__":
    main()
