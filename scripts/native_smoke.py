"""Launch like a first-time user, verify the dashboard and approve a fresh incident."""

import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.container_smoke import post  # noqa: E402


def main():
    from scripts import container_smoke

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    container_smoke.BASE = url
    environment = os.environ.copy()
    environment.pop("API_TOKEN", None)
    environment["API_TOKEN"] = ""
    log_path = ROOT / "native-smoke.log"
    with log_path.open("w+") as log:
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts/start.py"), "--no-browser", "--port", str(port)],
            cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        try:
            for _ in range(120):
                if process.poll() is not None:
                    raise RuntimeError("Launcher exited before the service became ready")
                try:
                    with urllib.request.urlopen(url + "/ready", timeout=2) as response:
                        if response.status == 200:
                            break
                except (OSError, urllib.error.URLError):
                    time.sleep(1)
            else:
                raise RuntimeError("Readiness timed out")
            with urllib.request.urlopen(url, timeout=5) as response:
                assert "SentinelOps" in response.read().decode()
            # Deliberately no POST /ingest: first-start readiness includes the knowledge base.
            paused = post("/triage", {"text": "Production outage: HTTP 502 Bad Gateway after deployment"})
            assert paused["status"] == "awaiting_approval", paused
            assert paused["execution_log"] == []
            result = post(f"/approve/{paused['thread_id']}", {"approved": True})
            assert result["status"] == "completed", result
            print("PASS: native first-start install, dashboard, automatic indexing and approval lifecycle")
        except Exception:
            log.flush()
            print(log_path.read_text())
            raise
        finally:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            else:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
