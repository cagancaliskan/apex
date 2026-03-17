# Architecture Diagrams

Visual architecture diagrams for the F1 Race Strategy Workbench v2.1.

> These diagrams use [Mermaid](https://mermaid.js.org/) syntax and render natively on GitHub.

---

## System Context Diagram

High-level view showing external systems and users.

```mermaid
C4Context
    title F1 Race Strategy Workbench - System Context

    Person(user, "Race Strategist", "Analyzes races and pit strategies")

    System(rsw, "Race Strategy Workbench", "Real-time F1 analytics, strategy optimization, and championship prediction")

    System_Ext(openf1, "OpenF1 API", "Real-time F1 timing data")
    System_Ext(fastf1, "FastF1", "Historical telemetry and session data")
    System_Ext(openmeteo, "OpenMeteo API", "Weather data and forecasts")

    Rel(user, rsw, "Uses", "HTTPS / WebSocket")
    Rel(rsw, openf1, "Fetches live data", "HTTPS polling 5s")
    Rel(rsw, fastf1, "Loads historical data", "Python library")
    Rel(rsw, openmeteo, "Fetches weather", "HTTPS")
```

---

## Component Diagram

Backend service architecture showing internal components.

```mermaid
graph TB
    subgraph "External Data Sources"
        OF[OpenF1 API]
        FF[FastF1 Library]
        OM[OpenMeteo API]
    end

    subgraph "Ingest Layer"
        OFC[OpenF1Client]
        FFS[FastF1Service]
        WC[WeatherClient]
    end

    subgraph "State Management"
        RED[Reducers]
        RSS[RaceStateStore]
        SCH[Schemas - DriverState / RaceState]
    end

    subgraph "Physics & ML Models"
        TM[TyreModel]
        FM[FuelModel]
        WM[WeatherModel]
        TRM[TrackModel]
        RLS[RLS Estimator]
        SL[SeasonLearner]
    end

    subgraph "Strategy Engine"
        MC[Monte Carlo]
        GS[GridSimulator]
        CAI[CompetitorAI]
        PW[PitWindow]
        DEC[Decision Engine]
        EXP[Explainability]
        SIT[SituationalStrategy]
    end

    subgraph "Services"
        SIM[SimulationService]
        LRS[LiveRaceService]
        CHS[ChampionshipService]
        STS[StrategyService]
    end

    subgraph "API Layer"
        REST[REST Endpoints]
        WS[WebSocket /ws]
        WSM[ConnectionManager]
    end

    subgraph "Frontend"
        LD[LiveDashboard]
        RP[ReplayPage]
        CP[ChampionshipPage]
        BP[BacktestPage]
    end

    OF --> OFC
    FF --> FFS
    OM --> WC

    OFC --> RED
    FFS --> RED
    WC --> RED
    RED --> RSS

    RSS --> SIM
    RSS --> LRS
    RSS --> STS

    TM --> GS
    FM --> GS
    WM --> GS
    TRM --> GS
    RLS --> STS
    SL --> CHS

    GS --> MC
    GS --> CHS
    CAI --> GS
    SIT --> CHS
    PW --> DEC
    MC --> DEC
    DEC --> EXP

    SIM --> WS
    LRS --> WS
    STS --> REST
    CHS --> REST
    EXP --> REST

    WS --> WSM
    WSM --> LD
    WSM --> RP
    REST --> CP
    REST --> BP
```

---

## Live Race Mode — Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User (Frontend)
    participant WS as WebSocket /ws
    participant LRS as LiveRaceService
    participant OF as OpenF1 API
    participant SS as StrategyService
    participant RSS as RaceStateStore

    U->>WS: {type: "start_live"}
    WS->>LRS: start(session_key)
    LRS-->>WS: {type: "live_started"}

    loop Every 5 seconds
        LRS->>OF: GET /positions, /laps, /car_data
        OF-->>LRS: JSON responses
        LRS->>RSS: apply_reducers(data)
        LRS->>SS: evaluate_strategy(drivers)
        SS-->>LRS: recommendations
        LRS->>WS: broadcast {type: "state_update", data: RaceState}
        WS-->>U: state_update (all connected clients)
    end

    U->>WS: {type: "stop_live"}
    WS->>LRS: stop()
    LRS-->>WS: {type: "live_stopped"}
```

---

## Championship Simulation — Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User (ChampionshipPage)
    participant API as REST API
    participant CHS as ChampionshipService
    participant FF as FastF1
    participant SL as SeasonLearner
    participant GS as GridSimulator

    U->>API: POST /api/championship/simulate
    Note over API: {year: 2023, start_from_round: 10, n_simulations: 200}

    API->>CHS: simulate(year, round, n_sims)
    CHS->>FF: get_event_schedule(year)
    FF-->>CHS: calendar (22 races)
    CHS->>FF: session.results (rounds 1-9)
    FF-->>CHS: completed standings
    CHS->>SL: get_driver_priors(year)
    SL-->>CHS: pace/degradation estimates

    Note over CHS: asyncio.to_thread() — CPU-heavy loop

    loop N=200 simulations
        loop Each remaining race (rounds 10-22)
            CHS->>CHS: Build ChampionshipContext per driver
            CHS->>CHS: calculate_risk_modifier()
            CHS->>GS: run_simulation(driver_grid, laps, sc_prob)
            GS-->>CHS: {driver: position}
            CHS->>CHS: apply_dnf(7% probability)
            CHS->>CHS: award_fastest_lap(+1 point)
            CHS->>CHS: position_to_points()
        end
    end

    CHS->>CHS: aggregate(mean, std, p10, p90, prob_champion)
    CHS-->>API: ChampionshipResult
    API-->>U: JSON (WDC + WCC standings)
```

---

## Race Simulation (Replay) — Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User (ReplayPage)
    participant WS as WebSocket /ws
    participant SIM as SimulationService
    participant FF as FastF1
    participant SS as StrategyService
    participant RSS as RaceStateStore

    U->>WS: {type: "start_session", year: 2023, round_num: 22}
    WS->>SIM: start(2023, 22)

    SIM->>FF: load_session(2023, 22, "R")
    FF-->>SIM: session data (laps, telemetry)

    WS-->>U: {type: "session_started"}

    loop Each lap (speed-adjusted)
        SIM->>RSS: apply_reducers(lap_data)
        SIM->>SS: evaluate_strategy(drivers)
        SS-->>SIM: recommendations
        SIM->>WS: broadcast {type: "state_update"}
        WS-->>U: state_update
    end

    U->>WS: {type: "set_speed", speed: 10}
    WS-->>U: {type: "speed_set", speed: 10}

    U->>WS: {type: "stop_session"}
    WS->>SIM: stop()
    WS-->>U: {type: "session_stopped"}
```

---

## Frontend Component Tree

```mermaid
graph TD
    App[App.tsx]

    App --> Nav[Tab Navigation]
    Nav --> T1[Live Tab]
    Nav --> T2[Replay Tab]
    Nav --> T3[Backtest Tab]
    Nav --> T4[Championship Tab]

    T1 --> LD[LiveDashboard]
    T2 --> RP[ReplayPage]
    T3 --> BP[BacktestPage]
    T4 --> CP[ChampionshipPage]

    LD --> DT[DriverTable]
    LD --> TM[TrackMap]
    LD --> SP[StrategyPanel]
    LD --> TP[TelemetryPanel]
    LD --> EP[ExplainabilityPanel]
    LD --> WW[WeatherWidget]
    LD --> RPB[RaceProgressBar]
    LD --> RM[RaceMessages]

    SP --> PRV[PitRejoinVisualizer]
    SP --> TLC[TyreLifeChart]
    SP --> SC[StrategyComparison]
    SP --> PPChart[PositionProbabilityChart]

    TP --> TC[TelemetryChart]
    TP --> MC[MetricCard]

    TM --> BZ[BrakingZoneIndicator]
    TM --> DRS[DRSZoneOverlay]

    CP --> WDC[WDC Standings Table]
    CP --> WCC[WCC Standings Table]
    CP --> PBC[Probability Bar Charts]
    CP --> STL[Season Timeline]
```

---

## Data Model — Entity Relationship

```mermaid
erDiagram
    RaceState ||--o{ DriverState : contains
    RaceState ||--o| WeatherData : has
    RaceState ||--o| TrackConfig : has
    RaceState ||--o{ RaceMessage : has
    RaceState ||--o{ PitStop : tracks

    DriverState {
        int driver_number PK
        string name_acronym
        string team_name
        int current_lap
        float last_lap_time
        float gap_to_leader
        string compound
        int tyre_age
        float deg_slope
        float cliff_risk
        int pit_window_min
        int pit_window_max
        string pit_recommendation
        float fuel_remaining_kg
        boolean in_pit
        boolean retired
    }

    WeatherData {
        float track_temp
        float air_temp
        float humidity
        float wind_speed
        float rainfall
        boolean is_raining
    }

    TrackConfig {
        json center_line
        json inner_edge
        json outer_edge
        json bounds
        json drs_zones
    }

    ChampionshipResult ||--o{ DriverStanding : wdc
    ChampionshipResult ||--o{ ConstructorStanding : wcc
    ChampionshipResult ||--o{ RaceCalendarEntry : calendar

    DriverStanding {
        int driver_number PK
        string name
        string team
        float current_points
        float total_points_mean
        float prob_champion
    }

    ConstructorStanding {
        string team PK
        float current_points
        float total_points_mean
        float prob_champion
    }
```

---

## Infrastructure — Docker Compose Stack

```mermaid
graph LR
    subgraph "Docker Compose"
        BE[Backend<br/>FastAPI :8000]
        FE[Frontend<br/>React :5173]
        DB[(PostgreSQL<br/>:5432)]
        RD[(Redis<br/>:6379)]
        PM[Prometheus<br/>:9090]
        GF[Grafana<br/>:3000]
    end

    User((User)) --> FE
    FE -->|REST / WS| BE
    BE --> DB
    BE --> RD
    PM -->|scrape| BE
    GF -->|query| PM

    OF[OpenF1 API] -->|HTTPS| BE
    OM[OpenMeteo API] -->|HTTPS| BE
```

---

## CI/CD Pipeline

```mermaid
graph LR
    subgraph "Triggers"
        PUSH[Push to main/develop]
        PR[Pull Request to main]
    end

    subgraph "Backend Tests"
        BT1[Setup Python 3.11]
        BT2[Install Dependencies]
        BT3[MyPy Type Checking]
        BT4[Ruff Linting]
        BT5[Bandit Security Scan]
        BT6[Pytest + Coverage]
    end

    subgraph "Frontend Tests"
        FT1[Setup Node 20]
        FT2[npm ci]
        FT3[ESLint]
        FT4[npm run build]
    end

    subgraph "Docker"
        D1[Build Backend Image]
        D2[Build Frontend Image]
    end

    subgraph "Security"
        S1[Trivy Vulnerability Scan]
    end

    PUSH --> BT1 --> BT2 --> BT3 --> BT4 --> BT5 --> BT6
    PUSH --> FT1 --> FT2 --> FT3 --> FT4
    PR --> BT1
    PR --> FT1

    BT6 --> D1
    FT4 --> D2

    PUSH --> S1
```
