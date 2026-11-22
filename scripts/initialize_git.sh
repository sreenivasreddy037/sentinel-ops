#!/usr/bin/env bash
# Run locally after verification; never creates commits containing .env or runtime data.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -e .git ]; then
  echo 'A Git repository already exists. Review and commit changes manually.'
  exit 1
fi
git var GIT_AUTHOR_IDENT >/dev/null 2>&1 || {
  echo 'Configure your Git user.name and user.email before initializing the history.'
  exit 1
}
bash scripts/verify.sh
git init -b main
git add pyproject.toml uv.lock .python-version .env.example .gitignore app data scripts/demo_run.py
git commit -m "feat: implement checkpointed incident triage and sandbox remediation"
git add tests evals
git commit -m "test: cover retrieval privacy retries and human approval lifecycle"
git add Dockerfile docker-compose.yml .dockerignore .github scripts/check_repository.py scripts/container_smoke.py scripts/verify.sh scripts/initialize_git.sh scripts/export_desktop.py
git commit -m "ci: add container smoke checks and offline evaluation gates"
git add AGENTS.md README.md docs
git commit -m "docs: explain architecture operations and verification limits"
git status --short
git log --oneline -4
echo 'Review the history and verification record, then add your GitHub remote and push.'
