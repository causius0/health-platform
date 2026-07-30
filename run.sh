#!/bin/bash

# Health Platform Startup Script
# Avvia sia il backend Flask che il frontend Vite

echo "🏥 Piattaforma Salute - Avvio..."

# Directory script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}")" && pwd )"
cd "$SCRIPT_DIR"

# Avvia backend in background
echo "📡 Avvio backend Flask..."
cd "$SCRIPT_DIR/backend"
source venv/bin/activate
python app.py &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Attendi che backend sia pronto
sleep 2

# Avvia frontend
echo "🌐 Avvio frontend Vite..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "✅ Piattaforma avviata!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:5000"
echo ""
echo "Premi Ctrl+C per fermare entrambi i server"

# Funzione cleanup su exit
trap "echo '🛑 Arresto server...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

# Attendi segnale exit
wait
