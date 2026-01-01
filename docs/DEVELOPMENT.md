# Development Guide

Complete guide for contributing to the F1 Race Strategy Workbench.

---

## Table of Contents

1. [Development Setup](#development-setup)
2. [Project Structure](#project-structure)
3. [Code Style](#code-style)
4. [Testing](#testing)
5. [Type Checking](#type-checking)
6. [Git Workflow](#git-workflow)
7. [Adding Features](#adding-features)
8. [Debugging](#debugging)
9. [IDE Configuration](#ide-configuration)

---

## Development Setup

### Prerequisites

| Requirement | Version | Installation |
|-------------|---------|--------------|
| Python | 3.11+ | [python.org](https://www.python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Git | 2.0+ | [git-scm.com](https://git-scm.com) |

### Initial Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-org/f1-strategy-workbench.git
cd f1-strategy-workbench

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Install pre-commit hooks
pre-commit install

# 5. Verify setup
python run.py --test
```

### Environment Variables

Create a `.env` file:

```env
RSW_ENV=development
RSW_DEBUG=true
RSW_LOG_LEVEL=DEBUG
```

---

## Project Structure

```
F1/
├── src/rsw/                    # Main Python package
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration loading
│   ├── exceptions.py           # Custom exceptions
│   ├── interfaces.py           # Abstract base classes
│   ├── container.py            # Dependency injection
│   ├── utils.py                # Shared utilities
│   ├── domain.py               # Value objects
│   ├── factories.py            # Factory patterns
│   │
│   ├── api/                    # REST API
│   │   └── routes/             # Route handlers
│   │
│   ├── ingest/                 # Data ingestion
│   │   ├── base.py             # DataProvider interface
│   │   └── openf1_client.py    # OpenF1 implementation
│   │
│   ├── state/                  # State management
│   │   ├── schemas.py          # Pydantic models
│   │   ├── store.py            # State store
│   │   └── reducers.py         # Pure update functions
│   │
│   ├── models/                 # ML models
│   │   ├── degradation/        # Tyre degradation
│   │   └── features/           # Feature engineering
│   │
│   ├── strategy/               # Strategy engine
│   │   ├── pit_window.py       # Pit window calc
│   │   ├── monte_carlo.py      # Simulations
│   │   └── decision.py         # Recommendations
│   │
│   ├── services/               # Business logic
│   └── middleware/             # HTTP middleware
│
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── services/
│   └── package.json
│
├── tests/                      # Test suite
│   ├── test_api_endpoints.py
│   ├── test_strategy.py
│   ├── test_integration.py
│   └── conftest.py
│
├── docs/                       # Documentation
├── run.py                      # CLI entry point
├── Makefile                    # Make commands
├── pyproject.toml              # Project config
└── requirements.txt            # Dependencies
```

---

## Code Style

### Python Style Guide

We follow **PEP 8** with these additions:

| Rule | Setting |
|------|---------|
| Line length | 100 characters |
| Quotes | Double quotes for strings |
| Imports | Sorted with isort |
| Type hints | Required for public APIs |

### Ruff Configuration

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B"]
ignore = ["E501"]
```

### Running Linters

```bash
# Lint code
python run.py --lint

# Format code
python run.py --format

# Or using Make
make lint
make format
```

### Import Order

```python
# Standard library
import asyncio
from datetime import datetime
from typing import Any

# Third-party
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

# Local
from rsw.config import load_app_config
from rsw.state import RaceState
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_pit_window(
    current_lap: int,
    total_laps: int,
    deg_slope: float,
) -> PitWindow:
    """
    Calculate optimal pit stop window.

    Args:
        current_lap: Current race lap.
        total_laps: Total race laps.
        deg_slope: Degradation rate (s/lap).

    Returns:
        PitWindow with min, max, and ideal lap.

    Raises:
        InsufficientDataError: If not enough laps for calculation.
    """
```

---

## Testing

### Test Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── test_api_endpoints.py       # API tests
├── test_strategy.py            # Strategy engine tests
├── test_rls.py                 # RLS estimator tests
├── test_degradation_model.py   # Degradation model tests
├── test_features.py            # Feature engineering tests
├── test_integration.py         # End-to-end tests
└── test_prediction_accuracy.py # Accuracy benchmarks
```

### Running Tests

```bash
# All tests
python run.py --test

# Specific file
PYTHONPATH=src pytest tests/test_strategy.py -v

# Specific test
PYTHONPATH=src pytest tests/test_strategy.py::TestPitWindow::test_find_optimal_window -v

# With coverage
python run.py --coverage
```

### Writing Tests

```python
import pytest
from rsw.strategy.pit_window import find_optimal_window, PitWindow


class TestPitWindow:
    """Tests for pit window calculations."""

    def test_find_optimal_window_early_race(self):
        """Test window calculation in early race."""
        window = find_optimal_window(
            current_lap=10,
            total_laps=50,
            deg_slope=0.05,
            current_pace=92.0,
            pit_loss=22.0,
            tyre_age=5,
            compound="MEDIUM",
            cliff_risk=0.3,
        )

        assert window.min_lap >= 10
        assert window.max_lap <= 50
        assert window.min_lap <= window.ideal_lap <= window.max_lap

    @pytest.mark.asyncio
    async def test_async_function(self):
        """Test async functionality."""
        result = await some_async_function()
        assert result is not None
```

### Fixtures

```python
# conftest.py
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from rsw.main import app
    return TestClient(app)


@pytest.fixture
def sample_race_state():
    """Create sample race state."""
    return RaceState(
        session_key=9999,
        session_name="Test Race",
        current_lap=25,
        total_laps=50,
    )
```

---

## Type Checking

### MyPy Configuration

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true
```

### Running Type Checker

```bash
python run.py --typecheck

# Or directly
mypy src/rsw --strict
```

### Type Annotations

```python
from typing import Any, Optional
from collections.abc import Callable


def process_data(
    data: list[dict[str, Any]],
    callback: Callable[[dict], None] | None = None,
) -> dict[str, float]:
    """Process data with optional callback."""
    ...
```

---

## Git Workflow

### Branch Naming

| Prefix | Use Case |
|--------|----------|
| `feature/` | New features |
| `fix/` | Bug fixes |
| `refactor/` | Code refactoring |
| `docs/` | Documentation |
| `test/` | Adding tests |

**Example:** `feature/monte-carlo-visualization`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
```
feat(strategy): add Monte Carlo simulation visualization
fix(api): handle missing driver data gracefully
docs(readme): update quick start instructions
```

### Pull Request Process

1. Create feature branch from `main`
2. Make changes with tests
3. Run all checks: `make check`
4. Push and create PR
5. Wait for CI and review
6. Squash and merge

---

## Adding Features

### Step-by-Step Guide

#### 1. Create Interface (if needed)

```python
# src/rsw/interfaces.py
class INewFeature(ABC):
    @abstractmethod
    def process(self, data: Data) -> Result:
        """Process data and return result."""
        pass
```

#### 2. Implement Feature

```python
# src/rsw/features/new_feature.py
from rsw.interfaces import INewFeature


class NewFeature(INewFeature):
    def __init__(self, config: Config) -> None:
        self._config = config

    def process(self, data: Data) -> Result:
        # Implementation
        return result
```

#### 3. Add Tests

```python
# tests/test_new_feature.py
class TestNewFeature:
    def test_process_valid_data(self):
        feature = NewFeature(config)
        result = feature.process(valid_data)
        assert result.valid is True
```

#### 4. Register in Container

```python
# src/rsw/container.py
Container.register(INewFeature, NewFeature(config))
```

#### 5. Add API Endpoint (if needed)

```python
# src/rsw/api/routes/new_feature.py
@router.get("/api/new-feature")
async def get_new_feature():
    feature = Container.get(INewFeature)
    return feature.process(data)
```

---

## Debugging

### Logging

```python
from rsw.logging_config import get_logger

logger = get_logger(__name__)

logger.info("Processing started", driver=44, lap=25)
logger.warning("High degradation detected", deg_slope=0.12)
logger.error("API request failed", error=str(e))
```

### Debug Mode

```bash
# Enable debug logging
export RSW_DEBUG=true
export RSW_LOG_LEVEL=DEBUG

python run.py
```

### VS Code Debugging

`.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["rsw.main:app", "--reload", "--port", "8000"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    },
    {
      "name": "Python: Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["tests/", "-v"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    }
  ]
}
```

---

## IDE Configuration

### VS Code Extensions

| Extension | Purpose |
|-----------|---------|
| Python | Python language support |
| Pylance | Type checking |
| Ruff | Linting & formatting |
| Python Test Explorer | Test UI |
| GitLens | Git integration |

### VS Code Settings

`.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.analysis.typeCheckingMode": "basic",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "ruff.enable": true,
  "ruff.organizeImports": true
}
```

### PyCharm

1. Set Project Interpreter: `.venv/bin/python`
2. Mark `src/` as Sources Root
3. Mark `tests/` as Tests Root
4. Enable Ruff plugin

---

## Next Steps

- [API Reference](API.md) — Endpoint documentation
- [Architecture](ARCHITECTURE.md) — System design
- [Deployment](DEPLOYMENT.md) — Production setup
