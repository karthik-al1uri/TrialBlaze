#!/bin/bash
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "TrailBlaze AI — Starting servers"
echo "────────────────────────────────"

if [ ! -f "ai/.env" ]; then
  echo -e "${RED}ERROR: ai/.env not found.${NC}"
  echo "Copy ai/.env.example to ai/.env and fill in your keys."
  exit 1
fi

export $(grep -v '^#' ai/.env | xargs) 2>/dev/null

MISSING=()
[ -z "$MONGO_URI" ]      && MISSING+=("MONGO_URI")
[ -z "$OPENAI_API_KEY" ] && MISSING+=("OPENAI_API_KEY")

if [ ${#MISSING[@]} -gt 0 ]; then
  echo -e "${RED}ERROR: Missing required env variables:${NC}"
  for key in "${MISSING[@]}"; do echo "  - $key"; done
  exit 1
fi

echo -e "${GREEN}✓${NC} Environment OK"

if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
  echo -e "${GREEN}✓${NC} Virtual environment activated"
fi

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo "Shutting down..."
  [ -n "$BACKEND_PID" ]  && kill $BACKEND_PID  2>/dev/null
  [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
  echo "Done."
  exit 0
}
trap cleanup SIGINT SIGTERM

mkdir -p logs
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
python -m uvicorn backend.app.main:app \
  --host 0.0.0.0 --port 8000 >> logs/backend.log 2>&1 &
BACKEND_PID=$!

echo -n "  Waiting for backend"
TRIES=0
until curl -s http://localhost:8000/health > /dev/null 2>&1; do
  sleep 1; echo -n "."; TRIES=$((TRIES+1))
  if [ $TRIES -ge 30 ]; then
    echo -e "\n${RED}ERROR: Backend failed. Check logs/backend.log${NC}"
    cleanup; exit 1
  fi
done
echo -e "\n${GREEN}✓${NC} Backend running on http://localhost:8000"

lsof -ti:3000 | xargs kill -9 2>/dev/null || true
cd frontend/nextjs-app
rm -rf .next/cache
npm run dev >> ../../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ../..

echo -n "  Waiting for frontend"
TRIES=0
until curl -s http://localhost:3000 > /dev/null 2>&1; do
  sleep 1; echo -n "."; TRIES=$((TRIES+1))
  if [ $TRIES -ge 45 ]; then
    echo -e "\n${RED}ERROR: Frontend failed. Check logs/frontend.log${NC}"
    cleanup; exit 1
  fi
done
echo -e "\n${GREEN}✓${NC} Frontend running on http://localhost:3000"

echo ""
echo "────────────────────────────────"
echo -e "${GREEN}TrailBlaze AI is running${NC}"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API docs:  http://localhost:8000/docs"
echo ""
echo "Logs: logs/backend.log | logs/frontend.log"
echo "Press Ctrl+C to stop."
echo "────────────────────────────────"
wait
