# F1 Race Strategy Workbench — Apex

<p align="center">
  <strong>Real-time F1 Race Analytics, Pit Strategy Optimization & Championship Prediction</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/fastapi-0.104+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/react-18.2-61dafb.svg" alt="React">
  <img src="https://img.shields.io/badge/typescript-5.3-3178c6.svg" alt="TypeScript">
  <img src="https://img.shields.io/badge/tests-211%20passed-success.svg" alt="Tests">
  <img src="https://img.shields.io/badge/version-2.1.0-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
</p>

---

## Overview

The **F1 Race Strategy Workbench** is a professional-grade platform for real-time Formula 1 race analysis, pit strategy optimization, and championship prediction. It combines live telemetry data with physics-based models, machine learning, and Monte Carlo simulations to deliver actionable strategy recommendations.

### Key Features

| Feature | Description |
|---------|-------------|
| **Live Race Mode** | Real-time session tracking via OpenF1 API with WebSocket streaming |
| **Championship Simulator** | Multi-race Monte Carlo prediction for WDC & WCC standings |
| **Pit Strategy Optimization** | Optimal pit windows with undercut/overcut detection |
| **Tyre Degradation Modeling** | Online RLS estimators with cliff-risk prediction |
| **Historical Replay** | Lap-by-lap replay of any race from 2023+ with FastF1 data |
| **Explainability Engine** | Human-readable strategy explanations with sensitivity analysis |
| **Physics Simulation** | Fuel model, weather effects, track evolution, dirty air modeling |
| **Grid Simulator** | Full 20-car race simulation with CompetitorAI decision-making |

---

## Documentation

| Document | Description |
|----------|-------------|
| [**Quick Start**](docs/QUICKSTART.md) | Installation and first run |
| [**Architecture**](docs/ARCHITECTURE.md) | System design, components, data flow |
| [**Architecture Diagrams**](docs/ARCHITECTURE_DIAGRAMS.md) | Visual system diagrams (Mermaid) |
| [**API Reference**](docs/API.md) | Complete REST & WebSocket API |
| [**User Guide**](docs/USER_GUIDE.md) | End-user feature documentation |
| [**Development**](docs/DEVELOPMENT.md) | Developer setup and guidelines |
| [**Deployment**](docs/DEPLOYMENT.md) | Docker, Kubernetes, cloud deployment |
| [**Python SDK**](docs/SDK.md) | Programmatic access to the API |
| [**Troubleshooting**](docs/TROUBLESHOOTING.md) | Common issues and fixes |

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/cagancaliskan/apex.git
cd apex

# 2. Install backend dependencies
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Install frontend dependencies
cd frontend && npm install && cd ..

# 4. Start backend
PYTHONPATH=src uvicorn rsw.main:app --reload --port 8000

# 5. Start frontend (new terminal)
cd frontend && npm run dev
```

**Backend:** http://localhost:8000 | **Frontend:** http://localhost:5173 | **API Docs:** http://localhost:8000/docs

For Docker setup: `docker-compose up --build`

---

## Technology Stack

| Layer | Technologies |
|-------|--------------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn, WebSockets, Pydantic v2 |
| **Frontend** | React 18, TypeScript 5.3, Vite 5, Recharts, Zustand, Lucide |
| **ML/Physics** | NumPy, Pandas, RLS Estimator, Tyre/Fuel/Weather Models |
| **Data Sources** | OpenF1 API (real-time), FastF1 (historical), OpenMeteo (weather) |
| **Infrastructure** | Docker, Docker Compose, GitHub Actions CI/CD |
| **Monitoring** | Prometheus, Grafana, Structured Logging (structlog) |
| **Database** | PostgreSQL 15, Redis 7 (optional caching) |
| **Quality** | Ruff, MyPy, Bandit, Pytest, Vitest, Trivy |

---

## Project Structure

```
apex/
├── src/rsw/                        # Backend source (84 modules, 16k+ LOC)
│   ├── api/routes/                 # REST API endpoints
│   │   ├── health.py               #   Health/readiness probes
│   │   ├── sessions.py             #   Session browsing & filtering
│   │   ├── simulation.py           #   Race simulation control
│   │   ├── live.py                 #   Live race tracking
│   │   ├── championship.py         #   Championship Monte Carlo
│   │   ├── explain_route.py        #   Strategy explainability
│   │   └── weather.py              #   Weather data & forecasts
│   ├── services/                   # Business logic layer
│   │   ├── simulation_service.py   #   Race replay engine
│   │   ├── live_race_service.py    #   Real-time OpenF1 polling
│   │   ├── championship_service.py #   Multi-race Monte Carlo
│   │   ├── strategy_service.py     #   Pit strategy calculations
│   │   └── session_service.py      #   Session data management
│   ├── strategy/                   # Strategy engine
│   │   ├── monte_carlo.py          #   Outcome simulation
│   │   ├── grid_simulator.py       #   Full 20-car grid simulation
│   │   ├── competitor_ai.py        #   AI competitor modeling
│   │   ├── situational_strategy.py #   Championship-aware strategy
│   │   ├── pit_window.py           #   Pit window optimization
│   │   └── explain.py              #   Strategy explanations
│   ├── models/                     # ML & physics models
│   │   ├── physics/                #   Tyre, fuel, weather, track models
│   │   └── degradation/            #   RLS degradation estimator
│   ├── ingest/                     # Data ingestion
│   │   ├── openf1_client.py        #   OpenF1 real-time API
│   │   ├── fastf1_service.py       #   FastF1 historical data
│   │   └── weather_client.py       #   OpenMeteo weather API
│   ├── state/                      # State management (reducer pattern)
│   ├── middleware/                  # Auth, rate limiting, error handling
│   └── main.py                     # FastAPI application entry point
│
├── frontend/                       # React TypeScript frontend (40 files, 7.6k LOC)
│   └── src/
│       ├── pages/                  # LiveDashboard, Replay, Backtest, Championship
│       ├── components/             # 30+ UI components
│       ├── hooks/                  # useWebSocket, useSimulation, useAlerts
│       ├── store/                  # Zustand race state
│       └── types/                  # TypeScript type definitions
│
├── tests/                          # Test suite (211 tests across 18 files)
├── configs/                        # YAML configuration (app, strategy, tracks)
├── docs/                           # Documentation suite (8 guides)
├── .github/workflows/              # CI/CD pipelines
├── docker-compose.yml              # Multi-service Docker orchestration
├── Dockerfile                      # Backend container
├── Makefile                        # Build automation
└── pyproject.toml                  # Python project configuration
```

---

## Architecture Overview

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   OpenF1    │  │   FastF1    │  │  OpenMeteo   │
│  (real-time)│  │ (historical)│  │  (weather)   │
└──────┬──────┘  └──────┬──────┘  └──────┬───────┘
       │                │                │
       ▼                ▼                ▼
┌─────────────────────────────────────────────────┐
│              Ingest Layer                        │
│  OpenF1Client · FastF1Service · WeatherClient    │
└───────────────────────┬─────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│              State Store (Reducers)              │
│       Immutable RaceState · DriverState          │
└──────┬──────────────────────────────┬───────────┘
       │                              │
       ▼                              ▼
┌──────────────────┐   ┌──────────────────────────┐
│  Strategy Engine │   │     Services Layer        │
│  MonteCarlo      │   │  SimulationService        │
│  GridSimulator   │   │  LiveRaceService          │
│  CompetitorAI    │   │  ChampionshipService      │
│  PitWindow       │   │  StrategyService          │
│  Explainability  │   └────────────┬──────────────┘
└──────┬───────────┘                │
       │                            │
       ▼                            ▼
┌──────────────────┐   ┌──────────────────────────┐
│    REST API      │   │       WebSocket           │
│  /api/sessions   │   │  Real-time state_update   │
│  /api/live       │   │  ping/pong keepalive      │
│  /api/championship│  │  start/stop session       │
│  /api/simulation │   │  start/stop live          │
│  /api/weather    │   └────────────┬──────────────┘
└──────┬───────────┘                │
       │                            │
       ▼                            ▼
┌─────────────────────────────────────────────────┐
│              React Frontend                      │
│  LiveDashboard · ReplayPage · ChampionshipPage   │
│  30+ components · Zustand · Recharts             │
└─────────────────────────────────────────────────┘
```

For detailed architecture diagrams, see [Architecture Diagrams](docs/ARCHITECTURE_DIAGRAMS.md).

---

## Testing

```bash
# Backend tests (211 tests)
PYTHONPATH=src python -m pytest tests/ -v

# With coverage
PYTHONPATH=src python -m pytest tests/ --cov=rsw --cov-report=html

# Frontend build verification
cd frontend && npm run build

# Full CI check
make test
```

**Current Status:** 211 backend tests passing, 0 failures, frontend builds cleanly.

---

## Docker

```bash
# Full stack (backend + frontend + PostgreSQL + Redis + Prometheus + Grafana)
docker-compose up --build

# Backend only
docker build -t rsw-backend .
docker run -p 8000:8000 rsw-backend

# Using Make
make docker
```

---

## Configuration

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RSW_ENVIRONMENT` | `development` | Environment mode |
| `RSW_CORS_ORIGINS` | `localhost:5173,localhost:3000` | Allowed CORS origins |
| `RSW_RATE_LIMIT_ENABLED` | `false` | Enable rate limiting |
| `RSW_WS_AUTH_REQUIRED` | `false` | Require WebSocket auth |
| `OPENF1_BASE_URL` | `https://api.openf1.org/v1` | OpenF1 API URL |

See [Deployment Guide](docs/DEPLOYMENT.md) for full configuration.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/sessions` | List available sessions |
| `POST` | `/api/simulation/load/{year}/{round}` | Load race simulation |
| `POST` | `/api/live/start` | Start live race tracking |
| `GET` | `/api/live/active-sessions` | List active F1 sessions |
| `POST` | `/api/championship/simulate` | Run championship Monte Carlo |
| `GET` | `/api/championship/calendar/{year}` | Season calendar |
| `GET` | `/api/strategy/explain/{driver}` | Strategy explanation |
| `GET` | `/api/weather/current/{circuit}` | Current weather |
| `WS` | `/ws` | Real-time state updates |

Full API reference: [docs/API.md](docs/API.md) | Interactive docs: http://localhost:8000/docs

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Security

For security concerns, please see our [Security Policy](SECURITY.md).

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [OpenF1](https://openf1.org) for providing free F1 timing data
- [FastF1](https://github.com/theOehrly/Fast-F1) for historical telemetry access
- [OpenMeteo](https://open-meteo.com) for weather API
- The F1 community for feedback and feature requests

---

<p align="center">
  Made with precision for F1 strategists and data enthusiasts
</p>
