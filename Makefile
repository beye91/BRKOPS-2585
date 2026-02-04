# =============================================================================
# BRKOPS-2585: AI-Driven Network Operations Demo Platform
# Makefile for build, deploy, and management commands
# =============================================================================

.PHONY: help build up down restart logs clean deploy test lint format

# Default target
help:
	@echo "BRKOPS-2585 Demo Platform - Available Commands"
	@echo "=============================================="
	@echo ""
	@echo "Development:"
	@echo "  make build       - Build all containers (--no-cache)"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - Follow container logs"
	@echo "  make logs-f      - Follow specific service logs (SERVICE=backend)"
	@echo ""
	@echo "Database:"
	@echo "  make db-shell    - Open PostgreSQL shell"
	@echo "  make db-reset    - Reset database (WARNING: destroys data)"
	@echo "  make db-seed     - Re-run seed data"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy      - Deploy to production (192.168.1.213)"
	@echo "  make deploy-quick- Quick restart on production"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean       - Remove containers, volumes, and images"
	@echo "  make prune       - Docker system prune"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run all tests"
	@echo "  make test-api    - Test API endpoints"
	@echo "  make health      - Check service health"
	@echo ""

# =============================================================================
# BUILD
# =============================================================================

build:
	@echo "Building all containers with --no-cache..."
	docker compose build --no-cache

build-frontend:
	@echo "Building frontend..."
	docker compose build --no-cache frontend

build-backend:
	@echo "Building backend..."
	docker compose build --no-cache backend

# =============================================================================
# RUNTIME
# =============================================================================

up:
	@echo "Starting all services..."
	docker compose up -d
	@echo ""
	@echo "Services starting. Check status with: make health"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend:  http://localhost:8000"

down:
	@echo "Stopping all services..."
	docker compose down

restart:
	@echo "Restarting all services..."
	docker compose restart

restart-backend:
	@echo "Restarting backend..."
	docker compose restart backend

restart-frontend:
	@echo "Restarting frontend..."
	docker compose restart frontend

logs:
	docker compose logs -f

logs-f:
	docker compose logs -f $(SERVICE)

# =============================================================================
# DATABASE
# =============================================================================

db-shell:
	docker compose exec postgres psql -U brkops -d brkops2585

db-reset:
	@echo "WARNING: This will destroy all data!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	docker compose down -v
	docker volume rm -f brkops-postgres-data
	docker compose up -d postgres
	@sleep 5
	@echo "Database reset complete."

db-seed:
	docker compose exec postgres psql -U brkops -d brkops2585 -f /docker-entrypoint-initdb.d/02-seed.sql

# =============================================================================
# DEPLOYMENT
# =============================================================================

DEPLOY_HOST ?= 192.168.1.213
DEPLOY_USER ?= cbeye
DEPLOY_PATH ?= /home/$(DEPLOY_USER)/brkops-2585

deploy:
	@echo "Deploying to $(DEPLOY_HOST)..."
	@echo "Step 1: Syncing files..."
	rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '__pycache__' \
		--exclude '.env' --exclude 'postgres-data' --exclude 'redis-data' \
		./ $(DEPLOY_USER)@$(DEPLOY_HOST):$(DEPLOY_PATH)/
	@echo "Step 2: Building containers on remote..."
	ssh $(DEPLOY_USER)@$(DEPLOY_HOST) "cd $(DEPLOY_PATH) && docker compose build --no-cache"
	@echo "Step 3: Starting services..."
	ssh $(DEPLOY_USER)@$(DEPLOY_HOST) "cd $(DEPLOY_PATH) && docker compose up -d"
	@echo "Step 4: Cleaning old images..."
	ssh $(DEPLOY_USER)@$(DEPLOY_HOST) "docker image prune -f"
	@echo ""
	@echo "Deployment complete!"
	@echo "Frontend: http://$(DEPLOY_HOST):3000"
	@echo "Backend:  http://$(DEPLOY_HOST):8000"

deploy-quick:
	@echo "Quick restart on $(DEPLOY_HOST)..."
	ssh $(DEPLOY_USER)@$(DEPLOY_HOST) "cd $(DEPLOY_PATH) && docker compose restart"

deploy-logs:
	ssh $(DEPLOY_USER)@$(DEPLOY_HOST) "cd $(DEPLOY_PATH) && docker compose logs -f"

# =============================================================================
# CLEANUP
# =============================================================================

clean:
	@echo "Stopping services and removing volumes..."
	docker compose down -v --rmi local
	docker image prune -f
	@echo "Cleanup complete."

prune:
	@echo "Running Docker system prune..."
	docker system prune -af --volumes

# Remove old images after rebuild
clean-images:
	@echo "Removing dangling images..."
	docker image prune -f

# =============================================================================
# TESTING
# =============================================================================

test:
	@echo "Running all tests..."
	docker compose exec backend pytest -v

test-api:
	@echo "Testing API endpoints..."
	@echo "Health check:"
	curl -s http://localhost:8000/health | jq .
	@echo ""
	@echo "API docs available at: http://localhost:8000/docs"

health:
	@echo "Checking service health..."
	@echo ""
	@echo "Container Status:"
	@docker compose ps
	@echo ""
	@echo "Health Endpoints:"
	@echo -n "Backend:  " && curl -sf http://localhost:8000/health && echo " OK" || echo "FAILED"
	@echo -n "Frontend: " && curl -sf http://localhost:3000 > /dev/null && echo "OK" || echo "FAILED"
	@echo -n "Postgres: " && docker compose exec -T postgres pg_isready -U brkops && echo "" || echo "FAILED"
	@echo -n "Redis:    " && docker compose exec -T redis redis-cli ping || echo "FAILED"

# =============================================================================
# DEVELOPMENT
# =============================================================================

dev-backend:
	@echo "Starting backend in development mode..."
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "Starting frontend in development mode..."
	cd frontend && npm run dev

# =============================================================================
# GITLAB
# =============================================================================

GITLAB_REGISTRY ?= 192.168.1.220:5050
GITLAB_PROJECT ?= root/brkops-2585

gitlab-login:
	docker login $(GITLAB_REGISTRY)

gitlab-push:
	@echo "Pushing images to GitLab registry..."
	docker tag brkops-2585-backend $(GITLAB_REGISTRY)/$(GITLAB_PROJECT)/backend:latest
	docker tag brkops-2585-frontend $(GITLAB_REGISTRY)/$(GITLAB_PROJECT)/frontend:latest
	docker push $(GITLAB_REGISTRY)/$(GITLAB_PROJECT)/backend:latest
	docker push $(GITLAB_REGISTRY)/$(GITLAB_PROJECT)/frontend:latest
