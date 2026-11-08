#!/bin/bash
# Fresh demo: frees the port, deletes the demo database and its -wal/-shm files, seeds, starts.
# The bench lives in bench.db and survives this.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${1:-8000}"
pids=$(lsof -ti "tcp:$PORT" || true)
if [ -n "$pids" ]; then kill $pids; sleep 1; fi
rm -f demo.db demo.db-wal demo.db-shm
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then echo "No ANTHROPIC_API_KEY: cloud is the qwen3:8b stand-in."; fi
export SH_DB=demo.db SH_DEMO=1
exec .venv/bin/python -m uvicorn counsel.server:app --host 0.0.0.0 --port "$PORT" --log-level warning
