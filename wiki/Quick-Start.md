# Quick Start Guide

Complete reference for running the F1 Race Strategy Workbench.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Running the Application](#running-the-application)
4. [Development Commands](#development-commands)
5. [Testing Commands](#testing-commands)
6. [Docker Commands](#docker-commands)
7. [Makefile Reference](#makefile-reference)

---

## Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | 2.0+ | `git --version` |

---

## Installation

### Clone Repository
```bash
git clone https://github.com/your-org/f1-strategy-workbench.git
cd f1-strategy-workbench
```

### Python Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate (macOS/Linux)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

### Install Dependencies
```bash
# Python dependencies
pip install -r requirements.txt

# Development dependencies (optional)
pip install -r requirements-dev.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Quick Install (One Command)
```bash
make install
```

---

## Running the Application

### Using run.py (Recommended)

```bash
# Run full program (default)
python run.py

# Run frontend only
python run.py --frontend

# Run on custom port
python run.py --port 3000

# Run in production mode
python run.py --prod
```

### Using Make

```bash
# Run full program
make run

# Run full program
make run-all

# Run in development mode with hot reload
make dev
```

### Using Uvicorn Directly

```bash
# Development (with reload)
uvicorn rsw.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn rsw.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Access Points

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |
| Frontend | http://localhost:5173 |
| WebSocket | ws://localhost:8000/ws |

---

## Development Commands

### Code Formatting

```bash
# Format code with Ruff
python run.py --format

# Or using Make
make format
```

### Linting

```bash
# Lint code
python run.py --lint

# Or using Make
make lint
```

### Type Checking

```bash
# Run MyPy type checker
python run.py --typecheck

# Or using Make
make typecheck
```

### All Quality Checks

```bash
# Run all checks (lint + format + typecheck)
make check
```

---

## Testing Commands

### Run All Tests

```bash
# Using run.py
python run.py --test

# Using Make
make test

# Using pytest directly
PYTHONPATH=src pytest tests/ -v
```

### Run Specific Test Categories

```bash
# Run only strategy tests
PYTHONPATH=src pytest tests/test_strategy.py -v

# Run only API tests
PYTHONPATH=src pytest tests/test_api_endpoints.py -v

# Run only integration tests
PYTHONPATH=src pytest tests/test_integration.py -v
```

### Run with Coverage

```bash
# Generate coverage report
python run.py --coverage

# Or using Make
make coverage

# Using pytest directly
PYTHONPATH=src pytest tests/ --cov=src/rsw --cov-report=html
```

### Run Single Test

```bash
# Run specific test function
PYTHONPATH=src pytest tests/test_strategy.py::TestPitWindow::test_find_optimal_window_early_race -v
```

---

## Docker Commands

### Build and Run

```bash
# Build Docker image
docker build -t rsw:latest .

# Run container
docker run -p 8000:8000 rsw:latest

# Or using docker-compose
docker-compose up --build

# Using Make
make docker
```

### Docker Compose Services

```bash
# Start all services (app + redis + postgres)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild and restart
docker-compose up --build -d
```

### Container Management

```bash
# List running containers
docker ps

# Enter container shell
docker exec -it rsw bash

# View container logs
docker logs rsw -f

# Stop container
docker stop rsw
```

---

## Makefile Reference

Complete list of available Make commands:

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies |
| `make run` | Run backend server |
| `make run-all` | Run backend + frontend |
| `make dev` | Run in development mode |
| `make test` | Run all tests |
| `make coverage` | Run tests with coverage |
| `make lint` | Run linter |
| `make format` | Format code |
| `make typecheck` | Run type checker |
| `make check` | Run all quality checks |
| `make docker` | Build and run Docker |
| `make clean` | Clean build artifacts |
| `make help` | Show all commands |

---

## Environment Variables

Set these before running:

```bash
# Required
export RSW_ENV=development

# Optional
export RSW_PORT=8000
export RSW_LOG_LEVEL=INFO
export RSW_DEBUG=true
export OPENF1_BASE_URL=https://api.openf1.org/v1

# Database (optional)
export DATABASE_URL=postgresql://user:pass@localhost:5432/rsw
export REDIS_URL=redis://localhost:6379/0

# Authentication (optional)
export JWT_SECRET=your-secret-key
export JWT_ALGORITHM=HS256
```

Or create a `.env` file:

```env
RSW_ENV=development
RSW_PORT=8000
RSW_LOG_LEVEL=INFO
```

---

## Troubleshooting Quick Commands

```bash
# Check Python version
python --version

# Check installed packages
pip list

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +

# Clear test cache
rm -rf .pytest_cache

# Verify imports work
python -c "from rsw.main import app; print('OK')"
```

---

## Next Steps

- Read the [Development Guide](DEVELOPMENT.md) for coding standards
- Check the [API Reference](API.md) for endpoint documentation
- See [Deployment Guide](DEPLOYMENT.md) for production setup

---
**Next:** [[User-Guide]]
