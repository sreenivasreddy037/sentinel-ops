"""First-run launcher: project-local uv/Python installation or a prepared runtime.

Bootstrap needs Python 3.9+ and internet; installed application runs on Python 3.12.
No administrator access or Docker is needed for the native demo.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".tools"
UV_VERSION = "0.9.11"


def run(command, env):
    subprocess.run([str(part) for part in command], cwd=ROOT, env=env, check=True)


def uv_binary():
    for candidate in [TOOLS / "bin/uv", TOOLS / "bin/uv.exe"]:
        if candidate.is_file():
            return str(candidate)
    installed = shutil.which("uv")
    if installed:
        return installed
    target = TOOLS / "bootstrap"
    for relative in ["bin/uv", "bin/uv.exe", "Scripts/uv.exe"]:
        if (target / relative).is_file():
            return str(target / relative)
    print("Installing uv from PyPI into .tools/bootstrap (no system changes)…", flush=True)
    command = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
               "--no-input", "--target", str(target), f"uv=={UV_VERSION}"]
    subprocess.run(command, cwd=ROOT, check=True)
    for relative in ["bin/uv", "bin/uv.exe", "Scripts/uv.exe"]:
        if (target / relative).is_file():
            return str(target / relative)
    raise RuntimeError("uv installation did not create a binary; install uv from docs.astral.sh/uv")


def portable_python():
    manifest = TOOLS / "runtime-manifest.json"
    executable = TOOLS / "python-runtime/bin/python3.12"
    if not manifest.is_file() or not executable.is_file():
        return None
    data = json.loads(manifest.read_text())
    if data["system"] != platform.system() or data["machine"] != platform.machine():
        raise RuntimeError("This prepared runtime is for a different OS/CPU; use the source download")
    return str(executable)


def existing_project_python():
    executable = ROOT / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
    if not executable.is_file():
        return None
    try:
        version = subprocess.check_output(
            [str(executable), "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
            text=True, timeout=10,
        ).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return str(executable) if version == "3.12" else None


def wait_and_open(url):
    for _ in range(90):
        try:
            with urllib.request.urlopen(url + "/ready", timeout=2) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(1)


def parser():
    result = argparse.ArgumentParser(description="Install and launch the SentinelOps incident console")
    result.add_argument("--mode", choices=["demo", "real"], default="demo")
    result.add_argument("--port", type=int, default=8000)
    result.add_argument("--no-browser", action="store_true")
    result.add_argument("--install-only", action="store_true")
    result.add_argument("--verify", action="store_true", help="Install dev dependencies and run checks")
    result.add_argument("--docker", action="store_true", help="Use an already installed Docker engine")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if not 1024 <= args.port <= 65535:
        raise RuntimeError("Choose a port from 1024 through 65535")
    env = os.environ.copy()
    env.update({"MOCK_LLM": "true" if args.mode == "demo" else "false", "AUTO_INGEST": "true",
                "DEEPEVAL_TELEMETRY_OPT_OUT": "YES"})
    if args.mode == "demo":
        # A demo must stay free even when the user's shell has real-mode settings.
        env.update({"RETRIEVAL_BACKEND": "mock", "LANGFUSE_PUBLIC_KEY": "",
                    "LANGFUSE_SECRET_KEY": "", "OPENAI_API_KEY": ""})
    url = f"http://127.0.0.1:{args.port}"
    if args.docker:
        if args.port != 8000:
            raise RuntimeError("The Compose demo uses port 8000; omit --port")
        if not shutil.which("docker"):
            raise RuntimeError("Docker is not installed. Run without --docker for the native demo.")
        run(["docker", "compose", "up", "--build", "--detach", "--wait", "--wait-timeout", "240"], env)
        print(f"SentinelOps is ready: {url}\nStop with: docker compose down", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        return
    # A native demo is self-contained and cannot accidentally select a remote Qdrant server.
    env.update({"QDRANT_MODE": "local", "QDRANT_PATH": str(ROOT / ".sentinel/qdrant"),
                "CHECKPOINT_PATH": str(ROOT / ".sentinel/checkpoints.sqlite")})
    python = portable_python()
    if python:
        prefix = [python, str(ROOT / "scripts/portable_runner.py")]
    else:
        uv = uv_binary()
        env["UV_PYTHON_INSTALL_DIR"] = str(TOOLS / "managed-python")
        env["UV_PYTHON_BIN_DIR"] = str(TOOLS / "bin")
        existing = existing_project_python()
        if existing:
            # In particular, do not replace an in-use Windows virtualenv interpreter.
            env["UV_PYTHON"] = existing
        else:
            env["UV_PYTHON"] = "3.12"
            run([uv, "python", "install", "3.12"], env)
        run([uv, "sync", "--frozen"] + ([] if args.verify else ["--no-dev"]), env)
        prefix = [uv, "run", "--frozen", "--no-sync", "python", "-m"]
    if args.verify:
        env.update({"MOCK_LLM": "true", "RETRIEVAL_BACKEND": "mock"})
        run(prefix + ["ruff", "check", "."], env)
        env["RUN_LLM_EVALS"] = "false"
        run(prefix + ["pytest", "-v"], env)
        run(prefix + ["scripts.demo_run"], env)
        return
    if args.install_only:
        print("SentinelOps runtime installed. Launch with: python3 scripts/start.py", flush=True)
        return
    if not args.no_browser:
        threading.Thread(target=wait_and_open, args=(url,), daemon=True).start()
    print(f"Starting SentinelOps at {url}\nMode: {args.mode}; remediation: simulation\n"
          "Press Ctrl+C to stop.", flush=True)
    run(prefix + ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(args.port),
                  "--workers", "1", "--no-access-log"], env)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSentinelOps stopped.")
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Setup/startup could not finish: {error}\n"
              "See docs/GETTING_STARTED.md for prerequisite and network troubleshooting.", file=sys.stderr)
        raise SystemExit(1) from None
