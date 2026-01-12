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

## [2.0.1] - 2026-01-12

### Fixed
- **Strategy Engine**: Fixed critical initialization failure caused by missing `Any` import in `monte_carlo.py`, which caused strategy recommendations to fail silently.
- **UI Updates**: Solved issue where UI got stuck on "Evaluating strategy..." due to the backend failure.
- **Serialization**: Fixed `numpy` type serialization error in `simulation_service.py` that caused WebSocket updates to fail.
- **Telemetry Panel**: 
    - Fixed "Gear" indicator layout shift by enforcing static width.
    - Adjusted speed gauge text position to prevent overlap with the graph.
- **Strategy Panel**: Fixed phantom "0" rendering when confidence was zero.
- **Pit Rejoin Visualizer**: Fixed TypeScript error regarding nullable driver positions.
- **Documentation**: Added LICENSE, updated repository URLs in README and CONTRIBUTING.

## [2.0.0] - 2026-01-10

### Added
- **Major Architecture Overhaul**: Complete refactor to service-oriented architecture.
- **New UI Components**: Added TelemetryPanel, StrategyPanel, and PitRejoinVisualizer.

---

## [1.0.6] - 2026-01-01

### Changed
- **Simulation**: Slowed down live simulation speed from 0.5s/1.0s to **3.0s per lap** to allow users to comfortably read real-time data and strategy updates.

## [1.0.7] - 2026-01-02

### Fixed
- **Type Safety**: Resolved all static analysis errors (`mypy`). Codebase now passes strict type checking.
- **Dependency Models**: Updated `sessionmaker` to `async_sessionmaker` in database layer for correct async typing.
- **Middleware**: Added strict return type casting for middleware components.
- **Replay Service**: Added runtime assertions to prevent access to uninitialized sessions.

## [1.0.5] - 2026-01-01

### Fixed
- **Frontend**: Fixed missing speed control buttons in Replay UI and improved their visibility on mobile devices.

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
| 2.0.1 | 2026-01-12 | V2 patch: Strategy fixes & UI polish |
| 2.0.0 | 2026-01-10 | Major V2 release: New Architecture |
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
