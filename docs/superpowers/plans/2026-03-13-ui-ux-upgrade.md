# UI/UX Industry-Grade Upgrade — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the F1 Race Strategy Workbench UI to industry-grade professional standard: CSS Modules per component, updated palette (deeper blacks + F1 red accent), improved information hierarchy, data density improvements, and new data surfaces from previously unused backend fields.

**Architecture:** CSS Modules replace the monolithic `index.css` (750 lines) — each component gets a scoped `.module.css` co-located with its source file. Global `index.css` shrinks to `:root` vars, resets, and top-level grid. Alert state moves from local `useState` in `LiveDashboard` to the Zustand store. Backend `recent_pits` is extended with compound data.

**Tech Stack:** React 18, TypeScript, Vite (CSS Modules built-in), Zustand, Python/FastAPI backend, Vitest for tests.

**Spec:** `docs/superpowers/specs/2026-03-13-ui-ux-upgrade-design.md`

---

## Chunk 1: Foundation — Palette Update + Store Additions

### Task 1: Update index.css palette

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Update CSS variables in `:root`**

In `frontend/src/index.css`, update the `:root` block. Change these values and add two new variables:

```css
:root {
  /* Background colors — deeper blacks */
  --bg-primary: #08090b;
  --bg-secondary: #0f1117;
  --bg-tertiary: #161b22;
  --bg-card: #0f1117;
  --bg-card-hover: #161b22;

  /* NEW: F1 red accent — for PIT_NOW badges, CLIFF label, primary interactive */
  --color-accent: #e10600;

  /* Info/blue — demoted to informational only */
  --color-info: #3b82f6;

  /* Text */
  --text-primary: #f0f0f0;
  --text-secondary: #6b7280;
  /* --text-tertiary and --text-muted: UNCHANGED — keep existing values */

  /* NEW: border color — replaces rgba(255,255,255,0.06) literals throughout */
  --border-color: #1f2937;

  /* Layout dimensions — density improvements */
  --status-bar-height: 28px;   /* was 32px */
  --tab-bar-height: 24px;      /* was 28px */
  --row-height: 26px;          /* was 28px */
  --leaderboard-width: 300px;  /* was 320px */
  --strategy-width: 340px;     /* was 360px */
}
```

Keep all other variables (status colors, tyre colors, spacing, radius, transitions) **unchanged**.

- [ ] **Step 2: Verify app still loads**

```bash
cd frontend && npm run dev
```

Open http://localhost:5173 — the app should render with slightly darker backgrounds. No red errors in console.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat: update palette — deeper blacks, F1 red accent, density vars"
```

---

### Task 2: Add alert state to raceStore

**Files:**
- Modify: `frontend/src/store/raceStore.ts`
- Test: `frontend/src/store/raceStore.test.ts` (create new)

Alert state is currently local `useState` inside `LiveDashboard.tsx`. Moving it to the store lets `App.tsx` read alerts directly without prop drilling.

- [ ] **Step 1: Write failing test**

Create `frontend/src/store/raceStore.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { useRaceStore } from './raceStore';

describe('raceStore — alert slice', () => {
    beforeEach(() => {
        useRaceStore.getState().reset();
    });

    it('starts with empty alerts', () => {
        expect(useRaceStore.getState().alerts).toEqual([]);
    });

    it('addAlert adds an alert', () => {
        useRaceStore.getState().addAlert('PIT_NOW', 'HAM — PIT NOW');
        const { alerts } = useRaceStore.getState();
        expect(alerts).toHaveLength(1);
        expect(alerts[0].type).toBe('PIT_NOW');
        expect(alerts[0].message).toBe('HAM — PIT NOW');
        expect(alerts[0].id).toBeTruthy();
        expect(alerts[0].ts).toBeGreaterThan(0);
    });

    it('does not duplicate same type within 30s', () => {
        useRaceStore.getState().addAlert('SC', 'SAFETY CAR');
        useRaceStore.getState().addAlert('SC', 'SAFETY CAR AGAIN');
        expect(useRaceStore.getState().alerts).toHaveLength(1);
    });

    it('dismissAlert removes alert by id', () => {
        useRaceStore.getState().addAlert('FLAG', 'YELLOW FLAG');
        const id = useRaceStore.getState().alerts[0].id;
        useRaceStore.getState().dismissAlert(id);
        expect(useRaceStore.getState().alerts).toHaveLength(0);
    });

    it('reset clears alerts', () => {
        useRaceStore.getState().addAlert('FLAG', 'RED FLAG');
        useRaceStore.getState().reset();
        expect(useRaceStore.getState().alerts).toHaveLength(0);
    });
});
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd frontend && npx vitest run src/store/raceStore.test.ts
```

Expected: FAIL — `addAlert is not a function` or similar.

- [ ] **Step 3: Add alert types + slice to raceStore.ts**

At the top of `frontend/src/store/raceStore.ts`, after the imports, add:

```typescript
// =============================================================================
// Alert Types
// =============================================================================

export type AlertType = 'FLAG' | 'SC' | 'PIT_NOW' | 'THREAT';

export interface Alert {
    id: string;
    type: AlertType;
    message: string;
    ts: number;
}
```

In the `RaceStore` interface, add:

```typescript
// Alerts
alerts: Alert[];
addAlert: (type: AlertType, message: string) => void;
dismissAlert: (id: string) => void;
```

In `initialState`, add:

```typescript
alerts: [] as Alert[],
```

In the store implementation (inside `subscribeWithSelector`), add these actions:

```typescript
addAlert: (type, message) => {
    const now = Date.now();
    const id = `${type}-${now}`;
    set(state => {
        const recent = state.alerts.find(a => a.type === type && now - a.ts < 30000);
        if (recent) return {};
        const newAlert: Alert = { id, type, message, ts: now };
        return { alerts: [newAlert, ...state.alerts].slice(0, 5) };
    });
},

dismissAlert: (id) => {
    set(state => ({ alerts: state.alerts.filter(a => a.id !== id) }));
},
```

In the `reset` action, `reset: () => set(initialState)` already covers alerts since `initialState` now includes `alerts: []`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npx vitest run src/store/raceStore.test.ts
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store/raceStore.ts frontend/src/store/raceStore.test.ts
git commit -m "feat: add alert state slice to raceStore"
```

---

### Task 3: Add recentPits to raceStore

**Files:**
- Modify: `frontend/src/store/raceStore.ts`
- Test: `frontend/src/store/raceStore.test.ts`

- [ ] **Step 1: Add failing test**

Append to `frontend/src/store/raceStore.test.ts`:

```typescript
describe('raceStore — recentPits', () => {
    beforeEach(() => {
        useRaceStore.getState().reset();
    });

    it('starts with empty recentPits', () => {
        expect(useRaceStore.getState().recentPits).toEqual([]);
    });

    it('updateState maps recent_pits to recentPits', () => {
        useRaceStore.getState().updateState({
            recent_pits: [
                { driver_number: 44, lap_number: 32, pit_duration: 23.4, compound: 'SOFT', timestamp: '2024-01-01T00:00:00' }
            ]
        } as any);
        const { recentPits } = useRaceStore.getState();
        expect(recentPits).toHaveLength(1);
        expect(recentPits[0].driver_number).toBe(44);
        expect(recentPits[0].compound).toBe('SOFT');
    });

    it('reset clears recentPits', () => {
        useRaceStore.getState().updateState({
            recent_pits: [{ driver_number: 1, lap_number: 5, pit_duration: 20, compound: 'MEDIUM', timestamp: '2024-01-01' }]
        } as any);
        useRaceStore.getState().reset();
        expect(useRaceStore.getState().recentPits).toEqual([]);
    });
});
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd frontend && npx vitest run src/store/raceStore.test.ts
```

Expected: FAIL — `recentPits` is undefined.

- [ ] **Step 3: Add recentPits to store**

In `frontend/src/types/index.ts`, update the `recent_pits` field in `RaceState`:

```typescript
recent_pits?: Array<{
    driver_number: number;
    lap_number: number;
    pit_duration: number | null;
    compound: string | null;
    timestamp: string;
}>;
```

In `frontend/src/store/raceStore.ts`:

Add to `RaceStore` interface:
```typescript
recentPits: Array<{
    driver_number: number;
    lap_number: number;
    pit_duration: number | null;
    compound: string | null;
    timestamp: string;
}>;
```

Add to `initialState`:
```typescript
recentPits: [],
```

Add to `updateState` action (after the `track_config` mapping line):
```typescript
if (state.recent_pits !== undefined) updates.recentPits = state.recent_pits ?? [];
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npx vitest run src/store/raceStore.test.ts
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store/raceStore.ts frontend/src/types/index.ts frontend/src/store/raceStore.test.ts
git commit -m "feat: add recentPits to raceStore and update RaceState type"
```

---

## Chunk 2: Backend — Extend recent_pits with Compound

### Task 4: Add compound to pit records in reducers.py

**Files:**
- Modify: `src/rsw/state/reducers.py`
- Test: `tests/` (find existing test file for reducers, or create `tests/test_reducers.py`)

The `apply_pits` function builds `pit_record` dicts. It currently omits compound. The driver's compound at pit time is available from `state.drivers`.

- [ ] **Step 1: Find or create test file**

```bash
find /Users/cagancaliskan/Desktop/İşler/F1/tests -name "*.py" | head -20
```

If `tests/test_reducers.py` exists, add to it. Otherwise create it.

- [ ] **Step 2: Write failing test**

Add to the reducers test file:

```python
from src.rsw.state.reducers import apply_pits
from src.rsw.state.schemas import RaceState, DriverState
from src.rsw.ingest.base import PitData
from datetime import datetime


def test_apply_pits_includes_compound():
    """recent_pits records must include the driver's compound at pit time."""
    driver = DriverState(driver_number=44, compound="SOFT")
    state = RaceState(drivers={44: driver})   # integer key — RaceState.drivers is dict[int, DriverState]
    pit = PitData(
        driver_number=44,
        lap_number=32,
        pit_duration=23.4,
        timestamp=datetime(2024, 1, 1),
    )

    new_state = apply_pits(state, [pit])

    assert len(new_state.recent_pits) == 1
    record = new_state.recent_pits[0]
    assert record["driver_number"] == 44
    assert record["lap_number"] == 32
    assert record["pit_duration"] == 23.4
    assert record["compound"] == "SOFT"


def test_apply_pits_compound_none_for_unknown_driver():
    """Compound is None when driver not found in state."""
    state = RaceState(drivers={})  # empty — driver 99 not present
    pit = PitData(
        driver_number=99,
        lap_number=10,
        pit_duration=20.0,
        timestamp=datetime(2024, 1, 1),
    )

    new_state = apply_pits(state, [pit])

    assert new_state.recent_pits[0]["compound"] is None
```

- [ ] **Step 3: Run to verify it fails**

```bash
cd /Users/cagancaliskan/Desktop/İşler/F1 && python -m pytest tests/test_reducers.py::test_apply_pits_includes_compound -v
```

Expected: FAIL — `compound` key not in record.

- [ ] **Step 4: Update apply_pits in reducers.py**

In `src/rsw/state/reducers.py`, find the `apply_pits` function and update the `pit_record` dict to include compound:

```python
driver_state = state.drivers.get(pit.driver_number)  # integer key — matches dict[int, DriverState]
pit_record = {
    "driver_number": pit.driver_number,
    "lap_number": pit.lap_number,
    "pit_duration": pit.pit_duration,
    "compound": driver_state.compound if driver_state else None,
    "timestamp": pit.timestamp.isoformat(),
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/cagancaliskan/Desktop/İşler/F1 && python -m pytest tests/test_reducers.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/rsw/state/reducers.py tests/test_reducers.py
git commit -m "feat: include compound in recent_pits pit records"
```

---

## Chunk 3: Alert System Refactor

### Task 5: Create useAlerts hook

> **Sequencing note:** Task 2 (Chunk 1) must be completed first — `Alert` and `AlertType` are exported from `raceStore.ts` and imported here. If implementing out of order, complete Task 2 before this task.

**Files:**
- Create: `frontend/src/hooks/useAlerts.ts`
- Modify: `frontend/src/hooks/index.ts`

The alert generation `useEffect` logic moves from `LiveDashboard.tsx` into a dedicated hook. `LiveDashboard.tsx` calls the hook. `App.tsx` reads `alerts` from the store.

- [ ] **Step 1: Create the hook**

Create `frontend/src/hooks/useAlerts.ts`:

```typescript
/**
 * useAlerts — subscribes to race state and dispatches alerts to raceStore.
 *
 * Call this hook once from LiveDashboard. It generates alerts for:
 * - Safety car / red flag / yellow flag deployment
 * - PIT_NOW recommendations
 * - Undercut threats
 *
 * Alerts are stored in raceStore.alerts and consumed by App.tsx alert strip.
 */
import { useEffect, useRef } from 'react';
import { useRaceStore } from '../store/raceStore';

export function useAlerts() {
    const addAlert = useRaceStore(s => s.addAlert);
    const safetycar = useRaceStore(s => s.safetycar);
    const redFlag = useRaceStore(s => s.redFlag);
    const vsc = useRaceStore(s => s.virtualSafetyCar);
    const flags = useRaceStore(s => s.flags);
    const sortedDrivers = useRaceStore(s => s.sortedDrivers);

    const prevRef = useRef({ sc: false, red: false, vsc: false, flags: [] as string[] });

    // Flag / SC alerts
    useEffect(() => {
        const prev = prevRef.current;
        if (redFlag && !prev.red) addAlert('FLAG', 'RED FLAG DEPLOYED');
        if (safetycar && !prev.sc) addAlert('SC', 'SAFETY CAR DEPLOYED');
        if (vsc && !prev.vsc) addAlert('SC', 'VIRTUAL SAFETY CAR');
        const hasYellow = flags.some(f => f === 'YELLOW' || f === 'DOUBLE_YELLOW');
        const prevHasYellow = prev.flags.some(f => f === 'YELLOW' || f === 'DOUBLE_YELLOW');
        if (hasYellow && !prevHasYellow) addAlert('FLAG', 'YELLOW FLAG');
        prevRef.current = { sc: safetycar, red: redFlag, vsc, flags };
    }, [redFlag, safetycar, vsc, flags, addAlert]);

    // PIT_NOW / undercut alerts
    useEffect(() => {
        sortedDrivers.forEach(d => {
            if (d.pit_recommendation === 'PIT_NOW') {
                addAlert('PIT_NOW', `${d.name_acronym} — PIT NOW (cliff: ${Math.round((d.cliff_risk || 0) * 100)}%)`);
            }
            if (d.undercut_threat) {
                addAlert('THREAT', `${d.name_acronym} — UNDERCUT THREAT from ${(d.position ?? 0) > 1 ? `P${(d.position ?? 0) - 1}` : 'behind'}`);
            }
        });
    }, [sortedDrivers, addAlert]);
}
```

- [ ] **Step 2: Create hooks/index.ts (if it does not exist)**

Create `frontend/src/hooks/index.ts` (new file — this directory/file may not exist yet):

```typescript
export { useAlerts } from './useAlerts';
```

If `frontend/src/hooks/index.ts` already exists, append the export line.

- [ ] **Step 3: Replace alert logic in LiveDashboard.tsx**

In `frontend/src/pages/LiveDashboard.tsx`:

1. Remove the `AlertType`, `Alert` interface definitions at the top (they now live in `raceStore.ts` and are exported from there).
2. Remove the `useState<Alert[]>` and `alertTimeouts` ref and `addAlert`/`dismissAlert` callbacks and their `useEffect` hooks.
3. Remove the `prevFlagsRef` ref.
4. Add at the top of the component body:
   ```typescript
   useAlerts();
   ```
5. Read alerts from the store:
   ```typescript
   // alerts are now in App.tsx — remove the alert banner JSX from LiveDashboard
   ```
6. Delete the `{/* Alert Banner */}` JSX block entirely from the `LiveDashboard` return.
7. Update imports: add `useAlerts` import from `'../hooks'`.

- [ ] **Step 4: Add alert strip to App.tsx**

In `frontend/src/App.tsx`:

1. Add imports:
   ```typescript
   import { useRaceStore } from './store/raceStore';
   import type { Alert } from './store/raceStore';
   ```
   (these may already be imported; add what's missing)

2. Inside the `App` component, add:
   ```typescript
   const alerts = useRaceStore(s => s.alerts);
   const dismissAlert = useRaceStore(s => s.dismissAlert);
   ```

3. Update the app container `grid-template-rows` to include the alert strip. The container currently uses `.app-container` which has `grid-template-rows: var(--status-bar-height) var(--tab-bar-height) 1fr`. We need to add the alert strip as a conditional row. The simplest approach: render the alert strip between `<nav>` (tab bar) and `<main>` unconditionally but with `display: none` when empty:

   After the `</nav>` closing tag and before `<main className="main-content">`, add:
   ```tsx
   {/* Alert Strip */}
   {alerts.length > 0 && (
       <div className="alert-strip">
           {alerts.map(a => (
               <div key={a.id} className={`alert-row alert-${a.type.toLowerCase()}`}>
                   <span className="alert-badge">{a.type}</span>
                   <span className="alert-msg">{a.message}</span>
                   <button className="alert-dismiss" onClick={() => dismissAlert(a.id)}>×</button>
               </div>
           ))}
       </div>
   )}
   ```

4. Fix `.app-container` grid to accommodate the optional alert strip row.

   In `frontend/src/index.css`, update `.app-container`:
   ```css
   .app-container {
     display: grid;
     grid-template-rows: var(--status-bar-height) var(--tab-bar-height) auto 1fr;
     height: 100vh;
     overflow: hidden;
   }
   ```
   The `auto` row collapses to `0` when the alert strip is not rendered (conditional), and expands to fit its content when rendered. The `1fr` row remains the main content area.

   Also rename `.alert-banner` to `.alert-strip` in `index.css`:
   ```css
   .alert-strip {
       background: rgba(225, 6, 0, 0.08);
       border-bottom: 1px solid var(--border-color);
       padding: 2px 4px;
       z-index: 90;
   }
   ```
   Keep `.alert-row`, `.alert-badge`, `.alert-msg`, `.alert-dismiss` as-is.

- [ ] **Step 5: Verify the app still works**

```bash
cd frontend && npm run dev
```

Open http://localhost:5173. Load a session, check that alerts appear in the strip below the tab bar (not inside the dashboard). Check no TypeScript errors: `npx tsc --noEmit`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useAlerts.ts frontend/src/hooks/index.ts frontend/src/pages/LiveDashboard.tsx frontend/src/App.tsx frontend/src/index.css
git commit -m "feat: move alert state to raceStore, extract useAlerts hook, alert strip in App.tsx"
```

---

## Chunk 4: Layout Density + Information Hierarchy

### Task 6: Panel separators + section headers

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/components/StrategyPanel.tsx`

- [ ] **Step 1: Replace rgba border literals in index.css**

In `frontend/src/index.css`, replace all occurrences of:
- `rgba(255, 255, 255, 0.06)` → `var(--border-color)`
- `rgba(255, 255, 255, 0.05)` → `var(--border-color)`
- `rgba(255,255,255,0.06)` → `var(--border-color)`
- `rgba(255,255,255,0.05)` → `var(--border-color)`

Use a find-and-replace in your editor across the file.

- [ ] **Step 2: Update StrategyPanel strategy-section-label**

In `frontend/src/components/StrategyPanel.tsx`, find all places where section headers are rendered with `var(--text-muted)` inline style or the `.strategy-section-label` class. Update their color to `var(--text-secondary)` and ensure they use: `fontSize: '10px', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em'`.

This ensures all section headers are visually consistent.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css frontend/src/components/StrategyPanel.tsx
git commit -m "feat: border-color var, unified section header style"
```

---

### Task 7: Information hierarchy — PIT_NOW badge + cliff threshold + undercut icons

**Files:**
- Modify: `frontend/src/components/StrategyPanel.tsx`
- Modify: `frontend/src/pages/LiveDashboard.tsx` (Leaderboard section)

- [ ] **Step 1: Update PIT_NOW badge in StrategyPanel**

In `frontend/src/components/StrategyPanel.tsx`, find the recommendation badge rendering. Look for where `pit_recommendation === 'PIT_NOW'` styles are applied. Change the color from `var(--status-red)` to `var(--color-accent)`. Ensure the badge text renders in Orbitron font and uppercase:

```tsx
style={{
    backgroundColor: 'var(--color-accent)',
    color: '#fff',
    fontFamily: "'Orbitron', sans-serif",
    fontWeight: 700,
    fontSize: '0.7rem',
    letterSpacing: '0.08em',
    padding: '2px 6px',
    borderRadius: 'var(--radius-sm)',
    textTransform: 'uppercase',
}}
```

- [ ] **Step 2: Update PIT_NOW in leaderboard row**

In `frontend/src/pages/LiveDashboard.tsx` (or wherever `lb-row-pit-now` CSS class styling lives), find the leaderboard row that highlights PIT_NOW. Update the color reference from `var(--status-red)` to `var(--color-accent)`. This may be in `index.css` under `.lb-row-pit-now`. Update that class:

```css
.lb-row-pit-now {
    background: rgba(225, 6, 0, 0.12);
    border-left: 2px solid var(--color-accent);
}
```

- [ ] **Step 3: Update cliff threshold in StrategyPanel**

In `frontend/src/components/StrategyPanel.tsx`, find the `getCliffColor` function (around lines 60–65). Update the threshold from `0.7` to `0.8`:

```typescript
function getCliffColor(cliffRisk: number): string {
    if (cliffRisk > 0.8) return 'var(--color-accent)';   // was var(--status-red) at 0.7 — updated to 0.8 per spec
    if (cliffRisk > 0.4) return 'var(--status-amber)';   // amber threshold unchanged from current code
    return 'var(--status-green)';
}
```

- [ ] **Step 4: Add CLIFF label to tyre life bar**

In `frontend/src/components/StrategyPanel.tsx`, find where the cliff risk percentage is displayed (the tyre life bar section). Immediately after or alongside the percentage, add a conditional CLIFF label:

```tsx
{(driver.cliff_risk ?? 0) > 0.8 && (
    <span style={{
        fontFamily: "'Orbitron', sans-serif",
        fontSize: '0.65rem',
        fontWeight: 700,
        color: 'var(--color-accent)',
        letterSpacing: '0.1em',
        marginLeft: '6px',
    }}>
        CLIFF
    </span>
)}
```

- [ ] **Step 5: Add undercut/overcut icons to leaderboard rows**

In `frontend/src/pages/LiveDashboard.tsx`, in the `Leaderboard` sub-component (look for the inline table/grid rendering around lines 250+), find the Status column cell. Add undercut/overcut badges:

```tsx
{/* Inside the status cell of each driver row */}
{driver.undercut_threat && (
    <span title="Undercut threat" style={{ color: 'var(--status-amber)', fontSize: '0.75rem' }}>⬇</span>
)}
{driver.overcut_opportunity && (
    <span title="Overcut opportunity" style={{ color: 'var(--status-green)', fontSize: '0.75rem' }}>⬆</span>
)}
```

- [ ] **Step 6: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/StrategyPanel.tsx frontend/src/pages/LiveDashboard.tsx frontend/src/index.css
git commit -m "feat: PIT_NOW uses accent red, cliff threshold 0.8, CLIFF label, undercut icons in leaderboard"
```

---

## Chunk 5: New Data Surfaces

### Task 8: Pit window range bar in StrategyPanel

**Files:**
- Modify: `frontend/src/components/StrategyPanel.tsx`

- [ ] **Step 1: Find the pit window display**

In `frontend/src/components/StrategyPanel.tsx`, find where `pit_window_ideal` is displayed. It likely renders something like "Pit Window: Lap X". Replace this with a full range display.

- [ ] **Step 2: Add the range bar**

Replace the existing pit window display with:

```tsx
{/* Pit Window Range */}
{driver.pit_window_min != null && driver.pit_window_min > 0 && (
    <div style={{ marginBottom: '8px' }}>
        <div style={{ fontSize: '10px', fontWeight: 500, textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '4px', letterSpacing: '0.06em' }}>
            PIT WINDOW
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}>
            <span style={{ color: 'var(--text-secondary)' }}>L{driver.pit_window_min}</span>
            <div style={{ flex: 1, height: '3px', background: 'var(--bg-tertiary)', borderRadius: '2px', position: 'relative' }}>
                {/* Ideal marker */}
                {driver.pit_window_ideal != null && (
                    <div style={{
                        position: 'absolute',
                        left: `${Math.max(0, Math.min(100, ((driver.pit_window_ideal - driver.pit_window_min) / Math.max(1, (driver.pit_window_max ?? driver.pit_window_ideal) - driver.pit_window_min)) * 100))}%`,
                        top: '-2px',
                        width: '2px',
                        height: '7px',
                        background: 'var(--color-accent)',
                        borderRadius: '1px',
                    }} />
                )}
            </div>
            <span style={{ color: 'var(--text-secondary)' }}>L{driver.pit_window_max ?? driver.pit_window_ideal}</span>
        </div>
        {driver.pit_window_ideal != null && (
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                Ideal: L{driver.pit_window_ideal}
            </div>
        )}
    </div>
)}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/StrategyPanel.tsx
git commit -m "feat: show full pit window range (min/ideal/max) in StrategyPanel"
```

---

### Task 9: Wire PitRejoinVisualizer in StrategyPanel

**Files:**
- Modify: `frontend/src/components/StrategyPanel.tsx`
- Modify: `frontend/src/components/PitRejoinVisualizer.tsx` (if needed)

- [ ] **Step 1: Understand the current inline rejoin block**

In `frontend/src/components/StrategyPanel.tsx`, find lines 327–343 (the inline "Predicted Rejoin" block). Note its current output.

- [ ] **Step 2: Add store selector for allDrivers in StrategyPanel**

`StrategyPanel.tsx` already calls `useRaceStore`. Add:

```typescript
const sortedDrivers = useRaceStore(s => s.sortedDrivers);
const currentLap = useRaceStore(s => s.currentLap);
```

- [ ] **Step 3: Replace inline block with PitRejoinVisualizer**

Import `PitRejoinVisualizer` at the top of `StrategyPanel.tsx`:

```typescript
import PitRejoinVisualizer from './PitRejoinVisualizer';
```

Check `PitRejoinVisualizer`'s props interface. It expects `allDrivers` and likely `selectedDriver` or similar. Read the component signature and pass accordingly.

Replace the inline "Predicted Rejoin" block (lines 327–343) with:

```tsx
{/* Rejoin Visualizer — shown when driver is in pit window or pitting */}
{((currentLap >= (driver.pit_window_min ?? 0) &&
   currentLap <= (driver.pit_window_max ?? 0) &&
   (driver.pit_window_min ?? 0) > 0) ||
  driver.in_pit === true) && (
    <PitRejoinVisualizer
        driver={driver}
        allDrivers={sortedDrivers}
    />
)}
```

Adjust prop names to match what `PitRejoinVisualizer` actually accepts. Read its TypeScript interface before writing.

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Fix any prop type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/StrategyPanel.tsx
git commit -m "feat: wire PitRejoinVisualizer in StrategyPanel, conditional on pit window"
```

---

### Task 10: Pit history strip in StrategyPanel

**Files:**
- Modify: `frontend/src/components/StrategyPanel.tsx`

The `recentPits` store field was added in Task 3. Now display it.

- [ ] **Step 1: Add recentPits selector to StrategyPanel**

In `frontend/src/components/StrategyPanel.tsx`, add:

```typescript
const recentPits = useRaceStore(s => s.recentPits);
```

- [ ] **Step 2: Add pit history strip at the bottom of the panel**

```tsx
{/* Pit History Strip */}
{recentPits.length > 0 && (
    <div style={{ marginTop: '8px', borderTop: '1px solid var(--border-color)', paddingTop: '6px' }}>
        <div style={{ fontSize: '10px', fontWeight: 500, textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '4px', letterSpacing: '0.06em' }}>
            RECENT PITS
        </div>
        {recentPits.slice(0, 3).map((pit, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', padding: '2px 0', color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--text-primary)', minWidth: '28px' }}>#{pit.driver_number}</span>
                <span>L{pit.lap_number}</span>
                {pit.compound && (
                    <span style={{
                        width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0,
                        background: pit.compound === 'SOFT' ? 'var(--tyre-soft)'
                            : pit.compound === 'MEDIUM' ? 'var(--tyre-medium)'
                            : pit.compound === 'HARD' ? 'var(--tyre-hard)'
                            : pit.compound === 'INTERMEDIATE' ? 'var(--tyre-inter)'
                            : pit.compound === 'WET' ? 'var(--tyre-wet)'
                            : 'var(--text-muted)',
                    }} />
                )}
                {pit.compound && <span style={{ fontSize: '0.7rem', textTransform: 'uppercase' }}>{pit.compound.slice(0, 1)}</span>}
                {pit.pit_duration != null && (
                    <span style={{ color: 'var(--text-muted)', marginLeft: 'auto' }}>{pit.pit_duration.toFixed(1)}s</span>
                )}
            </div>
        ))}
    </div>
)}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/StrategyPanel.tsx
git commit -m "feat: pit history strip in StrategyPanel (driver, lap, compound, duration)"
```

---

### Task 11: Sector bars in TelemetryPanel

**Files:**
- Modify: `frontend/src/components/TelemetryPanel.tsx`

The standalone `TelemetryPanel.tsx` (used in Replay/Backtest) lacks sector data. Add it.

- [ ] **Step 1: Read TelemetryPanel's props and current output**

Read `frontend/src/components/TelemetryPanel.tsx` to understand: what props it receives (`driver`? sector data?), what it already renders. The `DriverState` type has `sector_1`, `sector_2`, `sector_3` fields — confirm they're available.

- [ ] **Step 2: Check DriverState for sector fields**

In `frontend/src/types/index.ts`, verify `DriverState` has `sector_1`, `sector_2`, `sector_3` (type `number | null`). If they exist, proceed. If not, add them.

- [ ] **Step 3: Add sector mini bar to TelemetryPanel**

Find a logical place in the `TelemetryPanel` render output (near timing data) and add:

```tsx
{/* Sector Times */}
{(driver.sector_1 != null || driver.sector_2 != null || driver.sector_3 != null) && (
    <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
        {(['sector_1', 'sector_2', 'sector_3'] as const).map((key, i) => {
            const val = driver[key];
            return (
                <div key={key} style={{ flex: 1, textAlign: 'center' }}>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '2px' }}>
                        S{i + 1}
                    </div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: val != null ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                        {val != null ? val.toFixed(3) : '—'}
                    </div>
                </div>
            );
        })}
    </div>
)}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/TelemetryPanel.tsx frontend/src/types/index.ts
git commit -m "feat: add S1/S2/S3 sector bar to standalone TelemetryPanel"
```

---

### Task 12: Verify gap_to_ahead toggle

**Files:**
- Modify: `frontend/src/pages/LiveDashboard.tsx` (if fix needed, else read-only verification)

- [ ] **Step 1: Locate the INT/GAP toggle**

In `frontend/src/pages/LiveDashboard.tsx`, find the GAP/INT toggle (around lines 259–264). Read the cell rendering logic.

- [ ] **Step 2: Verify correct field + null handling**

Confirm the GAP mode renders `driver.gap_to_ahead` and shows `"—"` when `driver.gap_to_ahead == null`. If it already does: no change needed. If not:

```tsx
// In the gap cell, GAP mode:
{gapMode === 'GAP'
    ? (driver.gap_to_ahead != null ? `+${driver.gap_to_ahead.toFixed(3)}` : '—')
    : (driver.gap_to_leader != null ? `+${driver.gap_to_leader.toFixed(3)}` : '—')
}
```

- [ ] **Step 3: Commit (only if changes were needed)**

```bash
git add frontend/src/pages/LiveDashboard.tsx
git commit -m "fix: gap_to_ahead toggle correctly shows — when null"
```

---

## Chunk 6: CSS Modules — App Shell + Pages

### How CSS Modules work in Vite/React

Name your file `Foo.module.css`. Import as `import styles from './Foo.module.css'`. Use `className={styles.myClass}` instead of `className="my-class"`. Vite scopes the classnames automatically. Global classnames from `index.css` still work — only the ones you're migrating get the module treatment.

**Migration pattern for each component:**
1. Create `Foo.module.css` — paste the relevant CSS classes from `index.css`
2. Import `styles` in `Foo.tsx`
3. Replace `className="foo"` with `className={styles.foo}` throughout the component
4. Delete the migrated classes from `index.css`
5. Run `npx tsc --noEmit` + `npm run dev` to verify

---

### Task 13: App.module.css

**Files:**
- Create: `frontend/src/App.module.css`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/index.css` (remove migrated classes)

- [ ] **Step 1: Create App.module.css**

Create `frontend/src/App.module.css` with the following classes extracted from `index.css`:

```css
/* App Shell */
.statusBar {
    height: var(--status-bar-height);
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    padding: 0 12px;
    gap: 12px;
    font-size: 0.78rem;
    font-family: var(--font-mono);
    white-space: nowrap;
    overflow: hidden;
    z-index: 100;
}

.tabBar {
    height: var(--tab-bar-height);
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    padding: 0 8px;
    gap: 2px;
}

.tabBtn {
    padding: 0 12px;
    height: 100%;
    background: none;
    border: none;
    color: var(--text-secondary);
    font-size: 0.78rem;
    font-family: var(--font-sans);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: color var(--transition-fast), border-color var(--transition-fast);
}

.tabBtn:hover {
    color: var(--text-primary);
}

.tabBtnActive {
    color: var(--text-primary);
    border-bottom-color: var(--color-accent);
}

.mainContent {
    flex: 1;
    overflow: hidden;
    min-height: 0;
}

.alertStrip {
    background: rgba(225, 6, 0, 0.08);
    border-bottom: 1px solid var(--border-color);
    padding: 2px 4px;
    flex-shrink: 0;
    z-index: 90;
}

.alertRow {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 3px 6px;
    font-size: 0.78rem;
}

.alertBadge {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: var(--radius-sm);
    background: var(--color-accent);
    color: #fff;
    flex-shrink: 0;
}

.alertMsg {
    flex: 1;
    color: var(--text-primary);
}

.alertDismiss {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 1rem;
    padding: 0 4px;
}

.sessionDrawer {
    position: fixed;
    top: 0;
    left: 0;
    width: 280px;
    height: 100vh;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-color);
    z-index: 200;
    display: flex;
    flex-direction: column;
    padding: 12px;
    gap: 12px;
    overflow-y: auto;
}

.sessionDrawerOverlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 199;
}
```

Note: Keep `.app-container` and `.dashboard-grid` in global `index.css` since they define the top-level grid used by all pages.

- [ ] **Step 2: Update App.tsx to use CSS Modules**

In `frontend/src/App.tsx`:

1. Add import: `import styles from './App.module.css';`
2. Replace class strings:
   - `className="status-bar"` → `className={styles.statusBar}`
   - `className="tab-bar"` → `className={styles.tabBar}`
   - `className={`tab-btn${...}`}` → `className={`${styles.tabBtn}${active ? ' ' + styles.tabBtnActive : ''}`}`
   - `className="main-content"` → `className={styles.mainContent}`
   - `className="alert-strip"` → `className={styles.alertStrip}`
   - `className="alert-row ..."` → `className={styles.alertRow}`
   - `className="alert-badge"` → `className={styles.alertBadge}`
   - `className="alert-msg"` → `className={styles.alertMsg}`
   - `className="alert-dismiss"` → `className={styles.alertDismiss}`
   - `className="session-drawer"` → `className={styles.sessionDrawer}`
   - `className="session-drawer-overlay"` → `className={styles.sessionDrawerOverlay}`

- [ ] **Step 3: Remove migrated classes from index.css**

Delete from `index.css`: `.status-bar`, `.tab-bar`, `.tab-btn`, `.main-content`, `.alert-banner`, `.alert-strip`, `.alert-row`, `.alert-badge`, `.alert-msg`, `.alert-dismiss`, `.session-drawer`, `.session-drawer-overlay` and their child selectors.

- [ ] **Step 4: Verify**

```bash
cd frontend && npx tsc --noEmit && npm run dev
```

Check the app shell renders correctly. No missing styles.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.module.css frontend/src/index.css
git commit -m "refactor: migrate App.tsx to CSS Modules"
```

---

### Task 14: LiveDashboard.module.css

**Files:**
- Create: `frontend/src/pages/LiveDashboard.module.css`
- Modify: `frontend/src/pages/LiveDashboard.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Create LiveDashboard.module.css**

Extract all `.col-leaderboard`, `.col-center`, `.col-strategy`, and any leaderboard-specific classes (`.lb-row`, `.lb-row-pit-now`, `.lb-row-threat`, `.lb-header`, etc.) from `index.css` into `LiveDashboard.module.css`. Use camelCase names.

- [ ] **Step 2: Update LiveDashboard.tsx**

Import `styles from './LiveDashboard.module.css'` and replace all `className="..."` with `className={styles.xxx}`.

- [ ] **Step 3: Remove migrated classes from index.css**

- [ ] **Step 4: Verify + Commit**

```bash
cd frontend && npx tsc --noEmit && npm run dev
git add frontend/src/pages/LiveDashboard.tsx frontend/src/pages/LiveDashboard.module.css frontend/src/index.css
git commit -m "refactor: migrate LiveDashboard to CSS Modules"
```

---

### Task 15: ReplayPage.module.css + BacktestPage.module.css

**Files:**
- Create: `frontend/src/pages/ReplayPage.module.css`
- Create: `frontend/src/pages/BacktestPage.module.css`
- Modify: `frontend/src/pages/ReplayPage.tsx`
- Modify: `frontend/src/pages/BacktestPage.tsx`

Follow the same migration pattern as Task 14. Extract only the classes used by these specific pages.

- [ ] **Step 1: Read each page, identify className strings, extract to module**
- [ ] **Step 2: Import and update classNames in each page**
- [ ] **Step 3: Remove from index.css**
- [ ] **Step 4: Verify + Commit**

```bash
git add frontend/src/pages/ReplayPage.tsx frontend/src/pages/ReplayPage.module.css \
        frontend/src/pages/BacktestPage.tsx frontend/src/pages/BacktestPage.module.css \
        frontend/src/index.css
git commit -m "refactor: migrate ReplayPage and BacktestPage to CSS Modules"
```

---

## Chunk 7: CSS Modules — Core Components

### Task 16: DriverTable.module.css

**Files:**
- Create: `frontend/src/components/DriverTable.module.css`
- Modify: `frontend/src/components/DriverTable.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Read DriverTable.tsx** — identify all `className` strings used
- [ ] **Step 2: Create DriverTable.module.css** — extract from index.css, camelCase
- [ ] **Step 3: Update DriverTable.tsx** — import styles, replace classNames
- [ ] **Step 4: Remove from index.css**
- [ ] **Step 5: Verify + Commit**

```bash
git add frontend/src/components/DriverTable.tsx frontend/src/components/DriverTable.module.css frontend/src/index.css
git commit -m "refactor: migrate DriverTable to CSS Modules"
```

---

### Task 17: StrategyPanel.module.css

**Files:**
- Create: `frontend/src/components/StrategyPanel.module.css`
- Modify: `frontend/src/components/StrategyPanel.tsx`
- Modify: `frontend/src/index.css`

Key classes to migrate: `.strategy-section-label` (update to `var(--text-secondary)` as per spec), `.strategy-panel`, all badge and recommendation classes.

- [ ] **Step 1: Read StrategyPanel.tsx** — identify all classNames
- [ ] **Step 2: Create StrategyPanel.module.css** — extract and apply the section header fix:

```css
.sectionLabel {
    font-size: 10px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary);    /* was --text-muted */
    margin-bottom: 4px;
}
```

- [ ] **Step 3: Update StrategyPanel.tsx** — import styles, replace classNames
- [ ] **Step 4: Remove from index.css**
- [ ] **Step 5: Verify + Commit**

```bash
git add frontend/src/components/StrategyPanel.tsx frontend/src/components/StrategyPanel.module.css frontend/src/index.css
git commit -m "refactor: migrate StrategyPanel to CSS Modules, fix section header color"
```

---

### Task 18: TrackMap.module.css

**Files:**
- Create: `frontend/src/components/TrackMap.module.css`
- Modify: `frontend/src/components/TrackMap.tsx`
- Modify: `frontend/src/index.css`

- [ ] Follow same pattern. TrackMap uses SVG — any CSS classes on the wrapper div get migrated; SVG inline styles stay inline.
- [ ] Verify + Commit:

```bash
git add frontend/src/components/TrackMap.tsx frontend/src/components/TrackMap.module.css frontend/src/index.css
git commit -m "refactor: migrate TrackMap to CSS Modules"
```

---

### Task 19: TelemetryPanel.module.css + TelemetryChart.module.css

**Files:**
- Create: `frontend/src/components/TelemetryPanel.module.css`
- Create: `frontend/src/components/TelemetryChart.module.css`
- Modify: both `.tsx` files
- Modify: `frontend/src/index.css`

- [ ] Follow same pattern for both components.
- [ ] Verify + Commit:

```bash
git add frontend/src/components/TelemetryPanel.tsx frontend/src/components/TelemetryPanel.module.css \
        frontend/src/components/TelemetryChart.tsx frontend/src/components/TelemetryChart.module.css \
        frontend/src/index.css
git commit -m "refactor: migrate TelemetryPanel and TelemetryChart to CSS Modules"
```

---

## Chunk 8: CSS Modules — Supporting Components

### Task 20: Migrate remaining active components

For each of the following, follow the same CSS Modules migration pattern (read → create module → update component → remove from index.css → verify → commit). Each component gets its own commit.

**Components to migrate (one commit each):**

- [ ] `ExplainabilityPanel.tsx` → `ExplainabilityPanel.module.css`
- [ ] `WeatherWidget.tsx` → `WeatherWidget.module.css`
- [ ] `RaceMessages.tsx` → `RaceMessages.module.css`
- [ ] `MetricCard.tsx` → `MetricCard.module.css`
- [ ] `SessionSelector.tsx` → `SessionSelector.module.css`
- [ ] `RaceProgressBar.tsx` → `RaceProgressBar.module.css`
- [ ] `PitRejoinVisualizer.tsx` → `PitRejoinVisualizer.module.css`
- [ ] `TyreLifeChart.tsx` → `TyreLifeChart.module.css`
- [ ] `CompetitorPredictions.tsx` → `CompetitorPredictions.module.css`
- [ ] `PositionProbabilityChart.tsx` → `PositionProbabilityChart.module.css`
- [ ] `StrategyComparison.tsx` → `StrategyComparison.module.css`
- [ ] `DRSZoneOverlay.tsx` → `DRSZoneOverlay.module.css`
- [ ] `BrakingZoneIndicator.tsx` → `BrakingZoneIndicator.module.css`

For `TopBar.tsx` and `Sidebar.tsx` — **check if actively imported** in App.tsx, LiveDashboard.tsx, ReplayPage.tsx, or BacktestPage.tsx before migrating. If orphaned, skip.

**Per-component commit message template:**
```bash
git commit -m "refactor: migrate <ComponentName> to CSS Modules"
```

---

### Task 21: Final cleanup — index.css audit

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Audit remaining contents of index.css**

After all component migrations, `index.css` should contain only:
1. `:root {}` — CSS variables
2. `*, *::before, *::after {}`, `html {}`, `body {}`, `#root {}` — resets
3. `.app-container`, `.dashboard-grid` — top-level grid layout
4. Font imports / `@font-face`
5. `.card-glow`, `.text-gradient` — legacy stubs
6. `.btn`, `.btn-primary`, `.btn-secondary` — global button base styles (if used globally across pages)

Delete any remaining orphaned class definitions.

- [ ] **Step 2: Run full test suite**

```bash
cd frontend && npm run test
```

Expected: All existing tests pass (DriverTable, StrategyPanel tests).

- [ ] **Step 3: TypeScript final check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: Zero errors.

- [ ] **Step 4: Final commit**

```bash
git add frontend/src/index.css
git commit -m "refactor: index.css final cleanup — only global vars, resets, and top-level grid remain"
```

---

## Pre-existing Bug Note

`App.tsx` line 244 renders `[1, 2, 5, 10, 20]` as speed options. `SimulationSpeed` type is `1 | 5 | 10 | 20 | 50`. Do **not** fix this as part of this plan — it is explicitly out of scope. When migrating `App.tsx`, preserve this behavior exactly as-is.

---

## Summary

| Chunk | Tasks | What it delivers |
|---|---|---|
| 1 | 1–3 | Palette updated, alert + recentPits in store |
| 2 | 4 | Backend recent_pits includes compound |
| 3 | 5 | Alert system refactored to store + useAlerts hook |
| 4 | 6–7 | Density, borders, PIT_NOW badge, cliff label, undercut icons |
| 5 | 8–12 | Pit window bar, PitRejoinVisualizer, pit history strip, sector bars |
| 6 | 13–15 | App shell + all pages → CSS Modules |
| 7 | 16–19 | Core components → CSS Modules |
| 8 | 20–21 | All remaining components → CSS Modules + final cleanup |
