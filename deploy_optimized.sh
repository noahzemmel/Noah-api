#!/bin/bash

# deploy_optimized.sh - Deploy Daily Noah Optimized System
"""
🎯 DAILY NOAH OPTIMIZED DEPLOYMENT SCRIPT
Perfect balance of speed, quality, and timing accuracy.

This script sets up and deploys the optimized Noah system.
"""

echo "🎯 DAILY NOAH OPTIMIZED - DEPLOYMENT"
echo "====================================="
echo ""

# Kill any existing processes
echo "🛑 Stopping existing processes..."
pkill -f "server_optimized.py" 2>/dev/null
pkill -f "streamlit run app.py" 2>/dev/null
sleep 2

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p audio
mkdir -p logs

# Check for .env file
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your API keys:"
    echo "  OPENAI_API_KEY=your_key_here"
    echo "  ELEVENLABS_API_KEY=your_key_here"
    echo "  TAVILY_API_KEY=your_key_here"
    exit 1
fi

echo "✅ Environment file found"

# Install dependencies if needed
if [ "$1" == "--install" ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Start backend server
echo "🚀 Starting optimized backend server..."
source .env && nohup python server_optimized.py > logs/server.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
echo "⏳ Waiting for backend to initialize..."
sleep 5

# Check if backend is responding
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is healthy"
else
    echo "⚠️  Backend health check failed, but continuing..."
fi

# Start frontend
echo "🚀 Starting Streamlit frontend..."
source .env && nohup streamlit run app.py --server.port 8501 > logs/streamlit.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"

# Wait for frontend to be ready
echo "⏳ Waiting for frontend to initialize..."
sleep 5

echo ""
echo "====================================="
echo "🎯 DAILY NOAH OPTIMIZED IS RUNNING!"
echo "====================================="
echo ""
echo "🌐 Frontend: http://localhost:8501"
echo "🔧 Backend:  http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo ""
echo "Features:"
echo "  ⚡ Fast generation (30-45s)"
echo "  📰 High-quality recent news"
echo "  🎯 Precise timing (±15s)"
echo "  📊 Real-time progress"
echo ""
echo "Logs:"
echo "  📝 Backend:  logs/server.log"
echo "  📝 Frontend: logs/streamlit.log"
echo ""
echo "To stop: pkill -f 'server_optimized.py' && pkill -f 'streamlit'"
echo "====================================="

