#!/bin/bash
cd "$(dirname "$0")/backend"
export PATH="$HOME/.local/bin:$PATH"
export PYTHONPATH=.
# Prefer project .env
export $(grep -v '^#' ../.env 2>/dev/null | xargs) 2>/dev/null
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
