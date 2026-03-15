# UI/UX Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the F1 Race Strategy Workbench UI to professional "Refined Dark SaaS" standard targeting actual F1 team engineers.

**Architecture:** CSS-only visual overhaul — no logic changes. Token migration (old names → new names), new elevation/depth system, typography upgrade (Inter + JetBrains Mono), gradient fills for charts/status bars, and CSS keyframe micro-animations for race events. All changes are in CSS Modules + `index.css` + `index.html`, plus WeatherWidget.tsx which swaps custom SVGs for Lucide icons.

**Tech Stack:** React 18, TypeScript, CSS Modules, Recharts, Lucide-react (already installed), Google Fonts (Inter + JetBrains Mono via `<link>`)

---

## Chunk 1: Foundation — Tokens, Keyframes, Grid

**MUST be completed first.** All other chunks depend on the new tokens and keyframes existing in `index.css`.

---

### Task 1: Add Google Fonts to `index.html`

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Read the file**

  Open `frontend/index.html` and locate the `<head>` section.

- [ ] **Step 2: Replace existing font `<link>` tags**

  The file already has three font `<link>` tags loading Inter and Orbitron (but NOT JetBrains Mono). Replace all three existing font `<link>` lines with:

  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  ```

  This removes Orbitron (no longer used) and adds JetBrains Mono.

- [ ] **Step 3: Verify build**

  ```bash
  cd frontend && npm run build 2>&1 | tail -5
  ```
  Expected: exit 0, no errors.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/index.html
  git commit -m "feat(ui): add Inter + JetBrains Mono font loading"
  ```

---

### Task 2: Replace CSS tokens in `index.css` — `:root` block

**Files:**
- Modify: `frontend/src/index.css` (lines 6–85)

- [ ] **Step 1: Read current `:root` block**

  Read `frontend/src/index.css` lines 1–85. Lines 1–5 are the file header comment — do NOT modify those. The `:root` block starts at line 6 and closes at line 85.

- [ ] **Step 2: Replace the entire `:root` block**

  Replace from `:root {` (line 6) to its closing `}` (line 85) with:

  > **Note on `--accent-cyan`:** The old value was `#4fd1c5` (teal). The new alias maps it to `var(--status-blue)` (`#3b82f6`, blue). Any remaining component still referencing `var(--accent-cyan)` after migration will shift from teal to blue. This is intentional — verify visually during the smoke test in Task 20.

  ```css
  :root {
    /* ── Backgrounds — layered depth ── */
    --bg-base:        #050608;
    --bg-surface:     #0d1117;
    --bg-elevated:    #161b24;
    --bg-inset:       #0a0c10;

    /* Legacy aliases — kept so existing call sites compile without change */
    --bg-primary:     var(--bg-base);
    --bg-secondary:   var(--bg-surface);
    --bg-tertiary:    var(--bg-elevated);
    --bg-card:        var(--bg-surface);
    --bg-card-hover:  var(--bg-elevated);

    /* ── Borders ── */
    --border-subtle:  rgba(255, 255, 255, 0.06);
    --border-muted:   rgba(255, 255, 255, 0.10);
    --border-active:  rgba(225, 6, 0, 0.4);

    /* Legacy alias */
    --border-color:   var(--border-subtle);

    /* ── Accent ── */
    --color-accent:          #e10600;
    --color-accent-gradient: linear-gradient(135deg, #e10600 0%, #ff4500 100%);

    /* ── Info / status ── */
    --color-info:    #3b82f6;   /* retained for informational alerts only */
    --status-blue:   #3b82f6;
    --color-purple:  #a371f7;
    --status-green:  #3fb950;
    --status-amber:  #d29922;
    --status-red:    #f85149;
    --color-orange:  #ff6b00;

    /* Legacy aliases */
    --status-yellow:  var(--status-amber);
    --accent-green:   var(--status-green);
    --accent-yellow:  var(--status-amber);
    --accent-cyan:    var(--status-blue);
    --accent-orange:  var(--color-orange);
    --accent-magenta: var(--color-accent);
    --accent-purple:  var(--color-purple);

    /* ── Text ── */
    --text-primary:   #f0f6fc;
    --text-secondary: #8b949e;
    --text-muted:     #484f58;

    /* Legacy alias — collapse --text-tertiary into --text-muted */
    --text-tertiary:  var(--text-muted);

    /* ── Typography ── */
    --text-ui:        'Inter', system-ui, sans-serif;
    --text-mono:      'JetBrains Mono', 'Roboto Mono', monospace;
    --font-sans:      var(--text-ui);
    --font-mono:      var(--text-mono);
    --font-display:   var(--text-ui);   /* retained alias */

    /* ── Tyre compounds (F1 spec, unchanged) ── */
    --tyre-soft:   #ff0000;
    --tyre-medium: #ffd700;
    --tyre-hard:   #e8e8e8;
    --tyre-inter:  #39d353;
    --tyre-wet:    #0080ff;

    /* ── Layout ── */
    --sidebar-width:      48px;
    --topbar-height:      44px;
    --status-bar-height:  28px;
    --tab-bar-height:     24px;
    --panel-header:       32px;
    --row-height:         26px;
    --leaderboard-width:  300px;
    --strategy-width:     340px;

    /* ── Spacing ── */
    --space-xs:  0.25rem;
    --space-sm:  0.5rem;
    --space-md:  1rem;
    --space-lg:  1.5rem;
    --space-xl:  2rem;
    --space-2xl: 3rem;

    /* ── Border radius ── */
    --radius-sm:   3px;
    --radius-md:   6px;
    --radius-lg:   8px;
    --radius-xl:   12px;
    --radius-full: 9999px;

    /* ── Transitions ── */
    --transition-fast: 100ms ease;
    --transition-base: 200ms ease;
  }
  ```

- [ ] **Step 3: Verify build**

  ```bash
  cd frontend && npm run build 2>&1 | tail -5
  ```
  Expected: exit 0.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/index.css
  git commit -m "feat(ui): upgrade CSS token system — layered depth + legacy aliases"
  ```

---

### Task 3: Add animation keyframes + utility classes to `index.css`

**Files:**
- Modify: `frontend/src/index.css` (Animations section, around line 403)

- [ ] **Step 1: Locate the Animations section**

  Find the block starting with `/* === Animations (minimal, professional)` around line 403. The block ends at line 408 (two comment lines only — there are no actual keyframes yet). The Scrollbar section starts immediately after at line 410. Replace lines 403–408 only; do not touch the scrollbar rules below.

  > **CSS Modules note:** `@keyframes` defined globally in `index.css` are accessible by name from CSS Module files (e.g. `App.module.css`). The `slideInAlert` keyframe added here will work when referenced in `App.module.css` Task 5.

- [ ] **Step 2: Replace the Animations section**

  Replace lines 403–408 with:

  ```css
  /* ============================================================================
     Animations
     ============================================================================ */

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

  /* Utility classes — add via JS className for one-shot animations */
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

- [ ] **Step 3: Verify build**

  ```bash
  cd frontend && npm run build 2>&1 | tail -5
  ```
  Expected: exit 0.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/index.css
  git commit -m "feat(ui): add animation keyframes — pulse-ring, flash events, slideInAlert"
  ```

---

### Task 4: Update global layout + card styles in `index.css`

**Files:**
- Modify: `frontend/src/index.css` (`.app-container`, `.card`, `.body`, scrollbar, `.connection-dot`)

- [ ] **Step 1: Update `body` background**

  Find the `body { ... }` rule and add the radial gradient:

  ```css
  body {
    font-family: var(--font-sans);
    background: var(--bg-base);
    color: var(--text-primary);
    line-height: 1.5;
    min-height: 100vh;
    overflow-x: hidden;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    font-variant-numeric: tabular-nums;
  }
  ```

- [ ] **Step 2: Replace the entire `.app-container` rule**

  Find the `.app-container` rule and replace the full rule (not just add one property):

  ```css
  .app-container {
    display: grid;
    grid-template-rows: var(--status-bar-height) var(--tab-bar-height) auto 1fr;
    height: 100vh;
    overflow: hidden;
    background: radial-gradient(ellipse 80% 50% at 50% 0%, rgba(225,6,0,0.025) 0%, transparent 70%);
  }
  ```

- [ ] **Step 3: Update `.card`**

  ```css
  .card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
    box-shadow: 0 1px 3px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04);
    transition: background var(--transition-fast);
  }

  .card:hover {
    background: var(--bg-elevated);
  }
  ```

- [ ] **Step 4: Add animated `.connection-dot.connected`**

  Find `.connection-dot.connected` and update:

  ```css
  .connection-dot.connected {
    background: var(--status-green);
    animation: pulse-dot 2s ease-in-out infinite;
  }
  ```

- [ ] **Step 5: Update scrollbar tokens**

  Find scrollbar rules and update:

  ```css
  ::-webkit-scrollbar-track { background: var(--bg-surface); }
  ::-webkit-scrollbar-thumb { background: var(--bg-elevated); border-radius: 4px; }
  ```

- [ ] **Step 6: Verify build**

  ```bash
  cd frontend && npm run build 2>&1 | tail -5
  ```
  Expected: exit 0.

- [ ] **Step 7: Commit**

  ```bash
  git add frontend/src/index.css
  git commit -m "feat(ui): update body, card, app-container, connection dot styles"
  ```

---

## Chunk 2: App Shell

---

### Task 5: Redesign status bar + tab bar in `App.module.css`

**Files:**
- Modify: `frontend/src/App.module.css`

- [ ] **Step 1: Read the file**

  Read `frontend/src/App.module.css` fully.

- [ ] **Step 2: Update `.statusBar`**

  > **Mixed typography:** The spec calls for Inter (sans) on label items and JetBrains Mono on number items. The status bar rule sets a base `font-family: var(--font-mono)` for the whole bar, which is correct for the lap counter on the right. Label items (`.statusItem`, `.statusItemPrimary`) will inherit mono but look fine — if you want strict compliance, add `font-family: var(--font-sans)` to `.statusItem` and keep mono only on the lap counter element. For this implementation, `var(--font-mono)` on the full bar is acceptable.

  ```css
  .statusBar {
    background: linear-gradient(90deg, var(--bg-inset) 0%, var(--bg-surface) 100%);
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    padding: 0 12px;
    gap: 12px;
    font-size: 0.78rem;
    font-family: var(--font-mono);
    white-space: nowrap;
    overflow: hidden;
    z-index: 100;
    height: var(--status-bar-height);
  }
  ```

- [ ] **Step 3: Update `.tabBar` and active tab**

  ```css
  .tabBar {
    background: var(--bg-base);
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    align-items: stretch;
    padding: 0 12px;
    gap: 2px;
    z-index: 90;
  }

  .tabBtn {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 0 14px;
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: var(--font-sans);
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    transition: color var(--transition-fast), border-color var(--transition-fast);
    margin-bottom: -1px;
  }

  .tabBtn:hover {
    color: var(--text-primary);   /* upgraded from --text-secondary — intentional */
  }

  .tabBtnActive {
    color: var(--text-primary);
    border-bottom-color: var(--color-accent);   /* changed from --color-info blue to red */
  }
  ```

- [ ] **Step 4: Upgrade alert strip**

  ```css
  .alertStrip {
    backdrop-filter: blur(8px);
    background: rgba(13, 17, 23, 0.85);
    border-bottom: 1px solid var(--border-subtle);
    padding: 2px 4px;
    z-index: 90;
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex-shrink: 0;
  }

  .alertRow {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 10px;
    font-size: 0.78rem;
    font-family: var(--font-mono);
    border-radius: var(--radius-sm);
    border-left: 3px solid transparent;
    animation: slideInAlert 200ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }
  ```

  Leave the `[data-alert-type]` attribute selectors (`.alertRow[data-alert-type="flag"]` etc.) in place below `.alertRow` — do not remove or rewrite them. Only update the `.alertStrip` and `.alertRow` rules above them.

- [ ] **Step 5: Update session drawer tokens — both `App.module.css` AND `index.css`**

  In `App.module.css`, find `.sessionDrawer` — change `var(--bg-secondary)` → `var(--bg-surface)` and `var(--border-color)` → `var(--border-subtle)`.

  Also in `index.css`, find the global session drawer classes (`.session-drawer-header`, `.session-drawer-active`, `.session-drawer-controls`) which also use `var(--border-color)` and `var(--bg-secondary)`. Apply the same token replacements there.

- [ ] **Step 6: Verify build**

  ```bash
  cd frontend && npm run build 2>&1 | tail -5
  ```
  Expected: exit 0.

- [ ] **Step 7: Commit**

  ```bash
  git add frontend/src/App.module.css frontend/src/index.css
  git commit -m "feat(ui): redesign status bar, tab bar (red accent), alert strip animation"
  ```

---

### Task 6: Add Lucide tab icons + alert key fix in `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Read App.tsx**

  Read `frontend/src/App.tsx` — focus on the tab bar render and alert list render.

- [ ] **Step 2: Import Lucide icons**

  Add to the import block at the top of `App.tsx`:

  ```tsx
  import { Radio, RotateCcw, BarChart2 } from 'lucide-react';
  ```

- [ ] **Step 3: Update tab button renders**

  Find the tab buttons and add icons. Each tab `<button>` gets its icon as a sibling before the label text:

  - Live tab: `<Radio size={14} />`
  - Replay tab: `<RotateCcw size={14} />`
  - Backtest tab: `<BarChart2 size={14} />`

  Example pattern (adapt to actual JSX structure):
  ```tsx
  <button className={`${styles.tabBtn} ${page === 'live' ? styles.tabBtnActive : ''}`} onClick={() => setPage('live')}>
    <Radio size={14} />
    Live
  </button>
  ```

- [ ] **Step 4: Verify alert list uses `key={a.id}`**

  Find the alert `.map()` call. The current code already uses `key={a.id}` — verify this is the case and no change is needed. (This is required for the CSS entry animation to replay on each new alert; index-based keys would prevent it.)

- [ ] **Step 5: Verify build + tests**

  ```bash
  cd frontend && npm run build 2>&1 | tail -5 && npm run test:run 2>&1 | tail -10
  ```
  Expected: build exit 0, tests pass.

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/src/App.tsx
  git commit -m "feat(ui): add Lucide tab icons, fix alert key for CSS animation"
  ```

---

## Chunk 3: Live Dashboard + Leaderboard

---

### Task 7: Update leaderboard row styles in `LiveDashboard.module.css`

**Files:**
- Modify: `frontend/src/pages/LiveDashboard.module.css`
- Read: `frontend/src/pages/LiveDashboard.tsx` (to understand current class names)

- [ ] **Step 1: Read both files**

  Read `LiveDashboard.tsx` and `LiveDashboard.module.css` in full.

- [ ] **Step 2: Verify `.dashboard-grid` gap and add column separators**

  > The column separator lives in `index.css` (the global `.dashboard-grid`), not in `LiveDashboard.module.css`. The actual column wrapper class names in `LiveDashboard.module.css` are `.colLeaderboard`, `.colCenter`, and `.colStrategy`.
  >
  > **Gap check:** `.dashboard-grid` already has `gap: 4px` — no change needed there. Just verify it during read.

  In `index.css`, find `.dashboard-grid` and add a rule targeting the column wrappers. The simplest approach is to target column children directly and exclude the last:

  Add after the `.dashboard-grid` block:

  ```css
  .dashboard-grid > *:not(:last-child) {
    border-right: 1px solid var(--border-subtle);
  }
  ```

  Alternatively, add `border-right: 1px solid var(--border-subtle)` to `.colLeaderboard` and `.colCenter` in `LiveDashboard.module.css` (but NOT `.colStrategy`).

- [ ] **Step 3: Add/update leaderboard row classes in `LiveDashboard.module.css`**

  > The existing pit-now row class is `.lbRowPitNow` (not `.driverRowPitNow`). Selected-row highlight is currently applied via inline `style=` in `LiveDashboard.tsx`. Add the new classes below and update the TSX in Step 5 to use them.

  Add these new classes to `LiveDashboard.module.css`:

  ```css
  /* Position number — medal colors */
  .posP1   { color: #FFD700; font-family: var(--font-mono); font-weight: 700; }
  .posP2   { color: #C0C0C0; font-family: var(--font-mono); font-weight: 700; }
  .posP3   { color: #CD7F32; font-family: var(--font-mono); font-weight: 700; }
  .posRest { color: var(--text-muted); font-family: var(--font-mono); font-weight: 700; }

  /* Gap display */
  .gapGaining { color: var(--status-green); font-family: var(--font-mono); }
  .gapLosing  { color: var(--status-red);   font-family: var(--font-mono); }

  /* Driver row states */
  .lbRow:hover {
    background: rgba(255, 255, 255, 0.03);
    transition: background 100ms;
  }

  .lbRowSelected {
    border-left: 2px solid var(--color-accent);
    box-shadow: inset 4px 0 12px rgba(225, 6, 0, 0.08);
    background: rgba(225, 6, 0, 0.04);
  }

  /* Update existing .lbRowPitNow */
  .lbRowPitNow {
    background: rgba(225, 6, 0, 0.08);
    border-left: 2px solid var(--color-accent);
  }
  ```

- [ ] **Step 4: Add section header style**

  ```css
  .sectionHeader {
    font-size: 0.625rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-secondary);
    padding: 6px 8px;
    font-family: var(--font-sans);
    font-weight: 600;
    border-bottom: 1px solid var(--border-subtle);
  }
  ```

- [ ] **Step 5: Update `LiveDashboard.tsx` to apply new CSS classes**

  **Position medal classes** — in the leaderboard row render, apply based on `driver.position`:

  ```tsx
  const posClass = driver.position === 1 ? styles.posP1
    : driver.position === 2 ? styles.posP2
    : driver.position === 3 ? styles.posP3
    : styles.posRest;
  ```

  Apply to the position number `<span>`: `className={posClass}`

  **Selected row** — replace the current inline `style=` selected-row highlight with `styles.lbRowSelected`. Find where `selectedDriver?.driver_number === driver.driver_number` is checked for row styling and apply the module class instead of inline styles.

  **Gap arrow display** — `gap_to_leader` is always `>= 0` (absolute value). The direction (gaining/losing) is not available in `DriverState`. Use this pragmatic approach: show `▼` and red for all non-leader gaps (they are behind the leader), skip the arrow for P1 (show "LEADER"):

  ```tsx
  const gapDisplay = driver.position === 1
    ? 'LEADER'
    : `▼ ${formatGap(driver.gap_to_leader)}`;
  const gapClass = driver.position === 1 ? '' : styles.gapLosing;
  ```

  This is intentionally simplified — the data doesn't expose a lap-by-lap delta direction field.

- [ ] **Step 6: Verify build + tests**

  ```bash
  cd frontend && npm run build 2>&1 | tail -5 && npm run test:run 2>&1 | tail -5
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add frontend/src/pages/LiveDashboard.tsx frontend/src/pages/LiveDashboard.module.css
  git commit -m "feat(ui): leaderboard medal positions, gap arrows, column separators"
  ```

---

## Chunk 4: Structural Component Changes

---

### Task 8: TrackMap — SVG depth + car dot glow

**Files:**
- Modify: `frontend/src/components/TrackMap.tsx`
- Modify: `frontend/src/components/TrackMap.module.css`

- [ ] **Step 1: Read both files**

- [ ] **Step 2: Update track edge stroke colors**

  In `TrackMap.tsx`, find the SVG `<path>` or `<polyline>` elements for inner/outer track edges and update their `stroke` attributes:

  - Inner edge: `stroke="#1e2530"`
  - Outer edge: `stroke="#2a3441"`

- [ ] **Step 3: Add glow to selected driver dot**

  > The `CarMarker` component already renders an extra pulse ring `<circle>` for selected drivers. Enhance this by adding a drop-shadow filter to the main car dot. Use `teamColor` (not `currentColor` — the spec says `currentColor` but that resolves to black with no SVG `color` attribute set; `teamColor` is visually correct):

  ```tsx
  style={{
    filter: isSelected ? `drop-shadow(0 0 4px ${teamColor})` : undefined,
  }}
  ```

  Apply this to the main car dot `<circle>` element (not the pulse ring). Note: if the `<g>` wrapper has `willChange: transform`, the filter may not render in Safari — test in Chrome/Firefox first; the pulse ring already visible on selected drivers is an acceptable fallback.

- [ ] **Step 4: Update DRS zone stroke color**

  > DRS zones in `TrackMap.tsx` are rendered as `<line>` SVG elements (not filled shapes), so `fill` has no visual effect. The spec calls for a fill overlay (`rgba(0,200,180,0.15)`) but that is impossible on `<line>`. **Implementation deviation:** change the `stroke` color to `rgba(0,200,180,0.6)` and increase `strokeWidth` slightly (e.g. `3px`) to make the teal zone visible. This achieves the spec's visual intent (teal DRS highlight) while adapting to the actual SVG element type.

- [ ] **Step 5: Verify build**

  ```bash
  cd frontend && npm run build 2>&1 | tail -5
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/src/components/TrackMap.tsx frontend/src/components/TrackMap.module.css
  git commit -m "feat(ui): TrackMap — depth stroke colors, selected car glow, teal DRS zones"
  ```

---

### Task 9: TelemetryChart — gradient area fill + card elevation

**Files:**
- Modify: `frontend/src/components/TelemetryChart.tsx`
- Modify: `frontend/src/components/TelemetryChart.module.css`

- [ ] **Step 1: Read both files**

- [ ] **Step 2: Add chart container elevation in module CSS**

  Find the chart container class and apply card elevation:

  ```css
  .chartContainer {
    /* existing layout */
    background: linear-gradient(180deg, var(--bg-elevated) 0%, var(--bg-surface) 100%);
    box-shadow: 0 1px 3px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04);
  }
  ```

- [ ] **Step 3: Add SVG gradient for area fill in `TelemetryChart.tsx`**

  > `TelemetryChart.tsx` uses a **custom SVG implementation**, not Recharts. There is no `<AreaChart>`, `<Area>`, or `<ComposedChart>`. Read the file first to understand the SVG structure, then:

  1. Find the outer `<svg>` element in the chart render.
  2. Add a `<defs>` block as the first child of the `<svg>`:

  ```tsx
  <defs>
    <linearGradient id="speedAreaFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"   stopColor="#3b82f6" stopOpacity={0.15} />
      <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
    </linearGradient>
  </defs>
  ```

  3. Find the speed data `<path>` element (the line path). To make it an area fill, either:
     - Add a second closed `<path>` element that traces the same data points but closes back along the x-axis, with `fill="url(#speedAreaFill)"` and `stroke="none"`, OR
     - If the chart already renders a separate area element, change its `fill` to `url(#speedAreaFill)`.

  Read the existing chart render logic carefully before implementing — the exact approach depends on whether the component already has a separate area/fill path.

- [ ] **Step 4: Add CSS transition for smooth data updates**

  > The spec requires smooth line extension animation. Since `TelemetryChart.tsx` uses a custom SVG (no Recharts), there is no `isAnimationActive` prop. Add a CSS `transition` on the speed data `<path>` element via the module CSS:

  In `TelemetryChart.module.css`, find or add a class for the speed line path and add:

  ```css
  .speedLine {
    transition: d 300ms ease;   /* animates SVG path `d` attribute changes */
  }
  ```

  Apply `className={styles.speedLine}` to the speed data `<path>`. Note: CSS `transition` on SVG `d` attribute requires Chrome 93+ / Firefox 96+ — this is acceptable for a professional desktop tool.

- [ ] **Step 5: Verify build**

  ```bash
  cd frontend && npm run build 2>&1 | tail -5
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/src/components/TelemetryChart.tsx frontend/src/components/TelemetryChart.module.css
  git commit -m "feat(ui): TelemetryChart — gradient area fill, card elevation, animation"
  ```

---

### Task 10: StrategyPanel — pit window gradient + deg line + border-subtle

**Files:**
- Modify: `frontend/src/components/StrategyPanel.tsx`
- Modify: `frontend/src/components/StrategyPanel.module.css`

- [ ] **Step 1: Read both files**

- [ ] **Step 2: Update `.strategySection` border token**

  Find every instance of `var(--border-color)` in `StrategyPanel.module.css` and replace with `var(--border-subtle)`.

- [ ] **Step 3: Update section dividers — hairline only, no box borders**

  Remove any `border: 1px solid ...` from section wrapper classes; replace with `border-bottom: 1px solid var(--border-subtle)` or `border-top: 1px solid var(--border-subtle)` as appropriate.

- [ ] **Step 4: Add pit window gradient in `StrategyPanel.tsx`**

  Find the pit window bar element — typically a `<div>` with an inline width/background style. Update the bar's render to use a gradient:

  ```tsx
  // For the "optimal window" fill, use a gradient centered at ideal
  background: `linear-gradient(90deg, rgba(225,6,0,0.2) 0%, rgba(225,6,0,0.5) 50%, rgba(225,6,0,0.2) 100%)`
  ```

  *(Adapt to actual pit window bar implementation — may be a positioned `<div>` inside a container.)*

- [ ] **Step 5: Add gradient to degradation indicator**

  > `StrategyPanel.tsx` does **not** use a Recharts `<Line>` for degradation. The degradation display is a bar gauge rendered with `<div>` elements. Read the file to find the deg slope/cliff-risk bar and apply a gradient background instead of a flat color:

  Find the degradation severity bar `<div>` (the element whose width is set proportionally to `deg_slope`) and update its inline `style` to use a gradient that reflects severity:

  ```tsx
  // Map deg severity to gradient: low=green, mid=amber, high=red
  const degGradient = `linear-gradient(90deg, #3fb950 0%, #d29922 50%, #f85149 100%)`;
  // Apply to the bar fill div:
  style={{ width: `${barWidth}%`, background: degGradient }}
  ```

  If the bar color is currently set dynamically per severity level, replace that logic with the gradient approach so the color shift is continuous rather than stepped.

- [ ] **Step 6: Verify build**

  ```bash
  cd frontend && npm run build 2>&1 | tail -5
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add frontend/src/components/StrategyPanel.tsx frontend/src/components/StrategyPanel.module.css
  git commit -m "feat(ui): StrategyPanel — pit window gradient, deg line gradient, hairline dividers"
  ```

---

### Task 11: WeatherWidget — swap custom SVGs for Lucide icons

**Files:**
- Modify: `frontend/src/components/WeatherWidget.tsx`
- Modify: `frontend/src/components/WeatherWidget.module.css`

- [ ] **Step 1: Read both files**

- [ ] **Step 2: Remove custom weather SVG sub-components**

  > `WeatherWidget.tsx` exports four named symbols: `WeatherIcon`, `WindArrow`, `TemperatureDisplay`, and `RainIndicator`. `TemperatureDisplay` and `RainIndicator` internally use `WeatherIcon` and `WindArrow` in their render bodies.

  1. Before deleting anything, search for imports of `WeatherIcon`, `WindArrow`, `TemperatureDisplay`, `RainIndicator` across the entire codebase (`frontend/src`) — if any other file imports them, update those imports first.
  2. Delete the `WeatherIcon`, `WindArrow`, `TemperatureDisplay`, and `RainIndicator` sub-component definitions from `WeatherWidget.tsx`.
  3. Remove all four from the file's named export statement at the bottom.
  4. In the main `WeatherWidget` render, replace any usage of `<TemperatureDisplay>`, `<RainIndicator>`, `<WeatherIcon>`, `<WindArrow>` with Lucide icons (Step 4 below).

- [ ] **Step 3: Import Lucide icons**

  ```tsx
  import { Thermometer, Droplets, Wind } from 'lucide-react';
  ```

- [ ] **Step 4: Replace usage in JSX**

  Find each weather metric render and replace custom SVG components with Lucide:
  - Temperature field: `<Thermometer size={14} />`
  - Humidity/rain field: `<Droplets size={14} />`
  - Wind field: `<Wind size={14} />`

- [ ] **Step 5: Apply mono font to numeric values**

  Wherever a weather value number is rendered, add `style={{ fontFamily: 'var(--font-mono)' }}` or apply a CSS class with `font-family: var(--font-mono)`.

- [ ] **Step 6: Apply card elevation in module CSS**

  Add to the widget container class:

  ```css
  .weatherWidget {
    /* existing */
    background: var(--bg-surface);
    box-shadow: 0 1px 3px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04);
  }
  ```

- [ ] **Step 7: Verify build + tests**

  ```bash
  cd frontend && npm run build 2>&1 | tail -5 && npm run test:run 2>&1 | tail -5
  ```

- [ ] **Step 8: Commit**

  ```bash
  git add frontend/src/components/WeatherWidget.tsx frontend/src/components/WeatherWidget.module.css
  git commit -m "feat(ui): WeatherWidget — Lucide icons, mono numerics, card elevation"
  ```

---

### Task 12: RaceProgressBar — replace legacy alias tokens

**Files:**
- Modify: `frontend/src/components/RaceProgressBar.module.css`
- Modify: `frontend/src/components/RaceProgressBar.tsx` (if inline styles use legacy tokens)

- [ ] **Step 1: Read both files**

- [ ] **Step 2: Replace in BOTH module CSS and inline styles in `RaceProgressBar.tsx`**

  Apply the migration in `RaceProgressBar.module.css`:
  - `--accent-cyan` → `--status-blue`
  - `--accent-magenta` → `--color-accent`
  - `--accent-yellow` → `--status-amber`
  - `--accent-purple` → `--color-purple`

  Also search `RaceProgressBar.tsx` for inline `style=` props containing these legacy token names (e.g. `color: 'var(--accent-cyan)'`, `boxShadow: '... var(--accent-cyan)'`) and apply the same replacements there. There are multiple inline style usages including in the `EventMarker` sub-component.

- [ ] **Step 3: Update progress fill gradient**

  Find the bar fill gradient and set:

  ```css
  background: linear-gradient(90deg, var(--status-blue), var(--color-accent));
  ```

- [ ] **Step 4: Verify build**

  ```bash
  cd frontend && npm run build 2>&1 | tail -5
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/components/RaceProgressBar.tsx frontend/src/components/RaceProgressBar.module.css
  git commit -m "feat(ui): RaceProgressBar — replace legacy alias tokens, blue→red gradient"
  ```

---

## Chunk 5: Token Migration — All Remaining Files

> Apply the token migration table from the spec to every remaining file. These are all mechanical replacements using the old→new mapping. Legacy aliases in `index.css` mean visual breakage won't happen even if a file is missed, but canonical token names should be updated.

**Token migration table (quick reference):**
| Find | Replace |
|------|---------|
| `var(--bg-primary)` | `var(--bg-base)` |
| `var(--bg-secondary)` | `var(--bg-surface)` |
| `var(--bg-tertiary)` | `var(--bg-elevated)` |
| `var(--bg-card)` | `var(--bg-surface)` |
| `var(--bg-card-hover)` | `var(--bg-elevated)` |
| `var(--border-color)` | `var(--border-subtle)` |
| `var(--text-tertiary)` | `var(--text-muted)` |
| `var(--color-info)` *(non-alert use)* | `var(--color-accent)` |
| `var(--accent-cyan)` | `var(--status-blue)` |
| `var(--accent-purple)` | `var(--color-purple)` |
| `var(--accent-magenta)` | `var(--color-accent)` |

---

### Task 13: Migrate App.module.css remaining token references

**Files:**
- Modify: `frontend/src/App.module.css`

- [ ] **Step 1: Read file**, find any remaining `var(--bg-secondary)`, `var(--border-color)`, `var(--text-tertiary)`.
- [ ] **Step 2: Apply migration table** — replace all legacy tokens.
- [ ] **Step 3: Build**, commit: `"refactor(ui): App.module.css token migration"`

---

### Task 14: Migrate SessionSelector

**Files:**
- Modify: `frontend/src/components/SessionSelector.tsx`
- Modify: `frontend/src/components/SessionSelector.module.css`

- [ ] **Step 1: Read both files**
- [ ] **Step 2: Apply migration table** — specifically `var(--color-info)` active border → `var(--color-accent)`
- [ ] **Step 3: Build**, commit: `"refactor(ui): SessionSelector — red accent active border, token migration"`

---

### Task 15: Migrate DriverTable

**Files:**
- Modify: `frontend/src/components/DriverTable.tsx`
- Modify: `frontend/src/components/DriverTable.module.css`

- [ ] **Step 1: Read both files**
- [ ] **Step 2: Apply migration table**
- [ ] **Step 3: Build**, commit: `"refactor(ui): DriverTable token migration"`

---

### Task 16: Migrate MetricCard

**Files:**
- Modify: `frontend/src/components/MetricCard.tsx`
- Modify: `frontend/src/components/MetricCard.module.css`

- [ ] **Step 1: Read both files**
- [ ] **Step 2: Apply migration table** — pay attention to `--accent-cyan`, `--accent-purple`, `--color-info` usages
- [ ] **Step 3: Build**, commit: `"refactor(ui): MetricCard token migration"`

---

### Task 17: Migrate TelemetryPanel

**Files:**
- Modify: `frontend/src/components/TelemetryPanel.tsx`
- Modify: `frontend/src/components/TelemetryPanel.module.css`

- [ ] **Step 1: Read both files**
- [ ] **Step 2: Apply migration table**
- [ ] **Step 3: Build**, commit: `"refactor(ui): TelemetryPanel token migration"`

---

### Task 18: Migrate ReplayPage + BacktestPage

**Files:**
- Modify: `frontend/src/pages/ReplayPage.tsx` + `ReplayPage.module.css`
- Modify: `frontend/src/pages/BacktestPage.tsx` + `BacktestPage.module.css`

- [ ] **Step 1: Read all 4 files**
- [ ] **Step 2: Apply migration table to both pages** — including inline `style=` props in `.tsx` files
- [ ] **Step 3: Build**, commit: `"refactor(ui): ReplayPage + BacktestPage token migration"`

---

### Task 19: Migrate remaining components

**Files (read + apply migration table to each):**
- `frontend/src/components/TyreLifeChart.tsx` + `.module.css`
- `frontend/src/components/DRSZoneOverlay.tsx` + `.module.css`
- `frontend/src/components/ExplainabilityPanel.tsx` + `.module.css`
- `frontend/src/components/CompetitorPredictions.tsx` + `.module.css`
- `frontend/src/components/PositionProbabilityChart.tsx` + `.module.css`
- `frontend/src/components/BrakingZoneIndicator.tsx` + `.module.css`
- `frontend/src/components/StrategyComparison.tsx` + `.module.css`
- `frontend/src/components/PitRejoinVisualizer.tsx` + `.module.css`
- `frontend/src/components/RaceMessages.module.css`

- [ ] **Step 1: Read all files** (batch in parallel)
- [ ] **Step 2: Apply migration table to all** — especially inline `style=` props in `.tsx`
- [ ] **Step 3: Build + tests**

  ```bash
  cd frontend && npm run build 2>&1 | tail -5 && npm run test:run 2>&1 | tail -10
  ```
  Expected: build exit 0, all tests pass.

- [ ] **Step 4: Commit**

  ```bash
  git add \
    frontend/src/components/TyreLifeChart.tsx frontend/src/components/TyreLifeChart.module.css \
    frontend/src/components/DRSZoneOverlay.tsx frontend/src/components/DRSZoneOverlay.module.css \
    frontend/src/components/ExplainabilityPanel.tsx frontend/src/components/ExplainabilityPanel.module.css \
    frontend/src/components/CompetitorPredictions.tsx frontend/src/components/CompetitorPredictions.module.css \
    frontend/src/components/PositionProbabilityChart.tsx frontend/src/components/PositionProbabilityChart.module.css \
    frontend/src/components/BrakingZoneIndicator.tsx frontend/src/components/BrakingZoneIndicator.module.css \
    frontend/src/components/StrategyComparison.tsx frontend/src/components/StrategyComparison.module.css \
    frontend/src/components/PitRejoinVisualizer.tsx frontend/src/components/PitRejoinVisualizer.module.css \
    frontend/src/components/RaceMessages.module.css
  git commit -m "refactor(ui): migrate remaining components to new token system"
  ```

---

### Task 20: Final build + smoke test

- [ ] **Step 1: Full build**

  ```bash
  cd frontend && npm run build 2>&1
  ```
  Expected: exit 0, no warnings about undefined CSS variables.

- [ ] **Step 2: Run all tests**

  ```bash
  cd frontend && npm run test:run 2>&1
  ```
  Expected: all pass.

- [ ] **Step 3: Run dev server and visually verify**

  ```bash
  cd frontend && npm run dev
  ```
  Open `http://localhost:5173` and verify:
  - [ ] Status bar has gradient background + separator
  - [ ] Active tab has red underline (not blue)
  - [ ] Tab icons appear (Radio, RotateCcw, BarChart2)
  - [ ] Alert rows animate in on mount
  - [ ] Driver leaderboard shows medal colors for P1/P2/P3
  - [ ] Selected row has red left border
  - [ ] Track map car dots glow on selection
  - [ ] Weather widget shows Lucide icons
  - [ ] Charts have gradient fills

- [ ] **Step 4: Final commit**

  ```bash
  git add -A
  git commit -m "feat(ui): industry-ready Refined Dark SaaS redesign complete"
  ```
