# Makefile for ComfyUI-3D-Pack
# Provides convenient commands for development and deployment

.PHONY: help install test lint format clean docker-build docker-run

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
DOCKER := docker
DOCKER_COMPOSE := docker-compose
IMAGE_NAME := comfyui-3d-pack
VERSION := 0.1.6

## help: Show this help message
help:
	@echo "ComfyUI-3D-Pack - Makefile Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@sed -n 's/^##//p' ${MAKEFILE_LIST} | column -t -s ':' | sed -e 's/^/ /'

## install: Install all dependencies
install:
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "✓ Installation complete"

## install-dev: Install development dependencies
install-dev: install
	@echo "Installing development dependencies..."
	$(PIP) install pytest pytest-cov pytest-asyncio pytest-mock
	$(PIP) install ruff black mypy isort bandit
	$(PIP) install pre-commit
	@echo "✓ Development installation complete"

## test: Run all tests
test:
	@echo "Running tests..."
	pytest -v --cov=. --cov-report=term-missing --cov-report=html

## test-unit: Run unit tests only
test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v -m "unit"

## test-security: Run security tests only
test-security:
	@echo "Running security tests..."
	pytest tests/unit/ -v -m "security"

## test-watch: Run tests in watch mode
test-watch:
	@echo "Running tests in watch mode..."
	pytest-watch

## lint: Run all linters
lint:
	@echo "Running linters..."
	ruff check .
	black --check .
	isort --check-only .
	mypy .
	bandit -r . -c pyproject.toml

## format: Format code with black and isort
format:
	@echo "Formatting code..."
	black .
	isort .
	@echo "✓ Code formatted"

## security: Run security checks
security:
	@echo "Running security checks..."
	bandit -r . -c pyproject.toml -f json -o bandit-report.json
	@echo "✓ Security scan complete (see bandit-report.json)"

## clean: Clean up generated files
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf htmlcov/ coverage.xml .coverage
	rm -rf build/ dist/
	@echo "✓ Cleanup complete"

## docker-build: Build Docker image
docker-build:
	@echo "Building Docker image..."
	$(DOCKER) build -f Dockerfile.enterprise -t $(IMAGE_NAME):$(VERSION) -t $(IMAGE_NAME):latest .
	@echo "✓ Docker image built: $(IMAGE_NAME):$(VERSION)"

## docker-run: Run Docker container
docker-run:
	@echo "Running Docker container..."
	$(DOCKER) run -d \
		--name $(IMAGE_NAME) \
		--gpus all \
		-p 8188:8188 \
		-v $(PWD)/models:/app/models \
		-v $(PWD)/output:/app/output \
		--env-file .env \
		$(IMAGE_NAME):latest
	@echo "✓ Container started: $(IMAGE_NAME)"

## docker-stop: Stop Docker container
docker-stop:
	@echo "Stopping Docker container..."
	$(DOCKER) stop $(IMAGE_NAME) || true
	$(DOCKER) rm $(IMAGE_NAME) || true
	@echo "✓ Container stopped"

## docker-logs: Show Docker container logs
docker-logs:
	$(DOCKER) logs -f $(IMAGE_NAME)

## compose-up: Start all services with docker-compose
compose-up:
	@echo "Starting services..."
	$(DOCKER_COMPOSE) up -d
	@echo "✓ Services started"

## compose-up-full: Start all services including monitoring
compose-up-full:
	@echo "Starting all services with monitoring..."
	$(DOCKER_COMPOSE) --profile full --profile monitoring up -d
	@echo "✓ All services started"

## compose-down: Stop all services
compose-down:
	@echo "Stopping services..."
	$(DOCKER_COMPOSE) down
	@echo "✓ Services stopped"

## compose-logs: Show logs from all services
compose-logs:
	$(DOCKER_COMPOSE) logs -f

## dev: Start development environment
dev:
	@echo "Starting development environment..."
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up

## health: Check service health
health:
	@echo "Checking service health..."
	@curl -f http://localhost:8188/health || echo "Service not healthy"

## metrics: Show Prometheus metrics
metrics:
	@echo "Fetching metrics..."
	@curl -s http://localhost:8188/metrics

## generate-key: Generate a new API key
generate-key:
	@echo "Generated API Key:"
	@$(PYTHON) -c "import secrets; print(secrets.token_hex(32))"
	@echo ""
	@echo "Add this to your .env file:"
	@echo "API_KEYS=<paste-key-here>"

## pre-commit: Run pre-commit hooks on all files
pre-commit:
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files

## coverage: Generate and open coverage report
coverage:
	@echo "Generating coverage report..."
	pytest --cov=. --cov-report=html
	@echo "Opening coverage report..."
	@which xdg-open > /dev/null && xdg-open htmlcov/index.html || \
	which open > /dev/null && open htmlcov/index.html || \
	echo "Please open htmlcov/index.html manually"

## version: Show version information
version:
	@echo "ComfyUI-3D-Pack version: $(VERSION)"
	@$(PYTHON) --version
	@$(DOCKER) --version

## init-env: Initialize .env file from example
init-env:
	@if [ -f .env ]; then \
		echo ".env already exists. Skipping..."; \
	else \
		cp .env.example .env; \
		echo "✓ Created .env from .env.example"; \
		echo "Please edit .env and add your configuration"; \
	fi

## check: Run all quality checks (lint + test + security)
check: lint test security
	@echo "✓ All checks passed"

## ci: Run CI pipeline locally
ci: install-dev check
	@echo "✓ CI pipeline complete"

## prod-check: Pre-production checklist
prod-check:
	@echo "Production Deployment Checklist:"
	@echo ""
	@echo "[ ] .env configured with production values"
	@echo "[ ] API_KEYS set with strong, unique keys"
	@echo "[ ] ENABLE_AUTH=true"
	@echo "[ ] LOG_FORMAT=json"
	@echo "[ ] ALLOWED_IPS configured for production network"
	@echo "[ ] TLS/SSL enabled (reverse proxy)"
	@echo "[ ] Health checks configured"
	@echo "[ ] Monitoring set up (Prometheus/Grafana)"
	@echo "[ ] Backups configured"
	@echo "[ ] Secrets not in version control"
	@echo ""
	@read -p "Have you completed all items? (y/N): " confirm && [ "$$confirm" = "y" ]
