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

Global CSS vars are retained. Only values change. Two new variables are added.

| Variable | Old | New | Notes |
|---|---|---|---|
| `--bg-primary` | `#0d1117` | `#08090b` | Deeper black |
| `--bg-secondary` | `#161b22` | `#0f1117` | Tighter surface separation |
| `--bg-tertiary` | `#1c2128` | `#161b22` | Third surface layer |
| `--color-accent` **(new)** | — | `#e10600` | F1 red; used for PIT_NOW badges, CLIFF label, primary interactive accent |
| `--color-info` | `#58a6ff` | `#3b82f6` | Blue demoted to informational only |
| `--text-primary` | `#ffffff` | `#f0f0f0` | Slightly off-white |
| `--text-secondary` | `#8b949e` | `#6b7280` | Cooler gray |
| `--text-muted` | current value | **unchanged** | Retained as-is |
| `--text-tertiary` | current value | **unchanged** | Retained as-is |
| `--border-color` **(new)** | — | `#1f2937` | Replaces all existing border color literals (`rgba(255,255,255,0.06)` etc.) throughout the migration |
| `--status-red` | `#f85149` | **unchanged** | Retained for error/danger states only |
| `--status-green` | `#3fb950` | **unchanged** | |
| `--status-amber` | `#d29922` | **unchanged** | |
| Tyre colors | — | **unchanged** | |

**Note on two reds:** `--color-accent` (`#e10600`) is for *actionable critical signals* (PIT_NOW badge, CLIFF label). `--status-red` (`#f85149`) is for *error/danger indicators* (red flag, connection error). They coexist intentionally.

Font families (Orbitron, Inter, JetBrains Mono) remain unchanged.

---

## 2. Layout & Shell

**Size reductions (density improvement):**
- Status bar: `32px → 28px`
- Tab bar: `28px → 24px`
- Leaderboard column: `320px → 300px`
- Strategy panel column: `360px → 340px`
- Driver row height: `28px → 26px`

**Alert banner:** Alert state is currently local `useState` inside `LiveDashboard.tsx`. Move it into `raceStore.ts` as a new store slice. Add the following to `raceStore.ts`:

```ts
// Types to add (currently defined locally in LiveDashboard.tsx):
type AlertType = 'FLAG' | 'SC' | 'PIT_NOW' | 'THREAT';
interface Alert { id: string; type: AlertType; message: string; ts: number; }

// Store additions:
alerts: Alert[];          // in RaceStore interface
addAlert: (type: AlertType, message: string) => void;
dismissAlert: (id: string) => void;

// initialState addition:
alerts: [],

// Actions: move addAlert / dismissAlert logic from LiveDashboard.tsx into the store
```

`App.tsx` reads `alerts` from the store and renders a dedicated fixed-height alert strip (`32px`) immediately below the tab bar, before the main page content. Alert generation `useEffect` hooks (watch for `redFlag`, `safetycar`, `vsc`, `flags`, driver cliff/undercut changes) move from `LiveDashboard.tsx` into a new `useAlerts()` hook that is called from `LiveDashboard.tsx`.

**Panel separators:** Replace gap-based separation with `1px` solid `var(--border-color)` lines between all major panels.

**Section headers in StrategyPanel:** Unified to `10px` uppercase Inter `500` weight, `var(--text-secondary)` color. The existing `strategy-section-label` class (currently using `var(--text-muted)` via inline style) must be updated to `var(--text-secondary)` in the new `StrategyPanel.module.css`.

---

## 3. Information Hierarchy Fixes

| Element | Change |
|---|---|
| `PIT_NOW` badge | Use `var(--color-accent)` + uppercase Orbitron. Applies in `StrategyPanel.tsx` (recommendation badge) and the `lb-row-pit-now` leaderboard row class. Replaces current use of `var(--status-red)` for this badge only. |
| Tyre cliff risk — threshold | The canonical cliff threshold is **0.8** (`cliff_risk > 0.8`) across the entire app. Update `StrategyPanel.tsx`: the `getCliffColor` function (lines 60–65) currently uses `> 0.7` for its red trigger — update to `> 0.8`. |
| Tyre cliff risk — CLIFF label | When `cliff_risk > 0.8`: render a `CLIFF` text label in Orbitron font, `var(--color-accent)` color, inline next to the cliff risk percentage on the tyre life bar. |
| Undercut/overcut in Leaderboard | Add `⬇` (undercut) / `⬆` (overcut) icon badges in the Leaderboard driver row Status column cell. These are already shown in `StrategyPanel.tsx` — the gap is the Leaderboard rows only. |

---

## 4. New Data Surfaces

### Leaderboard (`LiveDashboard.tsx` inline leaderboard)

**`gap_to_ahead` toggle (verify only):**
The Leaderboard already has an INT/GAP toggle. Verify the GAP mode renders `driver.gap_to_ahead` (type: `number | null`), displaying `"—"` when null. No new column needed.

### StrategyPanel

**`pit_window_min` / `pit_window_max`:**
Show the full window range as a visual bar (e.g. "Window: L28–L34, ideal L31"). Currently only `pit_window_ideal` is shown. Both fields exist in `DriverState`.

**`predicted_rejoin_position` / `rejoin_traffic_severity` — replace inline block with `PitRejoinVisualizer`:**
Replace the inline "Predicted Rejoin" block in `StrategyPanel.tsx` (lines 327–343) with the existing `PitRejoinVisualizer` component.

- Do **not** thread `allDrivers` as a prop through `StrategyPanel`. Read `sortedDrivers` from the Zustand store directly inside `StrategyPanel` using `useRaceStore()`.
- Access `currentLap` via `useRaceStore(s => s.currentLap)` (flat selector — not `s.raceState.current_lap`).
- Render condition: `(currentLap >= selectedDriver.pit_window_min && currentLap <= selectedDriver.pit_window_max && selectedDriver.pit_window_min > 0) || selectedDriver.in_pit === true`. The `pit_window_min > 0` guard prevents spurious rendering when the field is the `0` sentinel (no pit window assigned yet).

**`recent_pits` — pit history strip:**
Add a micro pit history strip at the bottom of `StrategyPanel` showing the last 2–3 pit stops.

- `recent_pits` is on `RaceState` but **not currently in `raceStore.ts`**. Add to `raceStore.ts`:
  - `recentPits: Array<{ lap: number; driver: number }>` to the `RaceStore` interface
  - `recentPits: []` to `initialState` (required for `reset()` to work correctly)
  - map it in `updateState` action: `recentPits: state.recent_pits ?? []`
- Display: compact rows, driver number and lap only (e.g. `#44  L32`). No compound or duration — those fields don't exist in the type.

### TelemetryPanel (standalone — `src/components/TelemetryPanel.tsx`)

**`sector_1` / `sector_2` / `sector_3`:**
Add a 3-sector mini bar to the standalone `TelemetryPanel.tsx`. The `TelemetryHUD` in `LiveDashboard.tsx` already shows sectors for the Live page. This targets `TelemetryPanel.tsx` to bring parity to Replay and Backtest pages.

---

## 5. CSS Architecture

**Approach:** CSS Modules per component. Each module file is co-located with its source file:
- `src/App.tsx` → `src/App.module.css`
- `src/pages/Foo.tsx` → `src/pages/Foo.module.css`
- `src/components/Bar.tsx` → `src/components/Bar.module.css`

Global `index.css` shrinks to shared concerns only. `--border-color` replaces all existing border color literals throughout the migration.

**Scope rule for components:** Only migrate components that are actively imported in `App.tsx`, `LiveDashboard.tsx`, `ReplayPage.tsx`, or `BacktestPage.tsx`. Orphaned components (those with no active import path) should be skipped unless touched for another reason in this upgrade.

### Global `index.css` retains:
- `:root {}` — CSS variable declarations (updated palette + new vars)
- `*, body, html` — resets
- `.app-container`, `.dashboard-grid` — top-level layout grid
- Font imports / `@font-face`

### New `.module.css` files:

**App shell (`src/`):**
- `App.tsx` → `App.module.css` — shell grid, status bar, tab bar, alert strip, session drawer

**Pages (`src/pages/`):**
- `LiveDashboard.tsx` → `LiveDashboard.module.css`
- `ReplayPage.tsx` → `ReplayPage.module.css`
- `BacktestPage.tsx` → `BacktestPage.module.css`

**Active components (`src/components/`) — migrate only if actively imported:**
- `DriverTable.tsx` → `DriverTable.module.css`
- `StrategyPanel.tsx` → `StrategyPanel.module.css`
- `TrackMap.tsx` → `TrackMap.module.css`
- `TelemetryPanel.tsx` → `TelemetryPanel.module.css`
- `TelemetryChart.tsx` → `TelemetryChart.module.css`
- `ExplainabilityPanel.tsx` → `ExplainabilityPanel.module.css`
- `WeatherWidget.tsx` → `WeatherWidget.module.css`
- `RaceMessages.tsx` → `RaceMessages.module.css`
- `MetricCard.tsx` → `MetricCard.module.css`
- `SessionSelector.tsx` → `SessionSelector.module.css`
- `RaceProgressBar.tsx` → `RaceProgressBar.module.css`
- `PitRejoinVisualizer.tsx` → `PitRejoinVisualizer.module.css`
- `TyreLifeChart.tsx` → `TyreLifeChart.module.css`
- `CompetitorPredictions.tsx` → `CompetitorPredictions.module.css`
- `PositionProbabilityChart.tsx` → `PositionProbabilityChart.module.css`
- `StrategyComparison.tsx` → `StrategyComparison.module.css`
- `DRSZoneOverlay.tsx` → `DRSZoneOverlay.module.css`
- `BrakingZoneIndicator.tsx` → `BrakingZoneIndicator.module.css`
- `TopBar.tsx` → `TopBar.module.css` *(migrate only if actively used)*
- `Sidebar.tsx` → `Sidebar.module.css` *(migrate only if actively used)*

---

## 6. Pre-existing Bug (Flag, Don't Fix)

`App.tsx` line 244 renders simulation speed options as `[1, 2, 5, 10, 20]`. The `SimulationSpeed` type in `types/index.ts` is `1 | 5 | 10 | 20 | 50` — `2` is invalid and `50` is missing. This is a pre-existing mismatch. Do not fix it as part of this upgrade (it is not in scope), but do not inadvertently make it worse when migrating `App.tsx` to CSS Modules.

---

## 7. Out of Scope

- Backend changes (all new data is already being sent)
- Extending `recent_pits` type with compound/duration (backend change required)
- New pages or routes
- Responsive/mobile layout
- Animation system
- Design token architecture
