#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v uv >/dev/null || { echo 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/'; exit 1; }
uv sync --frozen
uv run ruff check .
uv run python scripts/check_repository.py
MOCK_LLM=true RUN_LLM_EVALS=false uv run pytest -v
MOCK_LLM=true uv run python scripts/demo_run.py
docker compose config --quiet
echo 'All local gates passed. Dependencies were installed from the committed uv.lock.'
