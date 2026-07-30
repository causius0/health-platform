#!/bin/bash

# Health Platform Development Startup Script
# Starts both Flask backend and Vite frontend together

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏥 Health Platform - Development Mode${NC}"
echo "================================"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Kill any existing processes on ports 5001 and 5173-5174
echo -e "${YELLOW}Stopping any existing processes...${NC}"
lsof -ti:5001 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
lsof -ti:5174 | xargs kill -9 2>/dev/null
sleep 1

# Start Flask backend
echo -e "${GREEN}🚀 Starting Flask backend on port 5001...${NC}"
cd "$BACKEND_DIR"
source venv/bin/activate
python app.py &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Check if backend started successfully
if ! curl -s http://localhost:5001 > /dev/null; then
    echo -e "${RED}❌ Backend failed to start${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backend started successfully (PID: $BACKEND_PID)${NC}"

# Start Vite frontend
echo -e "${GREEN}🚀 Starting Vite frontend...${NC}"
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 3

echo -e "${GREEN}✅ Frontend started successfully (PID: $FRONTEND_PID)${NC}"

echo ""
echo -e "${GREEN}🎉 Development servers are running!${NC}"
echo -e "${BLUE}Frontend:${NC} http://localhost:5173/"
echo -e "${BLUE}Backend:${NC}  http://localhost:5001/"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"

# Handle shutdown
trap "echo -e '${YELLOW}🛑 Stopping servers...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo -e '${GREEN}✅ All servers stopped${NC}'; exit 0" INT TERM

# Keep script running
wait
