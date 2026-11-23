# Run SentinelOps

SentinelOps is an incident-triage and remediation-planning application. The free demo includes the browser console, a real local Qdrant database, saved incident state, evidence lookup and the complete approval/rejection lifecycle. Remediation is simulated. Real OpenAI generation is a separate optional mode that needs your own API key.

## Download

Use GitHub's **Code → Download ZIP** and extract the folder, or clone:

```bash
git clone https://github.com/sreenivasreddy037/sentinel-ops.git
cd sentinel-ops
```

A ZIP download does not require Git. Never run commands from inside an unextracted archive.

## Easiest native start: Mac, Linux and Windows

You need **Python 3.9 or newer with pip** for the bootstrap and an internet connection for the first dependency installation. The launcher installs uv and the application dependencies inside this project, and uv installs Python 3.12. No administrator access, Docker, Qdrant account, OpenAI key or Langfuse account is required for the demo.

Mac / Linux:

```bash
bash start.sh
```

Windows, from Command Prompt:

```bat
start.cmd
```

On Mac you can also open `Start-SentinelOps.command`. The launcher opens **http://127.0.0.1:8000** after the runbooks are indexed. Choose an example, click **Analyze incident**, inspect the hypothesis and commands, then approve or reject the sandbox plan. Press Ctrl+C in the launch terminal to stop the application.

The first install can take several minutes and download several hundred megabytes. Later launches reuse the local environment. If port 8000 is occupied, use `bash start.sh --port 8001` or `start.cmd --port 8001`. Native startup binds to your own computer only.

Install without starting the server:

```bash
python3 scripts/start.py --install-only
```

Install development tools and verify lint, tests and the CLI demo:

```bash
python3 scripts/start.py --verify
```

For a terminal that should not open a browser, add `--no-browser`.

## Prepared Apple silicon Mac download

The `native-distribution (macos-15)` CI job produces a `SentinelOps-macos-arm64` artifact containing the source, Python 3.12, uv and locked Python dependencies. Download the artifact from a successful [Actions run](https://github.com/sreenivasreddy037/sentinel-ops/actions), unzip the artifact wrapper and extract `SentinelOps-macos-arm64.tar.gz`. Open the resulting `SentinelOps` folder and run `bash start.sh` or open `Start-SentinelOps.command`.

This bundle is for Apple silicon macOS only. It is checked after extraction into a different directory to catch machine-specific paths. No dependency download is needed to run its free demo. A GitHub sign-in may be required to download Actions artifacts, and artifacts expire after 30 days. The source download above remains the universal distribution path. Do not reuse the Mac runtime on Intel, Linux or Windows.

The prepared runtime contains software from the pinned PyPI dependencies and Astral's managed Python distribution. Source, manifests and the dependency lock remain inspectable. Normal OS software-verification prompts may still apply; follow your organization's installation policy.

## Docker alternative

If Docker Engine/Desktop and Compose v2 are already installed:

```bash
docker compose up --build --detach --wait
```

Open http://localhost:8000. Docker installs Python packages inside the image and starts Qdrant automatically. Startup indexes all runbooks; no manual `/ingest` call is needed. Stop with `docker compose down`.

Docker Desktop installation and any vendor license acceptance are handled by the person installing it. The native launcher avoids that prerequisite.

## Real AI mode

Copy `.env.example` to `.env`, add your own `OPENAI_API_KEY`, and set `MOCK_LLM=false`. Do not commit `.env`. Then launch explicitly:

```bash
bash start.sh --mode real
```

The `real` flag uses FastEmbed, BM25 and FlashRank plus the configured OpenAI models. It downloads local model files on first use and can incur OpenAI API charges. The default launcher always chooses the free deterministic demo, even if your shell contains real-mode settings. All remediation remains simulated in both modes.

Langfuse is optional. No account is needed to run the application. To use tracing, configure both Langfuse keys in `.env`; only transition metadata is recorded.

## Troubleshooting

| Symptom | Action |
|---|---|
| `python3`, `python` or `py` is missing | Install Python 3.9+ from python.org with pip enabled, or use the matching prepared Mac bundle. |
| `No module named pip` | Install pip for your Python distribution, or install uv using its official installation guide and rerun the launcher. |
| Download/DNS/proxy failure | Allow your approved terminal access to PyPI and GitHub. The setup needs internet; the prepared Mac demo does not. |
| Port already in use | Launch with `--port 8001`, or stop the previous SentinelOps process. |
| Qdrant reports a storage lock | Stop the other process using the same project folder. Use one server per native project. |
| Dashboard says not ready | Wait for startup to finish and refresh. `/ready` returns 200 only after indexing; check terminal output if it remains unavailable. |
| Server requires an access token | Expand the token field in the console and enter your configured `API_TOKEN`; it is not saved in browser storage. |
| Model or API error in real mode | Check the key, model access and network. Use `--mode demo` to verify the local application independently. |
| Restricted environment blocks local startup | Run the launcher in a terminal that permits dependency downloads and localhost listeners. |

## What is ready and what is optional

The downloadable demo is intended to run immediately after its prerequisites/launcher complete. CI checks the API, privacy and approval paths, first-start behavior, Docker distribution and native launch paths. Read `docs/VERIFICATION.md` for measured results and any unfinished checks.

Paid model-judge evaluation, organizational SSO/reviewer roles and real infrastructure execution are separate concerns. This project deliberately ships a safe simulation executor and does not claim to repair a production cloud account.
