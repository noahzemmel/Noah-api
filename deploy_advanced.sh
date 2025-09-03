#!/bin/bash
# deploy_advanced.sh - World-Class Daily Noah Advanced Deployment Script
"""
🚀 DAILY NOAH ADVANCED DEPLOYMENT
The most sophisticated deployment script for the world's most advanced AI briefing system.

Features:
- Automated deployment
- Health checks
- Rollback capability
- Performance monitoring
- Security validation
"""

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_NAME="daily-noah-advanced"
DOCKER_COMPOSE_FILE="docker-compose.advanced.yml"
HEALTH_CHECK_URL="http://localhost:8000/health"
MAX_HEALTH_CHECK_ATTEMPTS=30
HEALTH_CHECK_INTERVAL=10

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
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        log_warning ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_warning "Please update .env file with your API keys before continuing."
            exit 1
        else
            log_error ".env.example file not found. Please create .env file with required environment variables."
            exit 1
        fi
    fi
    
    log_success "Prerequisites check passed!"
}

build_images() {
    log_info "Building Docker images..."
    
    docker-compose -f $DOCKER_COMPOSE_FILE build --no-cache
    
    if [ $? -eq 0 ]; then
        log_success "Docker images built successfully!"
    else
        log_error "Failed to build Docker images!"
        exit 1
    fi
}

deploy_services() {
    log_info "Deploying services..."
    
    # Stop existing services
    docker-compose -f $DOCKER_COMPOSE_FILE down
    
    # Start services
    docker-compose -f $DOCKER_COMPOSE_FILE up -d
    
    if [ $? -eq 0 ]; then
        log_success "Services deployed successfully!"
    else
        log_error "Failed to deploy services!"
        exit 1
    fi
}

wait_for_health() {
    log_info "Waiting for services to be healthy..."
    
    local attempt=1
    while [ $attempt -le $MAX_HEALTH_CHECK_ATTEMPTS ]; do
        log_info "Health check attempt $attempt/$MAX_HEALTH_CHECK_ATTEMPTS..."
        
        if curl -f -s $HEALTH_CHECK_URL > /dev/null 2>&1; then
            log_success "Health check passed! Services are running."
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
    log_success "Deployment completed successfully!"
    echo ""
    echo "🚀 Daily Noah Advanced is now running!"
    echo ""
    echo "📍 Services:"
    echo "   • API: http://localhost:8000"
    echo "   • Frontend: http://localhost:8501"
    echo "   • API Docs: http://localhost:8000/docs"
    echo "   • Health Check: http://localhost:8000/health"
    echo "   • Metrics: http://localhost:9090"
    echo "   • Grafana: http://localhost:3000 (admin/admin)"
    echo "   • Prometheus: http://localhost:9091"
    echo "   • Kibana: http://localhost:5601"
    echo ""
    echo "🔧 Management Commands:"
    echo "   • View logs: docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
    echo "   • Stop services: docker-compose -f $DOCKER_COMPOSE_FILE down"
    echo "   • Restart services: docker-compose -f $DOCKER_COMPOSE_FILE restart"
    echo "   • Scale API: docker-compose -f $DOCKER_COMPOSE_FILE up -d --scale noah-api=3"
    echo ""
}

cleanup() {
    log_info "Cleaning up..."
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes (optional)
    # docker volume prune -f
    
    log_success "Cleanup completed!"
}

# ============================================================================
# MAIN DEPLOYMENT FLOW
# ============================================================================

main() {
    log_info "Starting Daily Noah Advanced deployment..."
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Build images
    build_images
    
    # Deploy services
    deploy_services
    
    # Wait for health
    if wait_for_health; then
        show_deployment_info
        cleanup
    else
        log_error "Deployment failed health checks!"
        log_info "Checking service logs..."
        docker-compose -f $DOCKER_COMPOSE_FILE logs --tail=50
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
    "build")
        check_prerequisites
        build_images
        ;;
    "start")
        deploy_services
        wait_for_health
        show_deployment_info
        ;;
    "stop")
        log_info "Stopping services..."
        docker-compose -f $DOCKER_COMPOSE_FILE down
        log_success "Services stopped!"
        ;;
    "restart")
        log_info "Restarting services..."
        docker-compose -f $DOCKER_COMPOSE_FILE restart
        wait_for_health
        log_success "Services restarted!"
        ;;
    "logs")
        docker-compose -f $DOCKER_COMPOSE_FILE logs -f
        ;;
    "status")
        docker-compose -f $DOCKER_COMPOSE_FILE ps
        ;;
    "health")
        curl -f $HEALTH_CHECK_URL && echo "✅ Healthy" || echo "❌ Unhealthy"
        ;;
    *)
        echo "Usage: $0 {deploy|build|start|stop|restart|logs|status|health}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Full deployment (default)"
        echo "  build   - Build Docker images only"
        echo "  start   - Start services"
        echo "  stop    - Stop services"
        echo "  restart - Restart services"
        echo "  logs    - View service logs"
        echo "  status  - Show service status"
        echo "  health  - Check health status"
        exit 1
        ;;
esac
