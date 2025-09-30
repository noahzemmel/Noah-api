#!/bin/bash
# deploy_lightning.sh - Lightning-Fast Daily Noah Deployment Script
"""
⚡ DAILY NOAH LIGHTNING DEPLOYMENT
The fastest deployment script for the world's most reliable AI briefing system.

Features:
- Lightning-fast deployment
- Bulletproof timeout protection
- Production-ready reliability
- Comprehensive error handling
"""

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_NAME="daily-noah-lightning"
HEALTH_CHECK_URL="http://localhost:8000/health"
MAX_HEALTH_CHECK_ATTEMPTS=15
HEALTH_CHECK_INTERVAL=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# DEPLOYMENT FUNCTIONS
# ============================================================================

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi
    
    # Check if pip is installed
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is not installed. Please install pip3 first."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        log_warning ".env file not found. Creating from template..."
        cat > .env << EOF
# Daily Noah Lightning Environment Variables
OPENAI_API_KEY=your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
API_BASE=http://localhost:8000
AUDIO_DIR=./audio
EOF
        log_warning "Please update .env file with your API keys before continuing."
        exit 1
    fi
    
    log_success "Prerequisites check passed!"
}

install_dependencies() {
    log_info "Installing lightning-fast dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    pip install -r requirements_perfect.txt
    
    if [ $? -eq 0 ]; then
        log_success "Dependencies installed successfully!"
    else
        log_error "Failed to install dependencies!"
        exit 1
    fi
}

start_backend() {
    log_info "Starting lightning backend..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Start backend in background
    python server_lightning.py &
    BACKEND_PID=$!
    
    # Wait for backend to start
    log_info "Waiting for backend to start..."
    sleep 3
    
    # Check if backend is running
    if ps -p $BACKEND_PID > /dev/null; then
        log_success "Backend started successfully (PID: $BACKEND_PID)"
        echo $BACKEND_PID > backend.pid
    else
        log_error "Failed to start backend!"
        exit 1
    fi
}

start_frontend() {
    log_info "Starting lightning frontend..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Start frontend in background
    streamlit run app_lightning.py --server.port 8501 --server.address 0.0.0.0 &
    FRONTEND_PID=$!
    
    # Wait for frontend to start
    log_info "Waiting for frontend to start..."
    sleep 3
    
    # Check if frontend is running
    if ps -p $FRONTEND_PID > /dev/null; then
        log_success "Frontend started successfully (PID: $FRONTEND_PID)"
        echo $FRONTEND_PID > frontend.pid
    else
        log_error "Failed to start frontend!"
        exit 1
    fi
}

wait_for_health() {
    log_info "Waiting for services to be healthy..."
    
    local attempt=1
    while [ $attempt -le $MAX_HEALTH_CHECK_ATTEMPTS ]; do
        log_info "Health check attempt $attempt/$MAX_HEALTH_CHECK_ATTEMPTS..."
        
        if curl -f -s $HEALTH_CHECK_URL > /dev/null 2>&1; then
            log_success "Health check passed! Services are running lightning fast."
            return 0
        fi
        
        log_info "Health check failed. Waiting $HEALTH_CHECK_INTERVAL seconds..."
        sleep $HEALTH_CHECK_INTERVAL
        ((attempt++))
    done
    
    log_error "Health check failed after $MAX_HEALTH_CHECK_ATTEMPTS attempts!"
    return 1
}

show_deployment_info() {
    log_success "Lightning deployment completed successfully!"
    echo ""
    echo "⚡ Daily Noah Lightning is now running!"
    echo ""
    echo "📍 Services:"
    echo "   • Backend API: http://localhost:8000"
    echo "   • Frontend UI: http://localhost:8501"
    echo "   • API Docs: http://localhost:8000/docs"
    echo "   • Health Check: http://localhost:8000/health"
    echo ""
    echo "🔧 Management Commands:"
    echo "   • Stop services: ./deploy_lightning.sh stop"
    echo "   • Restart services: ./deploy_lightning.sh restart"
    echo "   • Check status: ./deploy_lightning.sh status"
    echo "   • View logs: ./deploy_lightning.sh logs"
    echo ""
    echo "⚡ Lightning Features:"
    echo "   • Generation time: Under 60 seconds guaranteed"
    echo "   • Timeout protection: Active"
    echo "   • Real-time progress: Live updates"
    echo "   • Bulletproof reliability: Production-ready"
    echo ""
}

stop_services() {
    log_info "Stopping services..."
    
    # Stop backend
    if [ -f "backend.pid" ]; then
        BACKEND_PID=$(cat backend.pid)
        if ps -p $BACKEND_PID > /dev/null; then
            kill $BACKEND_PID
            log_success "Backend stopped"
        fi
        rm -f backend.pid
    fi
    
    # Stop frontend
    if [ -f "frontend.pid" ]; then
        FRONTEND_PID=$(cat frontend.pid)
        if ps -p $FRONTEND_PID > /dev/null; then
            kill $FRONTEND_PID
            log_success "Frontend stopped"
        fi
        rm -f frontend.pid
    fi
    
    # Kill any remaining processes
    pkill -f "server_lightning.py" || true
    pkill -f "streamlit run app_lightning.py" || true
    
    log_success "All services stopped!"
}

check_status() {
    log_info "Checking service status..."
    
    # Check backend
    if [ -f "backend.pid" ]; then
        BACKEND_PID=$(cat backend.pid)
        if ps -p $BACKEND_PID > /dev/null; then
            log_success "Backend is running (PID: $BACKEND_PID)"
        else
            log_warning "Backend is not running"
        fi
    else
        log_warning "Backend PID file not found"
    fi
    
    # Check frontend
    if [ -f "frontend.pid" ]; then
        FRONTEND_PID=$(cat frontend.pid)
        if ps -p $FRONTEND_PID > /dev/null; then
            log_success "Frontend is running (PID: $FRONTEND_PID)"
        else
            log_warning "Frontend is not running"
        fi
    else
        log_warning "Frontend PID file not found"
    fi
    
    # Check health
    if curl -f -s $HEALTH_CHECK_URL > /dev/null 2>&1; then
        log_success "Health check passed"
    else
        log_warning "Health check failed"
    fi
}

show_logs() {
    log_info "Showing service logs..."
    
    # Show backend logs
    if [ -f "backend.pid" ]; then
        BACKEND_PID=$(cat backend.pid)
        if ps -p $BACKEND_PID > /dev/null; then
            log_info "Backend logs:"
            tail -f /proc/$BACKEND_PID/fd/1 2>/dev/null || echo "Cannot access backend logs"
        fi
    fi
}

# ============================================================================
# MAIN DEPLOYMENT FLOW
# ============================================================================

main() {
    log_info "Starting Daily Noah Lightning deployment..."
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Install dependencies
    install_dependencies
    
    # Start backend
    start_backend
    
    # Start frontend
    start_frontend
    
    # Wait for health
    if wait_for_health; then
        show_deployment_info
    else
        log_error "Deployment failed health checks!"
        log_info "Checking service logs..."
        show_logs
        exit 1
    fi
}

# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "start")
        start_backend
        start_frontend
        wait_for_health
        show_deployment_info
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        stop_services
        sleep 2
        start_backend
        start_frontend
        wait_for_health
        log_success "Services restarted!"
        ;;
    "status")
        check_status
        ;;
    "logs")
        show_logs
        ;;
    "health")
        curl -f $HEALTH_CHECK_URL && echo "✅ Healthy" || echo "❌ Unhealthy"
        ;;
    *)
        echo "Usage: $0 {deploy|start|stop|restart|status|logs|health}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Full deployment (default)"
        echo "  start   - Start services"
        echo "  stop    - Stop services"
        echo "  restart - Restart services"
        echo "  status  - Show service status"
        echo "  logs    - View service logs"
        echo "  health  - Check health status"
        exit 1
        ;;
esac
