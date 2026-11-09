#!/bin/bash
# Start Chamber for real use. The firm's data stays in chamber.db between runs.
# Set CHAMBER_HOST=0.0.0.0 to reach it from other computers, and put HTTPS in front when you do.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${1:-8000}"
export SH_DB="${SH_DB:-chamber.db}"
unset SH_DEMO
source scripts/cloud_key.sh
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then echo "No ANTHROPIC_API_KEY: cloud is the qwen3:8b stand-in."; fi
exec .venv/bin/python -m uvicorn counsel.server:app --host "${CHAMBER_HOST:-127.0.0.1}" --port "$PORT" --log-level warning
