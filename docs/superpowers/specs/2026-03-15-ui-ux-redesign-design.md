# UI/UX Redesign — Industry-Ready F1 Race Strategy Workbench

**Date:** 2026-03-15
**Approach:** Refined Dark SaaS (Approach A)
**Target Users:** Professional F1 team race engineers
**Aesthetic Reference:** AWS/Azure/Vercel cloud dashboards — subtle gradients, layered depth, data-dense

---

## 1. Design System & Tokens (`index.css`)

### Token Migration Map (old → new)

All existing token references in every `.module.css` file AND inline `style=` props in every `.tsx` file must be updated using this explicit mapping:

| Old Token | New Token | New Value | Notes |
|-----------|-----------|-----------|-------|
| `--bg-primary` | `--bg-base` | `#050608` | |
| `--bg-secondary` | `--bg-surface` | `#0d1117` | |
| `--bg-tertiary` | `--bg-elevated` | `#161b24` | |
| `--bg-card` | `--bg-surface` | `#0d1117` | |
| `--bg-card-hover` | `--bg-elevated` | `#161b24` | |
| `--border-color` | `--border-subtle` | `rgba(255,255,255,0.06)` | |
| `--text-primary` | `--text-primary` | `#f0f6fc` | Value changes from `#f0f0f0` |
| `--text-secondary` | `--text-secondary` | `#8b949e` | Value changes from `#6b7280` |
| `--text-tertiary` | `--text-muted` | `#484f58` | Collapse into `--text-muted`. Remove `--text-tertiary` definition from `index.css` and migrate all call sites to `var(--text-muted)`. |
| `--color-info` | `--color-accent` | `#e10600` | **Only for non-alert highlights** (tabs, selected rows, active borders). Retain `--color-info: #3b82f6` for informational alerts. |
| `--accent-cyan` | `--status-blue` | `#3b82f6` | See new token definition below |
| `--accent-magenta` | `--color-accent` | `#e10600` | |
| `--accent-yellow` | `--status-amber` | `#d29922` | |
| `--accent-purple` | `--color-purple` | `#a371f7` | `--color-purple` already exists in `index.css` — do NOT map to `--bg-elevated` |
| `--font-display` | `--text-ui` | `var(--text-ui)` | Retain as alias: `--font-display: var(--text-ui)` in `index.css` to avoid changing all call sites |

> **Scope of migration:** Token replacements apply to ALL `.module.css` files AND all inline `style=` props inside `.tsx` files across the entire `frontend/src` directory. This includes but is not limited to: `ReplayPage.tsx`, `BacktestPage.tsx`, `TyreLifeChart.tsx`, `DRSZoneOverlay.tsx`, `TelemetryPanel.tsx`, `TelemetryChart.tsx`, `ExplainabilityPanel.tsx`, `CompetitorPredictions.tsx`, `PositionProbabilityChart.tsx`, `BrakingZoneIndicator.tsx`, `StrategyComparison.tsx`, `MetricCard.tsx`, `SessionSelector.tsx`. Item 11 in Section 6 (all remaining files) explicitly covers these.

> **`--font-display` strategy:** Rather than replacing all call sites, add `--font-display: var(--text-ui)` as a retained alias in `index.css`. This preserves all existing references without changes to individual files.

### New Token Definitions (add to `index.css`)

```css
--bg-base: #050608;
--bg-surface: #0d1117;
--bg-elevated: #161b24;
--bg-inset: #0a0c10;
--border-subtle: rgba(255, 255, 255, 0.06);
--border-muted: rgba(255, 255, 255, 0.10);
--border-active: rgba(225, 6, 0, 0.4);
--color-accent-gradient: linear-gradient(135deg, #e10600 0%, #ff4500 100%);
--text-muted: #484f58;
--text-mono: 'JetBrains Mono', 'Roboto Mono', monospace;
--text-ui: 'Inter', system-ui, sans-serif;
--status-blue: #3b82f6;
--font-display: var(--text-ui);   /* retained alias — do not remove */
```

Keep existing: `--color-info`, `--status-green`, `--status-amber`, `--status-red`, `--color-accent`, `--color-purple`, tyre tokens, `--text-primary`, `--text-secondary` (values updated per table above).

### Typography

- **UI font:** Inter — labels, names, headers, tabs
- **Numeric font:** JetBrains Mono — all lap times, gaps, speeds, positions, percentages
- `font-variant-numeric: tabular-nums` applied globally to any element displaying changing numbers
- Section labels: 10px, uppercase, `letter-spacing: 0.1em`, `var(--text-secondary)`
- Add to `frontend/index.html` `<head>`: `<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">`
- `lucide-react` is already a project dependency — no new package needed

### Elevation / Depth

- **Card surface:** `background: var(--bg-surface); box-shadow: 0 1px 3px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04);`
- **Active/selected row:** `border-left: 2px solid var(--color-accent); box-shadow: inset 4px 0 12px rgba(225,6,0,0.08);`
- **Chart containers:** `background: linear-gradient(180deg, var(--bg-elevated) 0%, var(--bg-surface) 100%);`
- **App radial background:** applied to `.app-container` in `index.css` (the global class, not a module class): add `background: radial-gradient(ellipse 80% 50% at 50% 0%, rgba(225,6,0,0.025) 0%, transparent 70%);`

---

## 2. Global Shell (`App.tsx` + `App.module.css`)

### Status Bar (28px)
- Background: `linear-gradient(90deg, var(--bg-inset) 0%, var(--bg-surface) 100%)`
- Bottom border: `1px solid var(--border-subtle)`
- Left: session name — Inter 11px uppercase, letter-spaced, `var(--text-secondary)`
- Center: track name + round — separated by `|` divider in `var(--text-muted)`
- Right: lap counter in JetBrains Mono
- Connection dot: small circle; when connected — `animation: pulse-dot 2s ease-in-out infinite` (green); static amber when connecting; static red when disconnected

### Tab Bar
- Active tab: white text + `border-bottom: 2px solid var(--color-accent)` (replace current `--color-info` blue underline in `.tabBtnActive` in `App.module.css`)
- Inactive tabs: `var(--text-secondary)` ghost text, no underline
- Lucide icons left of tab label: `Radio` (Live), `RotateCcw` (Replay), `BarChart2` (Backtest) — 14px
- Separator: `1px solid var(--border-subtle)` below tab bar

### SessionSelector (`SessionSelector.tsx` + `SessionSelector.module.css`)
- Active/hover selection border: change `--color-info` → `--color-accent` (selected session uses red accent, consistent with single accent language)

### Alert Strip
- `backdrop-filter: blur(8px)` + `background: rgba(13,17,23,0.85)`
- Left border `3px solid` per type: red=PIT_NOW/flags, amber=SC, blue=info
- Per-alert entry animation: `.alertRow` in `App.module.css` gets `animation: slideInAlert 200ms cubic-bezier(0.16,1,0.3,1) forwards`
- **React key strategy:** Alert items in `App.tsx` must be keyed by `alert.id` (not array index) so that new alerts trigger a fresh mount and replay the CSS entry animation. Verify the current render loop uses `key={alert.id}`.
- Exit: `opacity: 0` transition `150ms ease` on dismiss
- PIT_NOW icon: `animation: pulse-ring 1.5s ease-out infinite`

---

## 3. Dashboard Layout

### `index.css` — `.dashboard-grid` (global class)
> The 3-column grid is defined in the global `.dashboard-grid` class in `index.css`. All grid layout changes go here, not in `LiveDashboard.module.css`.

- Update `gap` to `4px` in `.dashboard-grid`
- Each column wrapper class: add `border-right: 1px solid var(--border-subtle)` (except last column — use `:last-child { border-right: none }`)
- Column section header elements: 10px uppercase Inter, `letter-spacing: 0.1em`, `var(--text-secondary)`, `padding: 6px 8px`

---

## 4. Component Designs

### Live Leaderboard Rows (`LiveDashboard.tsx` — inline `Leaderboard` component)
> The live race leaderboard is implemented as an inline component inside `LiveDashboard.tsx`. Changes to leaderboard row appearance go there, not in `DriverTable.tsx`.

- **Position number:** JetBrains Mono bold; P1=`#FFD700`, P2=`#C0C0C0`, P3=`#CD7F32`, rest=`var(--text-muted)`
- **Driver acronym:** Inter medium weight, `var(--text-primary)`
- **Gap:** JetBrains Mono; green (`--status-green`) gaining, red (`--status-red`) losing; `▲` prefix gaining, `▼` prefix losing
- **Tyre badge:** pill `border-radius: 4px`, compound color background, lap age in `var(--text-secondary)` subscript
- **PIT_NOW row:** `background: rgba(225,6,0,0.08)` + left glow border
- **Hover:** `background: rgba(255,255,255,0.03)` transition `100ms`
- **Selected row:** `border-left: 2px solid var(--color-accent)` + ambient glow (replace current `--color-info` blue highlight)

### DriverTable (`DriverTable.tsx` + `DriverTable.module.css`)
- Token migration only per Section 1 table

### MetricCard (`MetricCard.tsx` + `MetricCard.module.css`)
- Token migration per Section 1 table: `--bg-card` → `--bg-surface`, `--border-color` → `--border-subtle`, `--color-info` → `--color-accent` (for non-alert highlights), `--accent-cyan` → `--status-blue`, `--accent-purple` → `--color-purple`

### TrackMap (`TrackMap.tsx` + `TrackMap.module.css`)
- Track outline SVG stroke: inner edge `#1e2530`, outer edge `#2a3441`
- Selected driver dot: `filter: drop-shadow(0 0 4px currentColor)` glow
- DRS zones: `rgba(0,200,180,0.15)` teal fill overlay

### TelemetryChart (`TelemetryChart.tsx` + `TelemetryChart.module.css`)
- Chart container gets card elevation treatment
- Speed line area fill: Recharts `<Area>` with `fill` using SVG `linearGradient`: `rgba(59,130,246,0.15)` at top → `rgba(59,130,246,0)` at bottom
- Verify `isAnimationActive={true}` on `<Line>` and `<Area>` components

### StrategyPanel (`StrategyPanel.tsx` + `StrategyPanel.module.css`)
- `.strategySection` border: `var(--border-color)` → `var(--border-subtle)` (explicit replacement)
- Pit window bar: gradient fill — `rgba(225,6,0,0.2)` at edges → `rgba(225,6,0,0.5)` at ideal window center
- Degradation line: SVG `<linearGradient>` stops: `--status-green` at low deg → `--status-amber` at medium → `--status-red` at high/cliff
- Section cards: `1px solid var(--border-subtle)` hairline dividers — no full box borders

### WeatherWidget (`WeatherWidget.tsx` + `WeatherWidget.module.css`)
- Remove `WeatherIcon` and `WindArrow` custom SVG sub-components
- Replace with Lucide icons: `Thermometer`, `Droplets`, `Wind`
- Mini grid layout: icon + value pairs
- Numbers in `var(--text-mono)`
- Card gets elevation treatment

### RaceProgressBar (`RaceProgressBar.tsx` + `RaceProgressBar.module.css`)
- Replace `--accent-cyan` → `--status-blue`, `--accent-magenta` → `--color-accent`, `--accent-yellow` → `--status-amber`, `--accent-purple` → `--color-purple`, `--font-display` resolved via retained alias (no change needed at call site)
- Progress fill gradient: `linear-gradient(90deg, var(--status-blue), var(--color-accent))`

---

## 5. Animations & Micro-interactions

### Keyframe + Class Definitions (add to `index.css`)

```css
@keyframes pulse-ring {
  0%   { box-shadow: 0 0 0 0 rgba(225, 6, 0, 0.5); }
  70%  { box-shadow: 0 0 0 8px rgba(225, 6, 0, 0); }
  100% { box-shadow: 0 0 0 0 rgba(225, 6, 0, 0); }
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.6; transform: scale(0.85); }
}

@keyframes flash-amber {
  0%, 100% { background-color: transparent; }
  50%       { background-color: rgba(210, 153, 34, 0.15); }
}

@keyframes flash-red {
  0%, 100% { background-color: transparent; }
  50%       { background-color: rgba(248, 81, 73, 0.2); }
}

@keyframes slideInAlert {
  from { transform: translateY(-100%); opacity: 0; }
  to   { transform: translateY(0);     opacity: 1; }
}

@keyframes flashValue {
  from { background-color: rgba(255, 255, 255, 0.12); }
  to   { background-color: transparent; }
}

/* Utility classes for JS-triggered animations */
.flash-value {
  animation: flashValue 200ms ease-out forwards;
}

.flash-amber-bg {
  animation: flash-amber 0.8s ease-in-out 2;
}

.flash-red-bg {
  animation: flash-red 0.3s steps(1) 3;
}
```

### Race Event Animations
- **Safety Car:** Add `.flash-amber-bg` class to status bar element via `App.tsx`; after animation ends, hold `background-color: rgba(210,153,34,0.08)` via a persistent CSS class
- **Red Flag:** Add `.flash-red-bg` class; hold `background-color: rgba(248,81,73,0.12)` after animation
- **PIT_NOW icon element:** `animation: pulse-ring 1.5s ease-out infinite` inline in module CSS

### Real-time Data Updates
- **Number flash on change:** `App.tsx` or relevant component adds `.flash-value` class to the element, then removes it after `200ms` via `setTimeout` (the `animation: flashValue 200ms ease-out forwards` class definition is in `index.css` above — no additional CSS needed per component)
- **Position arrow:** `150ms` CSS `transition: transform 150ms ease, color 150ms ease` on the arrow element; React toggles a `.gaining` / `.losing` class

### Alert Entry Animation
- `.alertRow` in `App.module.css`: `animation: slideInAlert 200ms cubic-bezier(0.16,1,0.3,1) forwards`
- Alerts in `App.tsx` must use `key={alert.id}` (not index) so each new alert triggers a fresh DOM mount and replays the CSS animation

### Navigation
- Tab switch: `transition: opacity 150ms ease` on page content wrapper
- Driver selection: row highlight instant; panel crossfade `transition: opacity 200ms ease`

### Charts
- Recharts `isAnimationActive={true}` on `<Line>` and `<Area>`
- Degradation chart: SVG `<linearGradient>` with dynamic stops via React props

### Explicitly Excluded
- No parallax, no page loaders, no skeleton screens, no heavy page transitions

---

## 6. Implementation Scope

### Files to modify (no new files created):

**Mechanical token migration (every `.module.css` + all inline `style=` props in `.tsx`):**
1. `frontend/index.html` — add Google Fonts `<link>` for Inter + JetBrains Mono
2. `frontend/src/index.css` — add all new tokens, retained aliases, update changed token values, add `.dashboard-grid` gap, add all keyframe blocks + utility classes, add `.app-container` radial gradient

**Shell:**
3. `frontend/src/App.tsx` + `App.module.css` — status bar, tab bar (`color-info` → `color-accent`), alert strip animation, `key={alert.id}` on alert list

**Pages:**
4. `frontend/src/pages/LiveDashboard.tsx` + `LiveDashboard.module.css` — inline leaderboard row styles, column headers, selected row highlight (`color-info` → `color-accent`)
5. `frontend/src/pages/ReplayPage.tsx` + `ReplayPage.module.css` — token migration (inline styles + module)
6. `frontend/src/pages/BacktestPage.tsx` + `BacktestPage.module.css` — token migration

**Components (structural changes):**
7. `frontend/src/components/TrackMap.tsx` + `TrackMap.module.css` — SVG stroke colors, car dot glow, DRS zone color
8. `frontend/src/components/TelemetryChart.tsx` + `TelemetryChart.module.css` — chart gradient, card elevation, token migration
9. `frontend/src/components/StrategyPanel.tsx` + `StrategyPanel.module.css` — pit window gradient, deg SVG gradient, `border-color` → `border-subtle`
10. `frontend/src/components/WeatherWidget.tsx` + `WeatherWidget.module.css` — replace custom SVGs with Lucide, grid layout, mono numbers
11. `frontend/src/components/RaceProgressBar.tsx` + `RaceProgressBar.module.css` — legacy alias token replacement

**Components (token migration only):**
12. `frontend/src/components/DriverTable.tsx` + `DriverTable.module.css`
13. `frontend/src/components/MetricCard.tsx` + `MetricCard.module.css`
14. `frontend/src/components/SessionSelector.tsx` + `SessionSelector.module.css` — `color-info` → `color-accent` for active border
15. `frontend/src/components/TelemetryPanel.tsx` + `TelemetryPanel.module.css`
16. `frontend/src/components/TyreLifeChart.tsx` + `TyreLifeChart.module.css`
17. `frontend/src/components/DRSZoneOverlay.tsx` + `DRSZoneOverlay.module.css`
18. `frontend/src/components/ExplainabilityPanel.tsx` + `ExplainabilityPanel.module.css`
19. `frontend/src/components/CompetitorPredictions.tsx` + `CompetitorPredictions.module.css`
20. `frontend/src/components/PositionProbabilityChart.tsx` + `PositionProbabilityChart.module.css`
21. `frontend/src/components/BrakingZoneIndicator.tsx` + `BrakingZoneIndicator.module.css`
22. `frontend/src/components/StrategyComparison.tsx` + `StrategyComparison.module.css`
23. `frontend/src/components/PitRejoinVisualizer.tsx` + `PitRejoinVisualizer.module.css` — token migration (includes inline `style=` with `var(--bg-tertiary)`)
24. `frontend/src/components/RaceMessages.module.css` — token migration
25. Any remaining `.module.css` and `.tsx` files with legacy token references (including `TopBar.tsx` if it contains legacy inline styles)

### Implementation ordering (hard dependency):
**Item 2 (`index.css`) must be completed first** — all new token definitions, retained aliases, and keyframe blocks must exist in `index.css` before any component file is touched. Components referencing new tokens will render broken until the tokens are defined. Item 1 (`index.html` font link) must also precede any component changes to avoid font flash.

### No backend changes required.
### No new npm packages required. Note: `JetBrains Mono` is referenced in the existing `--font-mono` fallback stack but is **not currently loaded** via `index.html`. Item 1 adds the Google Fonts `<link>` — this is a required step, not optional.
