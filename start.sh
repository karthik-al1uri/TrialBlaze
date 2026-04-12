#!/bin/bash
set -e

# ── Colors ──────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── Move to project root (same dir as this script) ─────────
cd "$(dirname "$0")"

echo ""
echo "TrailBlaze AI — Starting servers"
echo "────────────────────────────────"

# ── Environment ──────────────────────────────────────────────
if [ ! -f "ai/.env" ]; then
  echo -e "${RED}ERROR: ai/.env not found.${NC}"
  echo "Copy ai/.env.example to ai/.env and fill in your keys."
  exit 1
fi

# Load env to check required keys (handles spaces around = safely)
while IFS= read -r line; do
  # Skip comments and empty lines
  [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
  # Trim spaces around = and export
  key="${line%%=*}"
  val="${line#*=}"
  key="$(echo "$key" | xargs)"
  val="$(echo "$val" | xargs)"
  export "$key=$val"
done < ai/.env

MISSING=()
[ -z "$MONGO_URI" ]       && MISSING+=("MONGO_URI")
[ -z "$OPENAI_API_KEY" ]  && MISSING+=("OPENAI_API_KEY")

if [ ${#MISSING[@]} -gt 0 ]; then
  echo -e "${RED}ERROR: Missing required env variables:${NC}"
  for key in "${MISSING[@]}"; do
    echo "  - $key"
  done
  echo "Add them to ai/.env and try again."
  exit 1
fi

echo -e "${GREEN}✓${NC} Environment variables OK"

# ── Virtual environment ───────────────────────────────────────
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
  echo -e "${GREEN}✓${NC} Virtual environment activated"
elif [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
  echo -e "${GREEN}✓${NC} Virtual environment activated"
else
  echo -e "${YELLOW}WARNING: No virtual environment found.${NC}"
  echo "Using system Python. Run: python -m venv .venv"
fi

# ── Create logs directory ────────────────────────────────────
mkdir -p logs

# ── Cleanup function ──────────────────────────────────────────
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "Shutting down servers..."
  [ -n "$BACKEND_PID" ]  && kill $BACKEND_PID  2>/dev/null
  [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
  echo "Servers stopped."
  exit 0
}

trap cleanup SIGINT SIGTERM

# ── Backend ───────────────────────────────────────────────────
echo ""
echo "Starting backend (FastAPI)..."

# Kill anything already on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 1

PYTHONPATH=. python -m uvicorn backend.app.main:app \
  --host 0.0.0.0 --port 8000 \
  >> logs/backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to be healthy (max 30s)
echo -n "  Waiting for backend"
TRIES=0
until curl -s http://localhost:8000/health > /dev/null 2>&1; do
  sleep 1
  echo -n "."
  TRIES=$((TRIES + 1))
  if [ $TRIES -ge 30 ]; then
    echo ""
    echo -e "${RED}ERROR: Backend did not start after 30s.${NC}"
    echo "Check logs/backend.log for details."
    tail -20 logs/backend.log
    cleanup
    exit 1
  fi
done
echo ""
echo -e "${GREEN}✓${NC} Backend running on http://localhost:8000"

# ── Frontend ──────────────────────────────────────────────────
echo ""
echo "Starting frontend (Next.js)..."

# Kill anything already on port 3000
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 1

cd frontend/nextjs-app

# Clear Next.js cache to prevent HMR corruption
rm -rf .next/cache

npm run dev >> ../../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ../..

# Wait for frontend (max 45s — Next.js takes longer)
echo -n "  Waiting for frontend"
TRIES=0
until curl -s http://localhost:3000 > /dev/null 2>&1; do
  sleep 1
  echo -n "."
  TRIES=$((TRIES + 1))
  if [ $TRIES -ge 45 ]; then
    echo ""
    echo -e "${RED}ERROR: Frontend did not start after 45s.${NC}"
    echo "Check logs/frontend.log for details."
    tail -20 logs/frontend.log
    cleanup
    exit 1
  fi
done
echo ""
echo -e "${GREEN}✓${NC} Frontend running on http://localhost:3000"

# ── Done ──────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────"
echo -e "${GREEN}TrailBlaze AI is running${NC}"
echo ""
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."
echo "Logs: logs/backend.log | logs/frontend.log"
echo "────────────────────────────────"
echo ""

# Keep script alive
wait
