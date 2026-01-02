# User Guide

Complete guide to using the F1 Race Strategy Workbench.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Dashboard Overview](#dashboard-overview)
4. [Live Race View](#live-race-view)
5. [Pit Strategy](#pit-strategy)
6. [Tyre Degradation](#tyre-degradation)
7. [Race Replay](#race-replay)
8. [Understanding Metrics](#understanding-metrics)
9. [Keyboard Shortcuts](#keyboard-shortcuts)
10. [FAQ](#faq)

---

## Introduction

The **F1 Race Strategy Workbench** is a real-time analytics tool that helps you understand and predict pit stop strategies during Formula 1 races. It combines live timing data with machine learning models to provide actionable insights.

### What Can You Do?

- 📊 **Track Live Races** — Real-time positions, gaps, and lap times
- 🛞 **Analyze Tyres** — See degradation curves and cliff warnings
- 🔧 **Predict Pit Stops** — Optimal pit windows for each driver
- 🎯 **Compare Strategies** — Monte Carlo simulations for what-if scenarios
- 📼 **Replay Races** — Analyze any race from 2023+

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

---

## Pit Strategy

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

Historical data is available from the 2023 season onwards.

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
- 🐛 [Report Issues](https://github.com/your-org/rsw/issues)
- 💬 [Community Discord](https://discord.gg/rsw)

---

## Next Steps

- [Quick Start](QUICKSTART.md) — Running the application
- [API Reference](API.md) — Developer integration
- [Troubleshooting](TROUBLESHOOTING.md) — Common issues

---
**Next:** [[Architecture]]
