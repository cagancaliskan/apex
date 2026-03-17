# Changelog

All notable changes to the F1 Race Strategy Workbench will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [2.1.0] - 2026-03-17

### Added

- **Live Race Mode** (Feature #1)
  - Real-time F1 session tracking via OpenF1 API polling (5s intervals)
  - `LiveRaceService` with automatic session detection and state broadcasting
  - REST endpoints: `POST /api/live/start`, `POST /api/live/stop`, `GET /api/live/status`, `GET /api/live/active-sessions`
  - WebSocket messages: `start_live`, `stop_live`, `live_started`, `live_stopped`
  - Mutual exclusion with simulation mode (auto-stops simulation when live starts)
  - 19 new tests for live race functionality

- **Championship Simulator** (Feature #2)
  - Multi-race Monte Carlo championship prediction (WDC & WCC)
  - `ChampionshipService` with full-season simulation using GridSimulator + CompetitorAI
  - `ChampionshipContext` integration — first real use of `calculate_risk_modifier()` from `situational_strategy.py`
  - REST endpoints: `POST /api/championship/simulate`, `GET /api/championship/calendar/{year}`, `GET /api/championship/standings/{year}/{up_to_round}`
  - Frontend `ChampionshipPage` with standings table, probability charts, season timeline
  - DNF modeling (7% probability), fastest lap bonus, sprint race support
  - Pydantic models: `RaceCalendarEntry`, `DriverStanding`, `ConstructorStanding`, `ChampionshipResult`
  - 39 new tests for championship simulation

- **UI/UX Redesign**
  - Complete CSS design token system migration (layered depth, elevation tokens)
  - Inter + JetBrains Mono typography integration
  - 30+ component refactors to new token system (DriverTable, MetricCard, TelemetryPanel, StrategyPanel, SessionSelector, TrackMap, WeatherWidget, RaceProgressBar, etc.)
  - Red accent theme with gradient fills and animation keyframes (pulse-ring, flash events, slideInAlert)
  - Lucide React icon integration across all tab and navigation elements
  - Card elevation system, hairline dividers, mono numeric styling

- **Strategy Explainability**
  - `GET /api/strategy/explain/{driver_number}` endpoint with factor ranking and sensitivity analysis
  - `ExplainabilityPanel` frontend component for human-readable strategy explanations

- **Weather Integration**
  - `WeatherClient` for OpenMeteo API integration
  - `GET /api/weather/current/{circuit_key}` and `GET /api/weather/forecast/{circuit_key}` endpoints
  - Weather effects integrated into physics simulation

- **Physics Models**
  - `FuelModel` — fuel load impact on lap time (burn rate, weight penalties)
  - `WeatherModel` — rain/temperature effects on grip and pace
  - `TrackModel` — track-specific characteristics and rubber evolution
  - `PitTrafficModel` — pit lane traffic and interaction effects
  - `SeasonLearner` — cross-session driver pace/degradation priors

- **Infrastructure**
  - Constants module (`src/rsw/config/constants.py`) for physics defaults
  - Enhanced WebSocket protocol with live mode messages
  - Comprehensive documentation suite update
  - Architecture diagrams (Mermaid)
  - CI/CD pipeline enhancements

### Changed
- Version bumped from 1.0.7 to 2.1.0
- Frontend version bumped to 1.1.0
- `App.tsx` now has 4 tabs: Live, Replay, Backtest, Championship
- TypeScript types expanded with championship and live mode interfaces
- Test count increased from 68 to 211 (143 new tests)

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
| 2.1.0 | 2026-03-17 | Live Race Mode, Championship Simulator, UI/UX redesign |
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
