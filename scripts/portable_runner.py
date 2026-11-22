"""Activate relocated dependencies without a machine-specific virtualenv path."""

import runpy
import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    site.addsitedir(str(ROOT / ".tools/site-packages"))
    sys.path.insert(0, str(ROOT))
    if len(sys.argv) < 2:
        raise SystemExit("Usage: portable_runner.py MODULE [ARGS]")
    module = sys.argv.pop(1)
    sys.argv[0] = module
    runpy.run_module(module, run_name="__main__")


if __name__ == "__main__":
    main()
