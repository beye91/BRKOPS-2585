#!/bin/bash
# =============================================================================
# BRKOPS-2585 Backend Startup Script
# Runs FastAPI server and arq worker in the same container
# =============================================================================

set -e

echo "Starting BRKOPS-2585 Backend..."

# Start arq worker in background
echo "Starting arq worker..."
python -m arq worker.WorkerSettings &
ARQ_PID=$!

# Start FastAPI server
echo "Starting FastAPI server..."
uvicorn main:app --host ${BACKEND_HOST:-0.0.0.0} --port ${BACKEND_PORT:-8000} &
UVICORN_PID=$!

# Handle shutdown signals
trap "kill $ARQ_PID $UVICORN_PID 2>/dev/null; exit 0" SIGTERM SIGINT

# Wait for either process to exit
wait -n $ARQ_PID $UVICORN_PID

# If one exits, kill the other
kill $ARQ_PID $UVICORN_PID 2>/dev/null
exit 1
