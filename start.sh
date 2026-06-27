#!/usr/bin/env bash
set -e

echo "Starting backend..."
cd "$(dirname "$0")/backend"
venv/bin/python app.py &
BACKEND_PID=$!

echo "Starting frontend..."
cd "$(dirname "$0")/frontend"
npx vite --host &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

echo "Backend:  http://localhost:5000"
echo "Frontend: http://localhost:5173"
wait
