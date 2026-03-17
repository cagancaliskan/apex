# User Guide

Complete guide to using the F1 Race Strategy Workbench.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Dashboard Overview](#dashboard-overview)
4. [Live Race Mode](#live-race-mode)
5. [Championship Simulator](#championship-simulator)
6. [Live Race View](#live-race-view)
7. [Pit Strategy](#pit-strategy)
8. [Strategy Explainability](#strategy-explainability)
9. [Tyre Degradation](#tyre-degradation)
10. [Race Replay](#race-replay)
11. [Understanding Metrics](#understanding-metrics)
12. [Keyboard Shortcuts](#keyboard-shortcuts)
13. [FAQ](#faq)

---

## Introduction

The **F1 Race Strategy Workbench** is a real-time analytics tool that helps you understand and predict pit stop strategies during Formula 1 races. It combines live timing data with machine learning models to provide actionable insights.

### What Can You Do?

- **Track Live Races** — Real-time positions, gaps, and lap times via OpenF1 API
- **Predict Championships** — Monte Carlo simulations for WDC and WCC standings
- **Analyze Tyres** — See degradation curves and cliff warnings
- **Predict Pit Stops** — Optimal pit windows for each driver
- **Compare Strategies** — Monte Carlo simulations for what-if scenarios
- **Understand Decisions** — Explainability engine shows why strategies are recommended
- **Replay Races** — Analyze any race from 2023+ with lap-by-lap simulation

---

## Getting Started

### Accessing the Application

1. Open your browser
2. Navigate to http://localhost:8000 (or your deployment URL)
3. The dashboard will load automatically

### First-Time Setup

1. **Select a Session**
   - Click "Sessions" in the top navigation
   - Choose a year (2023, 2024)
   - Select a race event
   - Click "Load Session"

2. **View the Dashboard**
   - The dashboard shows real-time data once a session is loaded
   - For historical races, click "Start Replay"

---

## Dashboard Overview

### Navigation

The application has four main tabs:

| Tab | Icon | Description |
|-----|------|-------------|
| **Live** | Activity | Real-time race view (simulation or live tracking) |
| **Replay** | RotateCcw | Historical race replay with FastF1 data |
| **Backtest** | FlaskConical | Strategy backtesting and what-if analysis |
| **Championship** | Trophy | Season championship Monte Carlo prediction |

### Main Layout

```
┌─────────────────────────────────────────────────────────┐
│  Navigation Bar                    [Sessions] [Settings]│
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────────────────────────┐│
│  │   Leaderboard │  │      Timing Tower               ││
│  │               │  │                                  ││
│  │  1. VER  0.0s │  │  LAP 35/57   🟢 GREEN FLAG     ││
│  │  2. HAM +2.5s │  │                                  ││
│  │  3. SAI +5.2s │  │  [Driver Details]               ││
│  │  ...          │  │                                  ││
│  └──────────────┘  └──────────────────────────────────┘│
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │           Strategy & Degradation Panel           │  │
│  │                                                  │  │
│  │  [Pit Window] [Deg Curve] [Monte Carlo]          │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Description |
|-----------|-------------|
| **Navigation** | Session selection, settings, help |
| **Leaderboard** | Live positions with gaps |
| **Timing Tower** | Lap times, sector times |
| **Strategy Panel** | Pit recommendations, degradation |
| **Status Bar** | Current lap, flags, weather |

---

## Live Race Mode

> New in v2.1

### What is Live Race Mode?

Live Race Mode connects directly to the OpenF1 API to track an ongoing F1 session in real-time. It polls for new data every 5 seconds and provides live strategy recommendations.

### Starting Live Tracking

1. Navigate to the **Live** tab
2. If a session is active, it will be detected automatically
3. Alternatively, use the WebSocket command: `{"type": "start_live"}`
4. The dashboard updates in real-time with positions, gaps, and strategy recommendations

### How It Works

- **Data Source**: OpenF1 public API (real-time positions, laps, car telemetry)
- **Update Rate**: Every 5 seconds
- **Strategy Engine**: Runs pit strategy calculations on each update cycle
- **Mutual Exclusion**: Starting live mode automatically stops any running simulation

### Stopping Live Mode

- Click "Stop" in the Live panel, or
- Send `{"type": "stop_live"}` via WebSocket

---

## Championship Simulator

> New in v2.1

### What is the Championship Simulator?

The Championship Simulator uses Monte Carlo methods to predict the final WDC (World Drivers' Championship) and WCC (World Constructors' Championship) standings. It simulates the remaining races hundreds of times to produce probability distributions.

### Using the Championship Simulator

1. Navigate to the **Championship** tab
2. Configure the simulation:
   - **Year**: Select the season (2018-2025)
   - **Starting Round**: Which round to simulate from (completed rounds use actual results)
   - **Simulations**: Number of Monte Carlo iterations (50/100/200/500)
   - **Include Sprints**: Toggle sprint race scoring
3. Click **Run Simulation**
4. Wait 20-60 seconds for results

### Reading the Results

**WDC Standings Table:**

| Column | Description |
|--------|-------------|
| # | Predicted final position |
| Driver | Driver name with team colour dot |
| Team | Constructor name |
| Pts | Actual points from completed races |
| Predicted | Mean total points +/- standard deviation |
| Range | 10th to 90th percentile range bar |
| P(Champ) | Probability of winning the championship |
| P(Top 3) | Probability of finishing in the top 3 |

**WCC Standings Table:**
Same structure but grouped by constructor, summing both drivers' points.

**Probability Chart:**
Bar chart showing championship win probability for the top 5-6 contenders, using team colours.

**Season Timeline:**
Horizontal progress bar showing completed rounds (solid) vs remaining rounds (striped pattern).

### How the Simulation Works

1. **Calendar**: Fetches the season schedule from FastF1
2. **Standings**: Loads actual results for completed rounds
3. **Grid Building**: Creates synthetic driver grids using pace priors from SeasonLearner
4. **Monte Carlo Loop**: For each simulation iteration:
   - Simulates each remaining race using GridSimulator (20-car physics simulation)
   - Applies random DNF events (7% probability per driver per race)
   - Awards fastest lap bonus (+1 point to a random top-10 finisher)
   - Converts finishing positions to points (standard F1 scoring)
5. **Aggregation**: Computes statistics across all iterations

---

## Live Race View

### Leaderboard

The leaderboard shows all drivers sorted by position:

| Column | Description |
|--------|-------------|
| **POS** | Current position |
| **#** | Car number |
| **Driver** | Three-letter code (VER, HAM, etc.) |
| **Gap** | Time gap to leader |
| **Int** | Interval to car ahead |
| **Tyre** | Current compound + age |
| **Stint** | Current stint number |

### Timing Details

Click any driver to see detailed timing:

- **Last Lap** — Most recent lap time
- **Best Lap** — Personal best this race
- **Sectors** — S1, S2, S3 times
- **Speed Trap** — Maximum speed
- **Pit Stops** — Pit history

### Race Status Indicators

| Indicator | Meaning |
|-----------|---------|
| 🟢 | Green flag (racing) |
| 🟡 | Yellow flag (caution) |
| 🔴 | Red flag (stopped) |
| 🚗 | Safety car deployed |
| 🔵 | Virtual safety car |

### Telemetry Analysis

The **Telemetry Panel** provides real-time car data visualization:

- **Speed/Throttle/Brake**: Live gauges showing driver inputs.
- **Gear**: Current gear indicator.
- **DRS**: DRS activation status (Green = Active).
- **History Trace**: Rolling graph of speed/thottle over the last minute.

---

## Pit Strategy

### Pit Rejoin Visualization

The **Ghost Car** visualization helps you understand where a driver will emerge after a pit stop:

- **Ghost Car**: Represents the predicted track position after completing a pit stop (approx. 20-25s loss).
- **Traffic Analysis**: Shows if the driver will rejoin in clean air (Green) or traffic (Red).
- **Battles**: Highlights cars that will immediately be fighting for position upon rejoin.

### Pit Window

The pit window shows the optimal timing for a pit stop:

```
┌─────────────────────────────────────────┐
│  VER - Pit Window                       │
├─────────────────────────────────────────┤
│                                         │
│  Min Lap: 38    Ideal: 42    Max: 48    │
│                                         │
│  ◄───────────●─────────────►            │
│       38    42              48          │
│                                         │
│  Recommendation: STAY OUT               │
│  Confidence: 85%                        │
│                                         │
│  "Tyres in good condition. Pit window  │
│   opens lap 38. Ideal stop lap 42."    │
│                                         │
└─────────────────────────────────────────┘
```

### Recommendation Types

| Type | Meaning | Action |
|------|---------|--------|
| **STAY OUT** | Continue current stint | No pit needed yet |
| **PIT NOW** | Pit this lap | Immediate stop recommended |
| **CONSIDER PIT** | Evaluate pitting | Good opportunity but not urgent |
| **EXTEND STINT** | Push current tyres | Can delay pit stop |

### Pit Strategy Factors

- **Tyre degradation** — How fast tyres are wearing
- **Cliff risk** — Risk of sudden performance drop
- **Track position** — Gap to cars behind
- **Undercut threat** — Can car behind undercut?
- **Safety car** — Free pit stop opportunity

---

## Strategy Explainability

> New in v2.1

### Understanding Strategy Recommendations

The Explainability Panel breaks down *why* a strategy is recommended, showing the contributing factors and their weights.

### Factor Ranking

Each recommendation shows the key factors that influenced the decision:

| Factor | Description |
|--------|-------------|
| **Tyre Condition** | Current degradation rate and remaining tyre life |
| **Track Position** | Clean air advantage vs traffic |
| **Undercut Threat** | Risk of being undercut by cars behind |
| **Safety Car Probability** | Likelihood of free pit stop opportunity |
| **Fuel Load** | Impact of fuel weight on pace |
| **Weather** | Changing conditions that may require tyre switch |

### Sensitivity Analysis

The "What If" section shows how the recommendation would change under different scenarios:
- **+5 laps on tyres**: Would the recommendation change if tyres are 5 laps older?
- **Safety car**: What if a safety car is deployed now?
- **Rain probability**: How does increasing rain probability affect the strategy?

---

## Tyre Degradation

### Degradation Curve

The degradation chart shows lap time evolution:

```
Lap Time (s)
  │
94│                           ●●●
  │                       ●●●
93│                   ●●●
  │               ●●●
92│          ●●●●
  │     ●●●●
91│●●●●
  └────────────────────────────────
       5   10   15   20   25   30
                Lap in Stint
```

### Key Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| **Deg Slope** | Time loss per lap (s) | < 0.05 |
| **Base Pace** | Clean-air pace | Lower = faster |
| **Cliff Risk** | Risk of sudden drop | < 40% |
| **Predicted +5** | Next 5 laps forecast | Stable trend |

### Cliff Risk Warning

When cliff risk exceeds 70%:
- ⚠️ Yellow warning (70-85%)
- 🔴 Red warning (85%+)

**Action:** Consider pitting before cliff hits.

---

## Race Replay

### Loading a Replay

1. Click **Sessions** → **Historical**
2. Select year and race
3. Click **Load**
4. Click **Start Replay**

### Playback Controls

| Control | Action |
|---------|--------|
| ▶️ Play | Start/resume playback |
| ⏸️ Pause | Pause playback |
| ⏹️ Stop | Stop and reset |
| ⏪ | Jump back 5 laps |
| ⏩ | Jump forward 5 laps |
| 1x / 2x / 5x | Playback speed |

### Replay Features

- **Lap-by-lap simulation** — See the race unfold as it happened
- **Strategy overlay** — Our predictions vs actual decisions
- **What-if analysis** — Modify pit stops and simulate outcomes

---

## Understanding Metrics

### Gap Formats

| Format | Meaning |
|--------|---------|
| `+2.5s` | 2.5 seconds behind leader |
| `+1 LAP` | One lap behind leader |
| `PIT` | Currently in pit lane |
| `OUT` | Out lap after pit |

### Tyre Compounds

| Compound | Color | Typical Life |
|----------|-------|--------------|
| **SOFT** | 🔴 Red | 15-20 laps |
| **MEDIUM** | 🟡 Yellow | 25-35 laps |
| **HARD** | ⚪ White | 35-45 laps |
| **INTER** | 🟢 Green | Variable |
| **WET** | 🔵 Blue | Variable |

### Sector Colors

| Color | Meaning |
|-------|---------|
| 🟣 Purple | Personal best + session best |
| 🟢 Green | Personal best |
| 🟡 Yellow | Slower than personal best |

---

## Keyboard Shortcuts

### Navigation

| Key | Action |
|-----|--------|
| `S` | Open sessions panel |
| `D` | Focus driver search |
| `Esc` | Close panel/modal |

### Replay Controls

| Key | Action |
|-----|--------|
| `Space` | Play/pause |
| `←` | Back 1 lap |
| `→` | Forward 1 lap |
| `1` | Speed 1x |
| `2` | Speed 2x |
| `5` | Speed 5x |

### Driver Selection

| Key | Action |
|-----|--------|
| `↑` | Previous driver |
| `↓` | Next driver |
| `Enter` | Select driver |

---

## FAQ

### Why is the data delayed?

Live data from OpenF1 typically has a 3-5 second delay. This is normal for free data sources.

### Why does my prediction differ from what happened?

My predictions are probabilistic. The actual outcome depends on factors we can't model (accidents, mistakes, weather changes).

### Can I use this for betting?

This tool is for educational and entertainment purposes only. We make no guarantees about prediction accuracy.

### How far back can I replay?

Historical data is available from the 2018 season onwards (via FastF1).

### How long does the championship simulation take?

Typically 20-60 seconds depending on the number of remaining races and simulation count. The computation runs in a background thread to keep the UI responsive.

### What does "P(Champ)" mean?

It's the probability that a driver wins the championship, calculated from Monte Carlo simulations. A value of 0.72 means the driver won the championship in 72% of all simulated seasons.

### Why is degradation "N/A" for some drivers?

We need at least 5 clean laps to calculate degradation. New stints or interrupted runs may show N/A temporarily.

### What's the difference between "Gap" and "Interval"?

- **Gap:** Time behind the race leader
- **Interval:** Time to the car directly ahead

### Why did strategy change suddenly?

Strategies update in real-time based on:
- New lap time data
- Position changes
- Safety car periods
- Weather changes

---

## Getting Help

- 📖 [Full Documentation](README.md)
- [Report Issues](https://github.com/cagancaliskan/apex/issues)

---

## Next Steps

- [Quick Start](QUICKSTART.md) — Running the application
- [API Reference](API.md) — Developer integration
- [Troubleshooting](TROUBLESHOOTING.md) — Common issues
