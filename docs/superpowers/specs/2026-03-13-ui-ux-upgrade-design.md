# UI/UX Industry-Grade Upgrade — Design Spec

**Date:** 2026-03-13
**Project:** F1 Race Strategy Workbench
**Branch:** v2.1-major-upgrade-complete
**Status:** Approved for implementation

---

## Context

The F1 Race Strategy Workbench is a React 18 + TypeScript + Vite application for real-time F1 race analysis. Primary users are F1 team engineers and analysts working pitside or in a race ops center. The UI must be dense, scannable, and unambiguous under pressure.

**Identified pain points:**
- Inconsistent styling — components feel ad-hoc, not part of a unified system
- Suboptimal data density — whitespace not earning its place, driver rows too tall
- Weak information hierarchy — critical alerts (PIT_NOW, undercut threats) don't stand out enough from ambient data
- Monolithic CSS — all ~750 lines in one `index.css`, no encapsulation

**Visual reference:** Actual F1 team tooling (high-contrast, structured grid) + modern SaaS analytics (polished dark mode, deliberate typography).

---

## 1. Palette (Updated CSS Variables in `index.css`)

Global CSS vars are retained. Only values change:

| Variable | Old | New |
|---|---|---|
| `--bg-primary` | `#0d1117` | `#08090b` |
| `--bg-secondary` | `#161b22` | `#0f1117` |
| `--bg-tertiary` | `#1c2128` | `#161b22` |
| `--color-accent` (new) | — | `#e10600` (F1 red) |
| `--color-info` | `#58a6ff` | `#3b82f6` (blue, informational only) |
| `--text-primary` | `#ffffff` | `#f0f0f0` |
| `--text-secondary` | `#8b949e` | `#6b7280` |
| `--border-color` (new) | — | `#1f2937` |

Status colors (`--status-green`, `--status-amber`, `--status-red`) and tyre colors remain unchanged — they are already correct.

Font families (Orbitron, Inter, JetBrains Mono) remain unchanged.

---

## 2. Layout & Shell

**Size reductions (density improvement):**
- Status bar: `32px → 28px`
- Tab bar: `28px → 24px`
- Leaderboard column: `320px → 300px`
- Strategy panel column: `360px → 340px`
- Driver row height: `28px → 26px`

**Alert banner:** Moved from a floating overlay above content into an inline strip inside the status bar. Eliminates layout shift; alert is always visible without displacing dashboard content.

**Panel separators:** Replace gap-based separation with `1px` solid `--border-color` lines between major panels. Clearer structure, less wasted space.

**Section headers in StrategyPanel:** Unified to `10px` uppercase Inter `500` weight, `--text-secondary` color. Clear hierarchy without competing with data.

---

## 3. Information Hierarchy Fixes

| Element | Change |
|---|---|
| `PIT_NOW` badge | Uses `--color-accent` (`#e10600`) + uppercase Orbitron — unmistakably critical |
| Tyre cliff risk bar | Adds `CLIFF` label in Orbitron red when degradation >80% — scannable without reading number |
| `undercut_threat` / `overcut_opportunity` | Small icon indicators in driver row (data was sent, never shown) |

---

## 4. New Data Surfaces (Backend Data Previously Unused)

The backend already sends the following fields which are not rendered in the frontend. This upgrade surfaces them:

### DriverTable
- **`gap_to_ahead`** — New column alongside `gap_to_leader`. Engineers need both simultaneously.
- **`undercut_threat` / `overcut_opportunity`** — Icon badges per driver row. Sent by backend, never displayed.

### StrategyPanel
- **`pit_window_min` / `pit_window_max`** — Display full window range as a bar (e.g. "Window: L28–L34, ideal L31"). Currently only `pit_window_ideal` is shown.
- **`predicted_rejoin_position` / `rejoin_traffic_severity`** — Rejoin preview card shown when driver is in pit window or actively pitting. Component `PitRejoinVisualizer` exists but is disconnected — wire it up.
- **`recent_pits`** — Micro pit history strip (2–3 rows) at bottom of strategy panel: lap, compound, duration.

### TelemetryPanel
- **`sector_1` / `sector_2` / `sector_3`** — 3-sector mini bar added to telemetry HUD for selected driver. Data is sent, never displayed.

---

## 5. CSS Architecture

**Approach:** CSS Modules per component. Global `index.css` shrinks to shared concerns only.

### Global `index.css` retains:
- `:root {}` — CSS variable declarations (updated palette)
- `*, body, html` — resets
- `.app-container`, `.dashboard-grid` — top-level layout grid
- Font imports / `@font-face`

### New `.module.css` files:

| Component | Module |
|---|---|
| `App.tsx` | `App.module.css` — shell grid, status bar, tab bar, session drawer |
| `DriverTable.tsx` | `DriverTable.module.css` — leaderboard, rows, badges, gap/threat columns |
| `StrategyPanel.tsx` | `StrategyPanel.module.css` — pit window bar, rejoin card, pit history strip |
| `TrackMap.tsx` | `TrackMap.module.css` — SVG container, car markers |
| `TelemetryPanel.tsx` | `TelemetryPanel.module.css` — HUD layout, sector bars |
| `ExplainabilityPanel.tsx` | `ExplainabilityPanel.module.css` |
| `WeatherWidget.tsx` | `WeatherWidget.module.css` |
| `RaceMessages.tsx` | `RaceMessages.module.css` |
| `MetricCard.tsx` | `MetricCard.module.css` — reusable card base |
| `LiveDashboard.tsx` | `LiveDashboard.module.css` |
| `ReplayPage.tsx` | `ReplayPage.module.css` |
| `BacktestPage.tsx` | `BacktestPage.module.css` |

---

## 6. Out of Scope

- Backend changes (all new data is already being sent)
- New pages or routes
- Responsive/mobile layout
- Animation system
- Design token architecture
