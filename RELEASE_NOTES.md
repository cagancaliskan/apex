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
