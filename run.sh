#!/usr/bin/env bash
# Run Guardian Agent API. Requires MongoDB (set MONGODB_URL). Redis/streams added at deployment.
set -e
cd "$(dirname "$0")"
export MONGODB_URL="${MONGODB_URL:-mongodb://localhost:27017}"
if [ -d ".venv" ]; then
  .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
  python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
