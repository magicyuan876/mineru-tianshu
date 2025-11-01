#!/bin/bash
# Tianshu - Docker Quick Setup Script
# One-click dependency check, environment setup, and service startup

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# ============================================================================
# Initialize Docker Compose command
# ============================================================================
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    log_error "Docker Compose is not installed or unavailable"
    exit 1
fi

# ============================================================================
# Check dependencies
# ============================================================================
check_dependencies() {
    log_info "Checking system dependencies..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed, please install Docker first"
        log_info "Installation guide: https://docs.docker.com/get-docker/"
        exit 1
    fi
    log_success "Docker is installed: $(docker --version)"

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        log_info "Installation guide: https://docs.docker.com/compose/install/"
        exit 1
    fi

    log_success "Docker Compose is installed: $($COMPOSE_CMD version 2>&1 | head -n1)"

    # Check NVIDIA Container Toolkit (GPU support)
    if command -v nvidia-smi &> /dev/null; then
        log_success "NVIDIA GPU detected"

        if docker run --rm --gpus all nvidia/cuda:12.6.2-base-ubuntu22.04 nvidia-smi &> /dev/null; then
            log_success "NVIDIA Container Toolkit is properly configured"
        else
            log_warning "NVIDIA Container Toolkit is not configured or incorrectly configured"
            log_info "Installation guide: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
            log_warning "Will run in CPU mode"
        fi
    else
        log_warning "NVIDIA GPU not detected, will run in CPU mode"
    fi
}

# ============================================================================
# Setup environment
# ============================================================================
setup_environment() {
    log_info "Setting up environment variables..."

    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            log_success ".env file created"
            log_warning "Please edit .env file, especially JWT_SECRET_KEY"

            # Generate random JWT secret
            if command -v openssl &> /dev/null; then
                JWT_SECRET=$(openssl rand -hex 32)
                sed -i "s/CHANGE_THIS_TO_A_SECURE_RANDOM_STRING_IN_PRODUCTION/$JWT_SECRET/" .env
                log_success "JWT_SECRET_KEY automatically generated"
            else
                log_warning "Please manually modify JWT_SECRET_KEY in .env"
            fi
        else
            log_error ".env.example file does not exist"
            exit 1
        fi
    else
        log_success ".env file already exists"
    fi
}

# ============================================================================
# Create necessary directories
# ============================================================================
create_directories() {
    log_info "Creating necessary directories..."

    mkdir -p models
    mkdir -p data/uploads
    mkdir -p data/output
    mkdir -p data/db
    mkdir -p logs/backend
    mkdir -p logs/worker
    mkdir -p logs/mcp

    log_success "Directory structure created"
}

# ============================================================================
# Build images
# ============================================================================
build_images() {
    log_info "Building Docker images (first run may take 10-30 minutes)..."
    log_warning "First build requires downloading large AI packages: PaddlePaddle ~1.8GB, PyTorch ~2GB"
    echo ""

    $COMPOSE_CMD build --parallel

    log_success "Image build completed"
}

# ============================================================================
# Start services
# ============================================================================
start_services() {
    local mode=${1:-prod}

    if [ "$mode" = "dev" ]; then
        log_info "Starting development environment..."
        $COMPOSE_CMD -f docker-compose.dev.yml up -d
    else
        log_info "Starting production environment..."
        $COMPOSE_CMD up -d
    fi

    log_success "Services starting..."

    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 10

    # Check service status
    $COMPOSE_CMD ps
}

# ============================================================================
# Show access information
# ============================================================================
show_info() {
    log_success "=========================================="
    log_success "Tianshu Deployment Complete!"
    log_success "=========================================="
    echo ""
    log_info "Service access addresses:"
    echo "  - Frontend:      http://localhost:$(grep FRONTEND_PORT .env | cut -d'=' -f2 || echo 80)"
    echo "  - API Docs:      http://localhost:$(grep API_PORT .env | cut -d'=' -f2 || echo 8000)/docs"
    echo "  - Worker:        http://localhost:$(grep WORKER_PORT .env | cut -d'=' -f2 || echo 8001)"
    echo "  - MCP:           http://localhost:$(grep MCP_PORT .env | cut -d'=' -f2 || echo 8002)"
    echo ""
    log_info "Common commands:"
    echo "  - View logs:     $COMPOSE_CMD logs -f"
    echo "  - Stop services: $COMPOSE_CMD down"
    echo "  - Restart:       $COMPOSE_CMD restart"
    echo "  - View status:   $COMPOSE_CMD ps"
    echo ""
    log_warning "On first run, models will be automatically downloaded, this may take some time"
    log_warning "Default admin account needs to be created via registration page"
}

# ============================================================================
# Main menu
# ============================================================================
show_menu() {
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║   Tianshu Docker Setup Script           ║"
    echo "╚════════════════════════════════════════╝"
    echo ""
    echo "Please select an option:"
    echo "  1) Full deployment (Check dependencies + Build + Start)"
    echo "  2) Start services only (Production)"
    echo "  3) Start development environment"
    echo "  4) Stop all services"
    echo "  5) Restart services"
    echo "  6) View service status"
    echo "  7) View logs"
    echo "  8) Clean all data (Dangerous operation)"
    echo "  0) Exit"
    echo ""
    read -p "Please enter option [0-8]: " choice

    case $choice in
        1)
            check_dependencies
            setup_environment
            create_directories
            build_images
            start_services prod
            show_info
            ;;
        2)
            start_services prod
            show_info
            ;;
        3)
            setup_environment
            create_directories
            start_services dev
            show_info
            ;;
        4)
            log_info "Stopping services..."
            $COMPOSE_CMD down
            log_success "Services stopped"
            ;;
        5)
            log_info "Restarting services..."
            $COMPOSE_CMD restart
            log_success "Services restarted"
            ;;
        6)
            $COMPOSE_CMD ps
            ;;
        7)
            $COMPOSE_CMD logs -f
            ;;
        8)
            log_warning "This operation will delete all data (including database, uploaded files, models)"
            read -p "Confirm deletion? (yes/no): " confirm
            if [ "$confirm" = "yes" ]; then
                $COMPOSE_CMD down -v
                rm -rf data/ logs/ models/
                log_success "Data cleaned"
            else
                log_info "Operation cancelled"
            fi
            ;;
        0)
            log_info "Exiting"
            exit 0
            ;;
        *)
            log_error "Invalid option"
            show_menu
            ;;
    esac
}

# ============================================================================
# Entry point
# ============================================================================
main() {
    # Switch to project root directory
    cd "$(dirname "$0")/.."

    # If arguments provided, execute directly
    if [ $# -gt 0 ]; then
        case $1 in
            setup)
                check_dependencies
                setup_environment
                create_directories
                build_images
                start_services prod
                show_info
                ;;
            start)
                start_services prod
                ;;
            dev)
                start_services dev
                ;;
            stop)
                $COMPOSE_CMD down
                ;;
            *)
                log_error "Unknown command: $1"
                echo "Usage: $0 [setup|start|dev|stop]"
                exit 1
                ;;
        esac
    else
        # Show menu
        show_menu
    fi
}

main "$@"
