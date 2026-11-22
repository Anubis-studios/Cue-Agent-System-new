#!/bin/bash
echo "Starting Cue Agent System..."
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
sleep 3
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
