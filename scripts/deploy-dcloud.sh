#!/bin/bash
# =============================================================================
# BRKOPS-2585 dCloud Deployment Script
# =============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}BRKOPS-2585 dCloud Deployment${NC}"
echo -e "${BLUE}=================================================================${NC}"

# Configuration
DCLOUD_HOST="198.18.134.22"
CML_MCP_PORT="9001"
FRONTEND_PORT="3003"
BACKEND_PORT="8003"
POSTGRES_PORT="5434"
REDIS_PORT="6380"

cd "$PROJECT_DIR"

# Check if .env.dcloud exists
if [ ! -f ".env.dcloud" ]; then
    echo -e "${RED}Error: .env.dcloud not found. Please configure it first.${NC}"
    exit 1
fi

# Copy .env.dcloud to .env for docker-compose
cp .env.dcloud .env

echo -e "${YELLOW}Step 1: Cleaning up old containers and images...${NC}"
docker compose -f docker-compose.dcloud.yml down --remove-orphans 2>/dev/null || true
docker system prune -f 2>/dev/null || true

echo -e "${YELLOW}Step 2: Building containers (no cache)...${NC}"
docker compose -f docker-compose.dcloud.yml build --no-cache

echo -e "${YELLOW}Step 3: Starting infrastructure services (PostgreSQL, Redis)...${NC}"
docker compose -f docker-compose.dcloud.yml up -d postgres redis

echo -e "${YELLOW}Waiting for database to be ready...${NC}"
sleep 10

# Wait for postgres to be healthy
until docker exec brkops-postgres-dcloud pg_isready -U brkops -d brkops2585 2>/dev/null; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done

echo -e "${GREEN}PostgreSQL is ready!${NC}"

echo -e "${YELLOW}Step 4: Starting backend service...${NC}"
docker compose -f docker-compose.dcloud.yml up -d backend

echo -e "${YELLOW}Waiting for backend to be healthy...${NC}"
sleep 15

# Wait for backend health
until curl -s http://localhost:${BACKEND_PORT}/health > /dev/null 2>&1; do
    echo "Waiting for backend..."
    sleep 3
done

echo -e "${GREEN}Backend is healthy!${NC}"

echo -e "${YELLOW}Step 5: Starting frontend service...${NC}"
docker compose -f docker-compose.dcloud.yml up -d frontend

echo -e "${YELLOW}Waiting for frontend to be ready...${NC}"
sleep 20

echo -e "${YELLOW}Step 6: Deploying CML MCP Server...${NC}"
# Stop and remove old CML MCP container if exists
docker stop cml-mcp-server-dcloud 2>/dev/null || true
docker rm cml-mcp-server-dcloud 2>/dev/null || true

# Deploy CML MCP Server
docker run -d \
  --name cml-mcp-server-dcloud \
  --restart unless-stopped \
  --network brkops-dcloud-network \
  -p ${CML_MCP_PORT}:9001 \
  -e CML_MCP_TRANSPORT=http \
  -e CML_MCP_BIND=0.0.0.0 \
  -e CML_MCP_PORT=9001 \
  -e CML_URL=https://198.18.130.201 \
  -e CML_USERNAME=admin \
  -e CML_PASSWORD=C1sco12345 \
  -e CML_VERIFY_SSL=false \
  -e PYATS_USERNAME=admin \
  -e PYATS_PASSWORD=cisco \
  -e DEBUG=false \
  xorrkaz/cml-mcp:latest

echo -e "${YELLOW}Waiting for CML MCP Server...${NC}"
sleep 10

echo -e "${BLUE}=================================================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo ""
echo -e "Services running on ${DCLOUD_HOST}:"
echo -e "  Frontend:     http://${DCLOUD_HOST}:${FRONTEND_PORT}"
echo -e "  Backend API:  http://${DCLOUD_HOST}:${BACKEND_PORT}"
echo -e "  Admin Panel:  http://${DCLOUD_HOST}:${FRONTEND_PORT}/admin"
echo -e "  Demo Page:    http://${DCLOUD_HOST}:${FRONTEND_PORT}/demo"
echo -e "  CML MCP:      http://${DCLOUD_HOST}:${CML_MCP_PORT}"
echo ""
echo -e "${YELLOW}Verification Commands:${NC}"
echo "  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
echo "  curl http://${DCLOUD_HOST}:${BACKEND_PORT}/health"
echo "  docker logs brkops-backend-dcloud"
echo ""
echo -e "${BLUE}=================================================================${NC}"
