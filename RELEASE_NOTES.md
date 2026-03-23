# Release Notes

---

## v2.1.0 (2026-03-17)

### Overview

Major feature release delivering real-time race tracking, championship predictions, neural pace modelling, a fully redesigned UI, and AI strategy explainability.

---

### New Features

#### Live Race Mode
- Real-time OpenF1 API polling (5-second interval) for positions, lap times, and car data
- WebSocket streaming of live state updates to all connected clients
- `LiveRaceService` with mutual exclusion against replay sessions
- REST endpoints: `POST /api/live/start`, `/stop`, `GET /status`, `/active-sessions`

#### Championship Simulator
- Monte Carlo simulation across all remaining season rounds (N=200 simulations)
- WDC (Drivers') and WCC (Constructors') championship probability tables
- `ChampionshipContext` per driver — championship phase adjusts risk appetite
- DNF modelling (7% probability), fastest lap bonus point, sprint race scoring
- New **Championship** tab in the frontend with probability bar charts and season timeline

#### Neural Pace Prediction
- NumPy-only MLP model (`neural_model.py`) — 11 inputs → 32 → 16 ReLU → 7 outputs
- Outputs: 5 predicted lap-time deltas + `cliff_probability` + model `confidence`
- Blended ensemble: RLS linear model + neural nonlinear model weighted by data volume
- `cliff_probability > 0.8` triggers immediate pit recommendation uplift
- Test suite: `tests/test_neural_pace.py`

#### Strategy Explainability
- `GET /api/strategy/explain/{driver_number}` — factor ranking + sensitivity analysis
- **ExplainabilityPanel** component with auto-refresh (15-second interval)
- Sensitivity bars show how cliff risk, pit loss, degradation rate, and tyre age affect the recommendation confidence
- What-if scenario generation for parameter perturbations

#### UI/UX Redesign
- CSS custom property token system (colors, spacing, elevation, typography)
- Layered depth system with four card elevation levels
- Inter (body) + JetBrains Mono (telemetry data) font pairing
- 30+ components migrated to token system
- `PitRejoinVisualizer` — shows predicted track position after pit stop
- Improved `StrategyPanel` — recommendation confidence bar, sparkline pace chart

---

### Bug Fixes

| Component | Fix |
|-----------|-----|
| `GridSimulator` | Replace dynamic attribute injection on Pydantic model with `sim_times` dict |
| `pit_window.py` | Convert cliff age from tyre laps to race lap before window calculation |
| `sensitivity.py` | Widen perturbation deltas; add tyre age as sensitivity parameter |
| `useAlerts.ts` | Remove PIT_NOW banners from global alert strip; shown in StrategyPanel |
| `StrategyPanel.tsx` | Show PitRejoinVisualizer whenever pit window data exists |

---

### Upgrading from v2.0.x

```bash
git pull origin main
pip install -r requirements.txt   # no new dependencies
python run.py
```

No database migrations required. No breaking API changes.

---

# Release Notes - v2.0.1

## Overview
This patch release addresses critical stability issues in the strategy engine and data serialization layers, along with significant UI polish fixes. It ensures reliable real-time updates and a stable frontend experience.

---

## 🚀 Key Improvements

### 🔧 Engine Stability
- **Fixed Strategy Initialization**: Resolved a backend crash that prevented the strategy engine from starting, which caused the UI to be stuck on "Evaluating strategy...".
- **Data Serialization**: Fixed a bug where `numpy` data types (from analysis libraries) caused WebSocket crashes, stopping live updates.

### 🎨 UI Polish
- **Telemetry Layout**: 
    - The **Gear Indicator** no longer jumps around when values change; it now has a solid, static width.
    - **Speed Gauge** text is now perfectly positioned to avoid overlapping the visual arc.
- **Strategy Panel**: Removed visual artifacts (like a random "0") and improved error handling for missing data.

### 🛠️ Developer Experience
- **Repository Health**: Added MIT License, standardized documentation, and cleaned up dead code.
- **Type Safety**: Fixed TypeScript errors in visualization components.

---

## 🐛 Bug Fixes Summary

| Component | Issue | Fix |
|-----------|-------|-----|
| **Backend** | `NameError: name 'Any' is not defined` | Added missing import in `monte_carlo.py` |
| **Backend** | WebSocket silent failure | Added `numpy` type conversion in `simulation_service.py` |
| **Frontend** | UI stuck on "Evaluating..." | Restored strategy engine data flow |
| **Frontend** | Gear indicator shifting layout | Enforced static CSS width |
| **Frontend** | Speed text overlap | Adjusted CSS positioning |
| **Frontend** | TypeScript errors | Added null checks for driver position |

---

## 📋 Updating

```bash
git pull origin main
pip install -r requirements.txt
python run.py
```
