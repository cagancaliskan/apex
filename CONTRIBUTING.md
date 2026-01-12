# Contributing to F1 Race Strategy Workbench

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [How to Contribute](#how-to-contribute)
4. [Development Process](#development-process)
5. [Pull Request Guidelines](#pull-request-guidelines)
6. [Coding Standards](#coding-standards)
7. [Testing Requirements](#testing-requirements)
8. [Documentation](#documentation)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold this code.

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Accept responsibility for mistakes

---

## Getting Started

### Prerequisites

- Python 3.11+
- Git
- Node.js 18+ (for frontend)

### Setup

```bash
# Fork and clone
git clone https://github.com/cagancaliskan/apex.git
cd f1-strategy-workbench

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests to verify setup
python run.py --test
```

---

## How to Contribute

### Reporting Bugs

1. Check existing issues first
2. Create a new issue with:
   - Clear title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version)
   - Error messages/stack traces

### Suggesting Features

1. Check existing feature requests
2. Create an issue describing:
   - The problem it solves
   - Proposed solution
   - Alternative approaches considered
   - Potential impact

### Submitting Code

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

---

## Development Process

### Branch Naming

```
feature/add-monte-carlo-visualization
fix/websocket-reconnection
docs/update-api-reference
refactor/strategy-engine
test/add-integration-tests
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `style` - Formatting (no code change)
- `refactor` - Code refactoring
- `test` - Adding tests
- `chore` - Maintenance tasks

**Examples:**
```
feat(strategy): add undercut probability calculation

Add new method to calculate probability of successful undercut
based on gap to car ahead and degradation differential.

Closes #123
```

---

## Pull Request Guidelines

### Before Submitting

- [ ] Tests pass locally (`python run.py --test`)
- [ ] Code is formatted (`python run.py --format`)
- [ ] Linting passes (`python run.py --lint`)
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventions

### PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested the changes.

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Changelog updated
```

### Review Process

1. Create PR against `main` branch
2. CI checks must pass
3. Request review from maintainers
4. Address feedback
5. Maintainer approves and merges

---

## Coding Standards

### Python Style

- Follow PEP 8
- Use type hints for public APIs
- Write docstrings (Google style)
- Maximum line length: 100 characters

### Example Code

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
        PitWindow with recommended timing.

    Raises:
        InsufficientDataError: If not enough data.
    """
    # Implementation
```

### Import Order

```python
# Standard library
import asyncio
from datetime import datetime

# Third-party
import httpx
from fastapi import FastAPI

# Local
from rsw.config import Config
```

---

## Testing Requirements

### All PRs Must Include Tests

- Unit tests for new functions
- Integration tests for API changes
- Update existing tests if behavior changes

### Running Tests

```bash
# All tests
python run.py --test

# Specific file
PYTHONPATH=src pytest tests/test_strategy.py -v

# With coverage
python run.py --coverage
```

### Test Structure

```python
class TestPitWindow:
    """Tests for pit window calculations."""

    def test_valid_input(self):
        """Test with valid input parameters."""
        result = calculate_pit_window(10, 50, 0.05)
        assert result.min_lap <= result.ideal_lap <= result.max_lap

    def test_edge_case(self):
        """Test edge case behavior."""
        result = calculate_pit_window(49, 50, 0.05)
        assert result.ideal_lap == 0  # Too late to pit
```

---

## Documentation

### When to Update Docs

- New features → Update USER_GUIDE.md
- API changes → Update API.md
- New config options → Update DEPLOYMENT.md
- Breaking changes → Update CHANGELOG.md

### Documentation Style

- Use clear, concise language
- Include code examples
- Add tables for reference data
- Keep formatting consistent

---

## Need Help?

- 📖 [Development Guide](docs/DEVELOPMENT.md)
- 💬 [GitHub Discussions](https://github.com/cagancaliskan/apex/discussions)
- 🐛 [Issue Tracker](https://github.com/cagancaliskan/apex/issues)

---

## Recognition

Contributors are listed in [CONTRIBUTORS.md](CONTRIBUTORS.md) and thanked in release notes.

Thank you for contributing! 🏎️
