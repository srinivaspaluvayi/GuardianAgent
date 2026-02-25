#!/usr/bin/env bash
# Run Guardian Agent API. Requires MongoDB (MONGODB_URL in .env). Redis/streams added at deployment.
set -e
cd "$(dirname "$0")"

PORT="${PORT:-8001}"

if [ -d ".venv" ]; then
  .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --reload
else
  python3 -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --reload
fi
