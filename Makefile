# =============================================================================
# F1 Race Strategy Workbench - Makefile
# =============================================================================
# Usage:
#   make run        - Start full application
#   make backend    - Start backend only
#   make frontend   - Start frontend only
#   make test       - Run all tests
#   make coverage   - Run tests with coverage
#   make lint       - Run linter
#   make format     - Format code
#   make install    - Install all dependencies
#   make docker     - Run with Docker
#   make clean      - Clean build artifacts

.PHONY: run backend frontend test coverage lint format install docker clean help

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := pip3
NPM := npm

# =============================================================================
# Main Commands
# =============================================================================

run: ## Start full application (backend + frontend)
	@$(PYTHON) run.py

backend: ## Start backend server only
	@$(PYTHON) run.py --backend --dev

frontend: ## Start frontend dev server only
	@$(PYTHON) run.py --frontend

dev: ## Start in development mode with auto-reload
	@$(PYTHON) run.py --dev

# =============================================================================
# Testing
# =============================================================================

test: ## Run all tests
	@$(PYTHON) run.py --test

test-unit: ## Run unit tests only
	@$(PYTHON) run.py --test unit

test-api: ## Run API tests only
	@$(PYTHON) run.py --test api

test-strategy: ## Run strategy tests only
	@$(PYTHON) run.py --test strategy

coverage: ## Run tests with coverage report
	@$(PYTHON) run.py --coverage

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run linter
	@$(PYTHON) run.py --lint

format: ## Format code
	@$(PYTHON) run.py --format

typecheck: ## Run type checking
	@$(PYTHON) run.py --typecheck

check: lint typecheck ## Run all code quality checks

# =============================================================================
# Installation
# =============================================================================

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install Python dependencies
	@echo "📦 Installing Python dependencies..."
	@$(PIP) install -r requirements.txt

install-frontend: ## Install Node.js dependencies
	@echo "📦 Installing frontend dependencies..."
	@cd frontend && $(NPM) install

# =============================================================================
# Data
# =============================================================================

download: ## Download session data (usage: make download YEAR=2023 ROUND=1)
	@$(PYTHON) run.py --download $(YEAR) $(ROUND)

# =============================================================================
# Docker
# =============================================================================

docker: ## Start all services with Docker
	@docker-compose up -d
	@echo "🐳 Services started:"
	@echo "   Frontend: http://localhost:5173"
	@echo "   Backend:  http://localhost:8000"
	@echo "   Grafana:  http://localhost:3000"

docker-build: ## Build Docker images
	@docker-compose build

docker-stop: ## Stop Docker services
	@docker-compose down

docker-logs: ## View Docker logs
	@docker-compose logs -f

# =============================================================================
# Cleanup
# =============================================================================

clean: ## Clean build artifacts
	@echo "🧹 Cleaning..."
	@rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	@rm -rf src/**/__pycache__ tests/__pycache__
	@rm -rf coverage_html htmlcov .coverage
	@rm -rf frontend/node_modules frontend/dist
	@rm -rf *.egg-info dist build
	@echo "Done!"

clean-cache: ## Clean Python cache only
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true

# =============================================================================
# Help
# =============================================================================

help: ## Show this help message
	@echo "F1 Race Strategy Workbench"
	@echo "=========================="
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
