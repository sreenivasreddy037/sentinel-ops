#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -x .tools/python-runtime/bin/python3.12 ]; then
  exec .tools/python-runtime/bin/python3.12 scripts/start.py "$@"
fi
if command -v python3 >/dev/null; then
  exec python3 scripts/start.py "$@"
fi
echo 'Install Python 3.9+ from https://www.python.org/downloads/ and run this launcher again.'
exit 1
