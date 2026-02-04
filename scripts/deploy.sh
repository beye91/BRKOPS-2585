#!/bin/bash
# =============================================================================
# BRKOPS-2585 Deployment Script
# =============================================================================
# Deploy the AI-Driven Network Operations Platform to production host
#
# Usage:
#   ./scripts/deploy.sh [OPTIONS]
#
# Options:
#   --full      Full rebuild with no cache
#   --quick     Quick restart without rebuild
#   --logs      Show logs after deployment
#   --help      Show this help message
# =============================================================================

set -e

# Configuration
HOST="192.168.1.213"
USER="cbeye"
DEPLOY_PATH="/opt/brkops-2585"
PROJECT_NAME="brkops-2585"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
FULL_REBUILD=false
QUICK_RESTART=false
SHOW_LOGS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            FULL_REBUILD=true
            shift
            ;;
        --quick)
            QUICK_RESTART=true
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        --help)
            echo "BRKOPS-2585 Deployment Script"
            echo ""
            echo "Usage: ./scripts/deploy.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --full      Full rebuild with no cache"
            echo "  --quick     Quick restart without rebuild"
            echo "  --logs      Show logs after deployment"
            echo "  --help      Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Functions
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

# Check SSH connectivity
check_connectivity() {
    log_info "Checking connectivity to $HOST..."
    if ssh -o ConnectTimeout=5 "$USER@$HOST" "echo 'Connected'" &>/dev/null; then
        log_success "SSH connection successful"
    else
        log_error "Cannot connect to $HOST"
        exit 1
    fi
}

# Quick restart (no rebuild)
quick_restart() {
    log_info "Performing quick restart..."

    ssh "$USER@$HOST" << EOF
        cd $DEPLOY_PATH
        echo "Restarting containers..."
        docker compose restart

        echo "Waiting for services to start..."
        sleep 15

        echo "Checking health..."
        curl -s http://localhost:8000/health | head -c 200
        echo ""
EOF

    log_success "Quick restart complete"
}

# Sync files to remote host
sync_files() {
    log_info "Syncing files to $HOST:$DEPLOY_PATH..."

    # Create deployment directory if it doesn't exist
    ssh "$USER@$HOST" "mkdir -p $DEPLOY_PATH"

    # Sync files excluding development artifacts
    rsync -avz --delete \
        --exclude 'node_modules' \
        --exclude '.git' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.env' \
        --exclude '.venv' \
        --exclude 'venv' \
        --exclude '.next' \
        --exclude 'dist' \
        --exclude 'build' \
        --exclude '*.log' \
        --exclude '.DS_Store' \
        ./ "$USER@$HOST:$DEPLOY_PATH/"

    log_success "Files synced successfully"
}

# Deploy with full rebuild
full_deploy() {
    log_info "Performing full deployment..."

    ssh "$USER@$HOST" << 'EOF'
        set -e
        cd /opt/brkops-2585

        echo "=== Stopping existing containers ==="
        docker compose down || true

        echo "=== Cleaning up old images ==="
        # Remove dangling images
        docker image prune -f

        # Remove old project images
        docker images --format '{{.Repository}}:{{.Tag}}' | grep 'brkops' | xargs -r docker rmi -f || true

        echo "=== Building with no cache ==="
        docker compose build --no-cache

        echo "=== Starting services ==="
        docker compose up -d

        echo "=== Waiting for services to initialize ==="
        sleep 30

        echo "=== Checking container status ==="
        docker compose ps

        echo "=== Health check ==="
        for i in {1..5}; do
            if curl -sf http://localhost:8000/health > /dev/null; then
                echo "Backend is healthy!"
                curl -s http://localhost:8000/health | head -c 200
                echo ""
                break
            fi
            echo "Waiting for backend... attempt $i/5"
            sleep 10
        done

        echo "=== Checking frontend ==="
        curl -I http://localhost:3000 2>/dev/null | head -1 || echo "Frontend check completed"

        echo ""
        echo "=== Deployment Complete ==="
EOF

    log_success "Full deployment complete"
}

# Standard deploy (rebuild only changed)
standard_deploy() {
    log_info "Performing standard deployment..."

    ssh "$USER@$HOST" << 'EOF'
        set -e
        cd /opt/brkops-2585

        echo "=== Building containers ==="
        docker compose build --no-cache

        echo "=== Recreating containers ==="
        docker compose up -d --force-recreate

        echo "=== Cleaning up ==="
        docker image prune -f

        echo "=== Waiting for services ==="
        sleep 20

        echo "=== Health check ==="
        curl -s http://localhost:8000/health || echo "Health check pending..."

        echo ""
        echo "=== Deployment Complete ==="
EOF

    log_success "Standard deployment complete"
}

# Show logs
show_logs() {
    log_info "Showing recent logs..."

    ssh "$USER@$HOST" << 'EOF'
        cd /opt/brkops-2585
        echo "=== Backend Logs ==="
        docker compose logs --tail=50 backend
        echo ""
        echo "=== Frontend Logs ==="
        docker compose logs --tail=20 frontend
EOF
}

# Print deployment info
print_info() {
    echo ""
    echo -e "${GREEN}=== BRKOPS-2585 Deployed ===${NC}"
    echo ""
    echo -e "  ${BLUE}Demo UI:${NC}      http://$HOST:3000/demo"
    echo -e "  ${BLUE}Admin Panel:${NC}  http://$HOST:3000/admin"
    echo -e "  ${BLUE}API Health:${NC}   http://$HOST:8000/health"
    echo -e "  ${BLUE}API Docs:${NC}     http://$HOST:8000/docs"
    echo ""
    echo -e "  ${YELLOW}SSH:${NC}          ssh $USER@$HOST"
    echo -e "  ${YELLOW}Logs:${NC}         docker compose logs -f"
    echo ""
}

# Main execution
main() {
    echo ""
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}  BRKOPS-2585 Deployment Script${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""

    check_connectivity

    if [ "$QUICK_RESTART" = true ]; then
        quick_restart
    else
        sync_files

        if [ "$FULL_REBUILD" = true ]; then
            full_deploy
        else
            standard_deploy
        fi
    fi

    if [ "$SHOW_LOGS" = true ]; then
        show_logs
    fi

    print_info
}

# Run main
main
