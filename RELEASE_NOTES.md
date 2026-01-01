# Release v1.0.0 - F1 Race Strategy Workbench

**Release Date:** January 1, 2026

This is the first production release of the F1 Race Strategy Workbench - a professional-grade application for real-time Formula 1 race analysis and pit strategy optimization.

---

## 🏎️ Features

### Core Functionality
- **Real-time Race Tracking** — Live positions, gaps, and lap times via OpenF1 API
- **Tyre Degradation Modeling** — ML-powered RLS estimators with cliff detection
- **Pit Strategy Optimization** — Optimal pit windows with confidence scoring
- **Monte Carlo Simulation** — Race outcome predictions for strategy scenarios
- **Undercut/Overcut Detection** — Real-time threat assessment
- **Historical Replay** — Lap-by-lap replay of any race from 2023+

### Technical Highlights
- **68 Passing Tests** — 100% test success rate
- **SOLID Architecture** — Clean code with dependency injection
- **WebSocket Support** — Real-time updates to clients
- **REST API** — Complete OpenAPI-documented API
- **Docker Ready** — Full containerization support

---

## 📚 Documentation

Complete industry-level documentation included:

- **README.md** — Project overview and quick start
- **docs/QUICKSTART.md** — All run commands
- **docs/ARCHITECTURE.md** — System design with diagrams
- **docs/API.md** — Complete API reference
- **docs/DEVELOPMENT.md** — Developer guide
- **docs/DEPLOYMENT.md** — Docker, Kubernetes, cloud guides
- **docs/SDK.md** — Python SDK documentation
- **docs/USER_GUIDE.md** — End-user guide
- **docs/TROUBLESHOOTING.md** — Common issues & fixes
- **CONTRIBUTING.md** — Contribution guidelines
- **SECURITY.md** — Security policy

**Total:** 12 documentation files + 3 architecture diagrams

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/cagancaliskan/apex.git
cd apex

# Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the application
python run.py
```

Open http://localhost:8000 to access the application.

---

## 📋 What's Included

### Backend (`src/rsw/`)
- FastAPI application with WebSocket support
- OpenF1 API integration
- RLS degradation models
- Pit strategy engine
- Monte Carlo simulator
- State management with reducers
- JWT authentication (optional)

### Frontend (`frontend/`)
- React 18 application
- Real-time WebSocket updates
- Interactive strategy dashboard
- Historical replay controls

### Tests (`tests/`)
- 68 comprehensive tests
- Unit, integration, and accuracy tests
- Fixtures and mocking

### Infrastructure
- Dockerfile and docker-compose.yml
- Kubernetes manifests
- CI/CD workflows
- Makefile for common commands

---

## 🔧 Configuration

Environment variables:

```env
RSW_ENV=production
RSW_PORT=8000
RSW_LOG_LEVEL=INFO
```

See `docs/DEPLOYMENT.md` for complete configuration options.

---

## 📊 Statistics

- **119 Files** committed
- **21,323 Lines** of code and documentation
- **~1.34 MB** total size
- **68 Tests** passing
- **12 Documentation files**
- **3 Architecture diagrams**

---

## 🛡️ Security

- JWT authentication support
- API key authentication
- Input validation via Pydantic
- CORS configuration
- Rate limiting

See `SECURITY.md` for vulnerability reporting.

---

## 🤝 Contributing

We welcome contributions! Please see `CONTRIBUTING.md` for:
- Code of conduct
- Development process
- Pull request guidelines
- Coding standards

---

## 📝 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- [OpenF1](https://openf1.org) for providing free F1 timing data
- The F1 community for feedback and support

---

## 📞 Support

- Documentation: [README.md](README.md)
- Issues: [GitHub Issues](https://github.com/cagancaliskan/apex/issues)
- Troubleshooting: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

**Download:** [v1.0.0 Release](https://github.com/cagancaliskan/apex/releases/tag/v1.0.0)
