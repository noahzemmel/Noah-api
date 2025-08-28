#!/bin/bash

# 🚀 Noah MVP Quick Start Script

echo "🎙️ Starting Noah MVP..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please ensure your .env file is configured with all API keys"
    exit 1
fi

# Load environment variables
source .env

# Check if required variables are set
if [ -z "$OPENAI_API_KEY" ] || [ -z "$ELEVENLABS_API_KEY" ] || [ -z "$TAVILY_API_KEY" ]; then
    echo "❌ Missing required API keys in .env file"
    exit 1
fi

echo "✅ Environment variables loaded"
echo "🌐 API_BASE: $API_BASE"

# Create audio directory
mkdir -p audio

# Function to cleanup on exit
cleanup() {
    echo "🛑 Shutting down services..."
    pkill -f "python server.py" 2>/dev/null
    pkill -f "streamlit run app.py" 2>/dev/null
    echo "✅ Services stopped"
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Start backend
echo "🔧 Starting FastAPI backend on port 8000..."
python server.py > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Test backend health
if curl -s "http://localhost:8000/health" > /dev/null; then
    echo "✅ Backend is running and healthy"
else
    echo "❌ Backend failed to start"
    exit 1
fi

# Start frontend
echo "🎨 Starting Streamlit frontend on port 8502..."
streamlit run app.py --server.port 8502 --server.address 0.0.0.0 > frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
echo "⏳ Waiting for frontend to start..."
sleep 8

# Show status
echo ""
echo "🎉 Noah MVP is running!"
echo ""
echo "📍 Services:"
echo "   Backend API:  http://localhost:8000"
echo "   Frontend UI:  http://localhost:8502"
echo "   API Docs:     http://localhost:8000/docs"
echo "   Health Check: http://localhost:8000/health"
echo ""
echo "🎙️ Open http://localhost:8502 in your browser to start generating bulletins!"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user to stop
wait
