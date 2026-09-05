#!/bin/sh
set -eu

uvicorn src.api.api:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

streamlit run app.py --server.address=0.0.0.0 --server.port=8501 &
FRONTEND_PID=$!

wait -n "$BACKEND_PID" "$FRONTEND_PID"
exit $?
