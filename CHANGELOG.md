# Changelog

All notable changes to the F1 Race Strategy Workbench will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Industry-level documentation suite
- Python SDK documentation
- Deployment guides for Docker and Kubernetes

---

## [1.0.4] - 2026-01-01

### Changed
- **Replay**: Further lowered minimum playback speed to **0.05x** and set default to **0.25x** to allow for extremely detailed analysis of race events.

## [1.0.3] - 2026-01-01

### Changed
- **Replay**: Added slower playback speed options (0.1x, 0.25x) and set default speed to 0.5x to improve data readability during replays.

## [1.0.2] - 2026-01-01

### Fixed
- **Frontend**: Fixed `StrategyPanel` to correctly handle selected driver objects, ensuring the strategy view updates when a driver is selected.

## [1.0.1] - 2026-01-01

### Fixed
- **Frontend**: Fixed driver selection interactivity in the live dashboard driver table. Clicking a row now correctly selects the driver and updates the strategy panel.

## [1.0.0] - 2026-01-01

### Added
- **Core Features**
  - Real-time F1 race tracking via OpenF1 API
  - Tyre degradation modeling with RLS estimators
  - Pit window optimization engine
  - Monte Carlo race simulation
  - Undercut/overcut threat detection

- **Architecture**
  - SOLID principles implementation
  - Dependency injection container
  - Factory patterns for extensibility
  - Immutable state management with reducers

- **API**
  - REST API for sessions, state, and strategy
  - WebSocket for real-time updates
  - OpenAPI documentation (Swagger UI)
  - JWT and API key authentication

- **Testing**
  - 68 unit and integration tests
  - 100% test pass rate
  - Prediction accuracy benchmarks

- **Infrastructure**
  - Unified `run.py` entry point
  - Makefile for common commands
  - Docker and Docker Compose support
  - Health check endpoints (liveness/readiness)

### Changed
- Replaced `datetime.utcnow()` with timezone-aware `datetime.now(timezone.utc)`
- Configured pytest to suppress deprecation warnings

### Fixed
- Import errors in degradation model exports
- Test thresholds for real-world data variability
- Asyncio event loop cleanup in API tests

---

## [0.2.0] - 2025-12-15

### Added
- Monte Carlo simulation for race outcomes
- Strategy comparison endpoint
- Replay functionality for historical races

### Changed
- Improved degradation model accuracy
- Enhanced pit window calculations

### Fixed
- WebSocket reconnection issues
- Cache invalidation timing

---

## [0.1.0] - 2025-11-01

### Added
- Initial project structure
- OpenF1 API integration
- Basic state management
- Simple degradation tracking

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 1.0.0 | 2026-01-01 | Production release, full documentation |
| 0.2.0 | 2025-12-15 | Monte Carlo, replay features |
| 0.1.0 | 2025-11-01 | Initial release |

---

## Upgrade Guide

### 0.x to 1.0

1. Update dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Add new environment variables:
   ```env
   RSW_AUTH_ENABLED=true
   JWT_SECRET=your-secret-key
   ```

3. Run database migrations (if applicable):
   ```bash
   python run.py --migrate
   ```

4. Restart services:
   ```bash
   docker-compose down && docker-compose up -d
   ```
