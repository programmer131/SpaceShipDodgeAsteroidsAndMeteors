#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# Use virtualenv python if available
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

exec $PYTHON run_all.py "$@"
