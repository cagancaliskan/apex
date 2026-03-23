# Architecture Documentation

Complete technical architecture documentation for the F1 Race Strategy Workbench v2.1.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Components](#core-components)
3. [Data Flow](#data-flow)
4. [Design Principles](#design-principles)
5. [Directory Structure](#directory-structure)
6. [Key Abstractions](#key-abstractions)
7. [Security Model](#security-model)
8. [Scalability](#scalability)

For visual diagrams, see [Architecture Diagrams](ARCHITECTURE_DIAGRAMS.md).

---

## System Overview

The F1 Race Strategy Workbench is a real-time analytics platform that ingests live F1 timing data, processes it through physics-based models and ML estimators, and provides pit strategy recommendations, championship predictions, and race simulations via REST API and WebSocket.

### Key Characteristics

| Aspect | Description |
|--------|-------------|
| **Architecture Style** | Event-driven, microservices-ready monolith |
| **Communication** | REST API + WebSocket for real-time updates |
| **Data Sources** | OpenF1 (real-time), FastF1 (historical), OpenMeteo (weather) |
| **State Management** | Immutable state with reducer pattern |
| **ML Pipeline** | Online learning with RLS estimators |
| **Physics Engine** | Tyre, fuel, weather, track models |
| **Simulation** | GridSimulator (20-car), Monte Carlo (championship) |

---

## Core Components

### 1. Ingest Layer (`src/rsw/ingest/`)

**Purpose:** Fetch and normalize data from three external sources.

| Module | Responsibility |
|--------|----------------|
| `base.py` | Abstract `DataProvider` interface, canonical DTOs |
| `openf1_client.py` | OpenF1 API client — real-time timing, positions, laps |
| `fastf1_service.py` | FastF1 library — historical telemetry, session results, event schedules |
| `weather_client.py` | OpenMeteo API — current conditions, forecasts by circuit coordinates |

**Key Classes:**
- `OpenF1Client` — HTTP client with caching for real-time data
- `FastF1Service` — Thread-pool executor wrapper for FastF1 (blocking I/O)
- `WeatherClient` — Async weather data for circuits worldwide

---

### 2. State Management (`src/rsw/state/`)

**Purpose:** Maintain immutable race state with reducer pattern.

| Module | Responsibility |
|--------|----------------|
| `schemas.py` | Pydantic models for `RaceState`, `DriverState` (80+ fields per driver) |
| `store.py` | `RaceStateStore` with observer pattern |
| `reducers.py` | Pure functions for state updates |

**DriverState Fields (key groups):**
```
DriverState:
  ├── Identity: driver_number, name_acronym, full_name, team_name, team_colour
  ├── Timing: current_lap, last_lap_time, best_lap_time, gap_to_leader, sectors
  ├── Telemetry: speed, gear, throttle, brake, drs
  ├── Position: rel_dist, x, y (track coordinates)
  ├── Tyres: compound, tyre_age, stint_number, deg_slope, cliff_risk
  ├── Strategy: pit_window_min/max/ideal, pit_recommendation, pit_confidence
  ├── Physics: fuel_remaining_kg, fuel_laps_remaining, predicted_pace[]
  └── Status: in_pit, retired, undercut_threat, overcut_opportunity
```

---

### 3. Physics & ML Models (`src/rsw/models/`)

**Purpose:** Physics simulation and real-time performance prediction.

#### Degradation Models (`models/degradation/`)

| Module | Responsibility |
|--------|----------------|
| `rls.py` | Recursive Least Squares estimator — online linear learning per driver |
| `neural_model.py` | **NEW v2.1** NumPy-only MLP for nonlinear pace prediction and cliff detection |
| `online_model.py` | Real-time degradation tracking — blends RLS linear + Neural nonlinear predictions |
| `calibration.py` | Model calibration against telemetry data |
| `__init__.py` | `ModelManager` — selects between models based on data availability and confidence |

**Neural Pace Prediction (v2.1):**
- **Architecture:** 11-feature input → 32 → 16 ReLU hidden units → 7 outputs
- **Inputs:** tyre age, track temp, compound one-hot (5), track type, fuel load
- **Outputs:** 5 predicted pace deltas (next 5 laps) + `cliff_probability` + `confidence`
- **Integration:** `DriverDegradationModel` blends RLS and neural predictions via ensemble weight α (higher α = more neural, lower α = more RLS), weighted by data volume
- **Cliff Detection:** `cliff_probability > 0.5` triggers "CLIFF" warning in the Strategy Panel; `> 0.8` triggers immediate pit recommendation uplift

#### Physics Models (`models/physics/`)

| Module | Responsibility |
|--------|----------------|
| `tyre_model.py` | Compound characteristics, degradation curves, cliff detection |
| `fuel_model.py` | Fuel burn rate, weight penalty (~0.035s/kg), range estimation |
| `weather_model.py` | Rain/temperature effects on grip, wet tyre transitions |
| `track_model.py` | Track-specific characteristics, rubber evolution over stint |
| `traffic_model.py` | DRS zones, dirty air effects on following cars |
| `pit_traffic_model.py` | Pit lane traffic interactions, unsafe release modeling |
| `season_learner.py` | Cross-session learning — driver pace/degradation priors from `data/season_data/` |

---

### 4. Strategy Engine (`src/rsw/strategy/`)

**Purpose:** Calculate optimal pit strategies and simulate race outcomes.

| Module | Responsibility |
|--------|----------------|
| `pit_window.py` | Optimal pit window calculation (min/max/ideal laps) |
| `pitloss.py` | Pit stop time loss estimation including traffic |
| `monte_carlo.py` | Parallelized single-race outcome simulation |
| `grid_simulator.py` | Full 20-car discrete event race simulation |
| `competitor_ai.py` | 10 team-specific AI profiles for pit decisions |
| `situational_strategy.py` | `ChampionshipContext`, `ChampionshipPhase`, `calculate_risk_modifier()` |
| `decision.py` | Strategy recommendation engine (PIT_NOW / STAY_OUT / CONSIDER_PIT) |
| `explain.py` | Human-readable strategy explanations |
| `sensitivity.py` | Parameter sensitivity analysis |
| `strategy_generator.py` | Strategy variant generation |
| `strategy_comparator.py` | Multi-strategy comparison |
| `driver_behavior.py` | Driver characteristic extraction |
| `team_profiles.py` | Team-specific strategy patterns |

**GridSimulator:**
- Simulates all 20 cars lap-by-lap with physics models
- CompetitorAI makes pit decisions per team strategy profile
- Accounts for safety cars, tyre degradation, fuel burn, track evolution
- Used by both single-race Monte Carlo and Championship Simulator

---

### 5. Services Layer (`src/rsw/services/`)

**Purpose:** Orchestrate business logic and coordinate state updates.

| Service | Responsibility |
|---------|----------------|
| `SimulationService` | Race replay — loads FastF1 data, steps through laps, broadcasts state via WebSocket |
| `LiveRaceService` | **NEW v2.1** — Real-time OpenF1 polling (5s interval), state updates, mutual exclusion with simulation |
| `ChampionshipService` | **NEW v2.1** — Multi-race Monte Carlo (N simulations x remaining races), WDC/WCC prediction |
| `StrategyService` | Async strategy evaluation, caching, parallel execution |
| `SessionService` | Session data management, FastF1 loading |
| `ReplayService` | Historical session playback control |

**LiveRaceService Flow:**
```
start(session_key) → polling loop (5s):
  1. Fetch positions, laps, car data from OpenF1
  2. Apply reducers to update RaceState
  3. Run StrategyService for pit recommendations
  4. Broadcast state_update via WebSocket
```

**ChampionshipService Flow:**
```
simulate(year, start_from_round, n_simulations) → asyncio.to_thread():
  1. Fetch calendar via FastF1
  2. Fetch completed standings via FastF1 session.results
  3. Build synthetic driver grid from SeasonLearner priors
  4. For each simulation (N=200):
       For each remaining race:
         a. Build ChampionshipContext per driver
         b. calculate_risk_modifier() → adjust SC probability
         c. GridSimulator.run_simulation()
         d. Apply DNF (7% probability)
         e. Award fastest lap (+1 point to random top-10)
         f. Convert positions → points (Race/Sprint scoring)
  5. Aggregate: mean/std/p10/p90/prob_champion per driver
  6. Group by team for WCC standings
```

---

### 6. API Layer (`src/rsw/api/`)

**Purpose:** REST and WebSocket endpoints.

| Module | Responsibility |
|--------|----------------|
| `routes/health.py` | Health, liveness, readiness probes |
| `routes/sessions.py` | Session browsing and filtering |
| `routes/simulation.py` | Race simulation control (load/stop/speed) |
| `routes/live.py` | **NEW v2.1** — Live race tracking (start/stop/status/active-sessions) |
| `routes/championship.py` | **NEW v2.1** — Championship simulation and standings |
| `routes/explain_route.py` | Strategy explainability with sensitivity analysis |
| `routes/weather.py` | Weather data and forecasts |
| `websocket_manager.py` | WebSocket connection management and broadcasting |

**Endpoint Summary:**

| Category | Endpoints |
|----------|-----------|
| Health | `GET /health`, `/health/live`, `/health/ready` |
| Sessions | `GET /api/sessions`, `/api/sessions/{key}` |
| Simulation | `POST /api/simulation/load/{year}/{round}`, `/stop`, `/speed/{speed}`, `GET /status` |
| Live | `POST /api/live/start`, `/stop`, `GET /status`, `/active-sessions` |
| Championship | `POST /api/championship/simulate`, `GET /calendar/{year}`, `/standings/{year}/{round}` |
| Explain | `GET /api/strategy/explain/{driver_number}` |
| Weather | `GET /api/weather/current/{circuit}`, `/forecast/{circuit}` |
| State | `GET /api/state` |
| Replay | `GET /api/replay/sessions`, `POST /replay/{key}/start`, `/control` |
| WebSocket | `WS /ws` — state_update, ping/pong, start/stop session, start/stop live, set_speed |

---

### 7. Frontend (`frontend/`)

**Purpose:** React 18 TypeScript single-page application.

| Directory | Content |
|-----------|---------|
| `src/pages/` | `LiveDashboard`, `ReplayPage`, `BacktestPage`, `ChampionshipPage` |
| `src/components/` | 30+ UI components (see below) |
| `src/hooks/` | `useWebSocket`, `useSimulation`, `useAlerts` |
| `src/store/` | Zustand store (`raceStore.ts`) |
| `src/types/` | TypeScript type definitions mirroring backend schemas |

**Component Categories:**
- **Core:** DriverTable, TrackMap, SessionSelector, TopBar, Sidebar
- **Analytics:** TelemetryPanel, StrategyPanel, ExplainabilityPanel, TelemetryChart
- **Visualization:** TyreLifeChart, PositionProbabilityChart, PitRejoinVisualizer, CompetitorPredictions
- **Indicators:** BrakingZoneIndicator, DRSZoneOverlay, RaceProgressBar, WeatherWidget
- **UI Primitives:** MetricCard, RaceMessages, StrategyComparison

**Design System (v2.1):**
- CSS custom property tokens for colors, spacing, elevation, typography
- Layered depth system with card elevation levels
- Inter (body) + JetBrains Mono (data) font pairing
- Red accent theme with gradient fills
- Animation keyframes: pulse-ring, flash events, slideInAlert

---

## Data Flow

### Mode 1: Live Race

```
OpenF1 API (polling 5s)
       │
       ▼
LiveRaceService
       │
       ├── Fetch positions, laps, car data
       ├── Apply reducers → RaceStateStore
       ├── StrategyService → recommendations
       │
       ▼
WebSocket broadcast (state_update)
       │
       ▼
React Frontend (LiveDashboard)
```

### Mode 2: Historical Replay

```
FastF1 (session.load)
       │
       ▼
SimulationService (lap-by-lap stepping)
       │
       ├── Apply reducers → RaceStateStore
       ├── StrategyService → recommendations
       │
       ▼
WebSocket broadcast (state_update)
       │
       ▼
React Frontend (ReplayPage)
```

### Mode 3: Championship Prediction

```
POST /api/championship/simulate
       │
       ▼
ChampionshipService.simulate()
       │
       ├── FastF1: calendar + completed standings
       ├── SeasonLearner: driver pace priors
       │
       ▼
asyncio.to_thread() → simulation loop:
  N simulations × remaining races
       │
       ├── ChampionshipContext per driver
       ├── GridSimulator.run_simulation()
       ├── DNF + fastest lap + points
       │
       ▼
JSON Response → ChampionshipResult
       │
       ▼
React Frontend (ChampionshipPage)
```

---

## Design Principles

### SOLID Principles

| Principle | Implementation |
|-----------|----------------|
| **SRP** | Each service has single responsibility |
| **OCP** | Factories enable extension without modification |
| **LSP** | All implementations substitutable for interfaces |
| **ISP** | Focused interfaces (DataProvider, Cache) |
| **DIP** | Dependency injection via Container and `init_*_routes()` pattern |

### Additional Patterns

| Pattern | Implementation |
|---------|----------------|
| **Reducer Pattern** | Immutable state updates via pure functions |
| **Observer Pattern** | WebSocket broadcasting on state change |
| **Strategy Pattern** | CompetitorAI with 10 team-specific profiles |
| **Factory Pattern** | DataProviderFactory for data source selection |
| **Service Layer** | Business logic isolated from API routes |

---

## Directory Structure

```
src/rsw/
├── main.py                     # FastAPI app entry, lifespan, WebSocket handler
├── config/                     # Configuration
│   ├── settings.py             #   App config loading (YAML + env vars)
│   └── constants.py            #   Physics constants and defaults
├── api/                        # REST API layer
│   ├── routes/
│   │   ├── health.py           #   Health/readiness probes
│   │   ├── sessions.py         #   Session browsing
│   │   ├── simulation.py       #   Simulation control
│   │   ├── live.py             #   Live race tracking
│   │   ├── championship.py     #   Championship Monte Carlo
│   │   ├── explain_route.py    #   Strategy explainability
│   │   └── weather.py          #   Weather data
│   └── websocket_manager.py    #   Connection management
├── services/                   # Business logic
│   ├── simulation_service.py   #   Race replay engine
│   ├── live_race_service.py    #   Real-time OpenF1 polling
│   ├── championship_service.py #   Championship prediction
│   ├── strategy_service.py     #   Pit strategy calculations
│   ├── session_service.py      #   Session data management
│   └── replay_service.py       #   Playback control
├── strategy/                   # Strategy engine
│   ├── monte_carlo.py          #   Race outcome simulation
│   ├── grid_simulator.py       #   20-car race simulation
│   ├── competitor_ai.py        #   AI competitor modeling
│   ├── situational_strategy.py #   Championship-aware strategy
│   ├── pit_window.py           #   Pit window optimization
│   ├── decision.py             #   Recommendations
│   ├── explain.py              #   Explanations
│   └── sensitivity.py          #   Sensitivity analysis
├── models/                     # ML & physics models
│   ├── degradation/            #   RLS estimator, neural MLP, calibration
│   │   ├── rls.py              #     RLS online linear estimator
│   │   ├── neural_model.py     #     NumPy MLP for nonlinear pace prediction
│   │   ├── online_model.py     #     RLS + neural ensemble blending
│   │   └── calibration.py      #     Model calibration
│   ├── physics/                #   Tyre, fuel, weather, track, traffic models
│   └── features/               #   Feature engineering
├── ingest/                     # Data ingestion
│   ├── openf1_client.py        #   OpenF1 real-time API
│   ├── fastf1_service.py       #   FastF1 historical data
│   └── weather_client.py       #   OpenMeteo weather API
├── state/                      # State management
│   ├── schemas.py              #   Pydantic state models
│   ├── store.py                #   Race state store
│   └── reducers.py             #   Pure state update functions
├── middleware/                  # HTTP middleware
│   ├── auth.py                 #   JWT authentication
│   ├── rate_limit.py           #   Rate limiting
│   └── error_handler.py        #   Centralized error handling
├── repositories/               # Data access layer
├── db/                         # Database models (SQLAlchemy)
└── backtest/                   # Replay and metrics
```

---

## Security Model

### Authentication

| Method | Use Case |
|--------|----------|
| JWT Bearer | User authentication |
| API Key | Service-to-service |
| WebSocket Token | Optional WS auth (`RSW_WS_AUTH_REQUIRED`) |
| None | Development mode (default) |

### Security Features

- CORS origin validation (wildcards rejected in production)
- Input validation via Pydantic v2
- Rate limiting middleware (configurable)
- Correlation ID middleware for request tracing
- SQL injection prevention (parameterized queries)
- XSS protection (React escaping)
- Trivy vulnerability scanning in CI
- Bandit static security analysis

---

## Scalability

### Horizontal Scaling

```
                    Load Balancer
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
    │  App 1  │    │  App 2  │    │  App 3  │
    └────┬────┘    └────┬────┘    └────┬────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                    ┌────▼────┐
                    │  Redis  │ (shared state)
                    └─────────┘
```

### Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| REST API (p95) | < 100ms | Standard endpoints |
| WebSocket update | < 50ms | State broadcast |
| Championship simulation | 20-60s | Batch computation, `asyncio.to_thread()` |
| Live polling cycle | 5s | OpenF1 API rate-limited |
| GridSimulator (single race) | ~15ms | Used in Monte Carlo loop |

---

## Related Documentation

- [Architecture Diagrams](ARCHITECTURE_DIAGRAMS.md) — Visual Mermaid diagrams
- [API Reference](API.md) — Detailed endpoint documentation
- [Deployment Guide](DEPLOYMENT.md) — Production deployment
- [Development Guide](DEVELOPMENT.md) — Contributing code
