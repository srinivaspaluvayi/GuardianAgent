#!/usr/bin/env bash
# Run Guardian API from project root.
# Loads GUARDIAN_* from .env in this directory (no export needed).
cd "$(dirname "$0")"
export PYTHONPATH="${PWD}:${PYTHONPATH:-}"
exec "${PWD}/.venv/bin/python" -m uvicorn app.main:app --reload --port 8000 "$@"
