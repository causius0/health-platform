#!/bin/bash
# Health Platform — avvio sviluppo (backend Flask :5001 + frontend Vite :5173)

GREEN='\033[0;32m'; BLUE='\033[0;34m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo -e "${BLUE}Health Platform — sviluppo${NC}"

# libera le porte
lsof -ti:5001 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true
sleep 1

# backend
if [ ! -x "$BACKEND_DIR/venv/bin/python" ]; then
  echo -e "${YELLOW}venv mancante: creo l'ambiente e installo le dipendenze…${NC}"
  python3 -m venv "$BACKEND_DIR/venv"
  "$BACKEND_DIR/venv/bin/pip" install -q -r "$BACKEND_DIR/requirements-dev.txt"
fi

# controllo PostgreSQL
if ! (pg_isready -h localhost -p 5432 >/dev/null 2>&1 || /opt/homebrew/opt/postgresql@18/bin/pg_isready -h localhost -p 5432 >/dev/null 2>&1); then
  echo -e "${RED}PostgreSQL non raggiungibile su :5432. Avvialo e riprova.${NC}"
  echo "DATABASE_URL configurabile in backend/.env"
  exit 1
fi

echo -e "${GREEN}Avvio backend su :5001…${NC}"
cd "$BACKEND_DIR"
./venv/bin/python app.py &
BACKEND_PID=$!

sleep 2
if ! curl -sf http://localhost:5001/api/health >/dev/null; then
  echo -e "${RED}Backend non avviato: controlla i log.${NC}"
  kill $BACKEND_PID 2>/dev/null
  exit 1
fi
echo -e "${GREEN}Backend OK (PID $BACKEND_PID)${NC}"

# frontend
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo -e "${YELLOW}Installo le dipendenze frontend…${NC}"
  (cd "$FRONTEND_DIR" && npm install)
fi

echo -e "${GREEN}Avvio frontend su :5173…${NC}"
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
sleep 3

echo ""
echo -e "${GREEN}Server attivi${NC}"
echo -e "${BLUE}Frontend:${NC} http://localhost:5173/"
echo -e "${BLUE}Backend :${NC} http://localhost:5001/api/health"
echo -e "${BLUE}Demo    :${NC} doctor / patient1..5 — HealthPlatform.Demo2026!"
echo ""
echo -e "${YELLOW}Ctrl+C per fermare tutto${NC}"

trap "echo -e '${YELLOW}Arresto…${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
