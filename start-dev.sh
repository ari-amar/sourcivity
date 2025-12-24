#!/bin/bash

# Startup script to run both frontend and backend in development mode

# Get the directory where this script is located and cd to it
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "🚀 Starting Sourcivity development servers..."
echo "📁 Working directory: $SCRIPT_DIR"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python3 to run the backend."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js to run the frontend."
    exit 1
fi

# Check if backend env.config exists
if [ ! -f "app/api/config/env.config" ]; then
    echo "⚠️  Warning: app/api/config/env.config not found. Backend may not work properly."
fi

# Check if frontend .env.local exists
if [ ! -f ".env.local" ]; then
    echo "⚠️  Warning: .env.local not found. Creating default configuration..."
    echo "NEXT_PUBLIC_BACKEND_URL=http://localhost:8000" > .env.local
fi

echo "📦 Installing frontend dependencies..."
npm install

echo ""
echo "📦 Installing backend dependencies..."
cd "$SCRIPT_DIR/app/api"
pip3 install -r requirements.txt 2>/dev/null || echo "⚠️  No requirements.txt found or installation failed"

echo ""
echo "✅ Starting backend server on http://localhost:8000..."
cd "$SCRIPT_DIR/app/api"
python3 main.py 2>&1 | sed 's/^/[BACKEND] /' &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

echo "✅ Starting frontend server on http://localhost:3000..."
cd "$SCRIPT_DIR"
npm run dev 2>&1 | sed 's/^/[FRONTEND] /' &
FRONTEND_PID=$!

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Development servers are running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Trap Ctrl+C and kill both processes
trap "echo ''; echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# Wait for both processes
wait
