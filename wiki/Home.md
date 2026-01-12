# F1 Race Strategy Workbench

<p align="center">
  <img src="images/logo.png" alt="Race Strategy Workbench" width="200">
</p>

<p align="center">
  <strong>Real-time F1 Race Analytics & Pit Strategy Optimization</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/fastapi-0.104+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/tests-68%20passed-success.svg" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
</p>

---

## 🏎️ Overview

The **F1 Race Strategy Workbench** is a professional-grade application for real-time Formula 1 race analysis and pit strategy optimization. It combines live telemetry data with machine learning models to provide actionable strategy recommendations.

### Key Features

- **Real-time Race Tracking** — Live positions, gaps, and lap times via WebSocket
- **Tyre Degradation Modeling** — ML-powered degradation prediction with cliff detection
- **Pit Strategy Optimization** — Optimal pit windows with Monte Carlo simulations
- **Historical Replay** — Replay any race from 2023+ with lap-by-lap simulation
- **Undercut/Overcut Detection** — Real-time threat assessment

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [**Quick Start**](Quick-Start) | All commands to run the application |
| [**Architecture**](Architecture) | System design and components |
| [**API Reference**](API-Reference) | Complete REST & WebSocket API |
| [**Development**](Development-Guide) | Developer setup and guidelines |
| [**Deployment**](Deployment) | Docker, Kubernetes, cloud deployment |
| [**User Guide**](User-Guide) | End-user features documentation |
| [**Python SDK**](Python-SDK) | Programmatic access to the API |
| [**Troubleshooting**](Troubleshooting) | Common issues and fixes |

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/cagancaliskan/apex.git
cd apex

# 2. Install dependencies
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Run the application
python run.py
```

**Open:** http://localhost:8000

For detailed setup instructions, see [Quick Start Guide](Quick-Start).

---

## 🏗️ Technology Stack

| Layer | Technologies |
|-------|--------------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn, WebSockets |
| **Frontend** | React 18, TypeScript, Vite, Recharts |
| **ML/Data** | NumPy, Pandas, RLS Estimator |
| **Data Source** | OpenF1 API (real-time & historical) |
| **Infrastructure** | Docker, Redis (optional), PostgreSQL (optional) |

---

## 📁 Project Structure

```
F1/
├── src/rsw/                    # Backend source code
│   ├── api/                    # REST API routes
│   ├── ingest/                 # Data providers (OpenF1)
│   ├── models/                 # ML models (degradation, RLS)
│   ├── strategy/               # Strategy engine
│   ├── state/                  # State management
│   └── main.py                 # FastAPI application
├── frontend/                   # React frontend
├── tests/                      # Test suite (68 tests)
├── docs/                       # Documentation
├── run.py                      # Unified entry point
├── Makefile                    # Make commands
└── requirements.txt            # Python dependencies
```

---

## 🧪 Testing

```bash
# Run all tests
python run.py --test

# With coverage
python run.py --coverage

# Using Make
make test
```

**Current Status:** 68 tests passing, 0 warnings

---

## 🐳 Docker

```bash
# Build and run
docker-compose up --build

# Or using Make
make docker
```

---

## 🔧 Configuration

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RSW_ENV` | `development` | Environment (development/staging/production) |
| `RSW_PORT` | `8000` | Server port |
| `RSW_LOG_LEVEL` | `INFO` | Logging level |
| `OPENF1_BASE_URL` | `https://api.openf1.org/v1` | OpenF1 API URL |

See [Deployment Guide](Deployment) for full configuration options.

---

## 📊 Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   OpenF1    │────▶│   Ingest    │────▶│    State    │
│     API     │     │   Layer     │     │    Store    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐            │
                    │   Strategy  │◀───────────┤
                    │   Engine    │            │
                    └──────┬──────┘            │
                           │                   │
                    ┌──────▼──────┐     ┌──────▼──────┐
                    │  REST API   │     │  WebSocket  │
                    └──────┬──────┘     └──────┬──────┘
                           │                   │
                    ┌──────▼───────────────────▼──────┐
                    │           Frontend              │
                    └─────────────────────────────────┘
```

For detailed architecture, see [Architecture Documentation](Architecture).

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](Contributing) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 🔒 Security

For security concerns, please see our [Security Policy](Security).

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [OpenF1](https://openf1.org) for providing free F1 timing data
- [FastF1](https://github.com/theOehrly/Fast-F1) for historical data access
- The F1 community for feedback and feature requests

---

<p align="center">
  Made with ❤️ for F1 fans and data enthusiasts
</p>

---
**Next:** [[Quick-Start]]
