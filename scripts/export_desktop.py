"""Copy reviewed project source to a new Desktop folder without runtime secrets.

Exports source files only and never overwrites an existing folder.
"""

import shutil
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
ENTRIES = [
    "AGENTS.md", "README.md", "pyproject.toml", "uv.lock", ".python-version", ".env.example",
    ".gitignore", ".dockerignore", "Dockerfile", "docker-compose.yml", ".github", "app", "data",
    "scripts", "tests", "evals", "docs", "start.sh", "start.cmd", "Start-SentinelOps.command",
]


def ignore(directory, names):
    return {name for name in names if name in {"__pycache__", ".pytest_cache", ".ruff_cache"}
            or name.endswith((".pyc", ".sqlite", ".db"))}


def main():
    destination = Path.home() / "Desktop/SentinelOps"
    if destination.exists():
        raise SystemExit(f"Refusing to overwrite {destination}; rename the existing folder first")
    destination.mkdir(parents=True)
    try:
        for entry in ENTRIES:
            original = SOURCE / entry
            if not original.exists():
                continue
            target = destination / entry
            if original.is_dir():
                shutil.copytree(original, target, ignore=ignore)
            else:
                shutil.copy2(original, target)
        # A source-only export is intentional: no .env, caches or incident state.
        print(f"Created {destination}. Launch with bash start.sh; see docs/GETTING_STARTED.md.")
    except Exception:
        print(f"Export incomplete. Review the partially created folder: {destination}")
        raise


if __name__ == "__main__":
    main()
