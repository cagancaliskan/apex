"""
Centralized constants for the Race Strategy Workbench.

Replaces hardcoded magic numbers scattered across the codebase.
All values here represent sensible defaults that can be overridden
by track-specific configuration or runtime calibration.
"""

# =============================================================================
# Pace & Timing
# =============================================================================

DEFAULT_BASE_PACE_SECONDS: float = 90.0
"""Fallback base lap time when no calibration data is available."""

FRAME_INTERVAL_SECONDS: float = 0.02
"""Animation frame interval (50 FPS)."""

# =============================================================================
# Pit Strategy
# =============================================================================

DEFAULT_PIT_LOSS_SECONDS: float = 22.0
"""Default time lost during a pit stop (pit lane transit + stationary)."""

DEFAULT_TOTAL_LAPS: int = 57
"""Default race length when actual data is unavailable."""

PIT_LANE_DELTA_FRACTION: float = 0.6
"""Fraction of total pit loss attributable to pit lane transit (~60%)."""

STATIONARY_FRACTION: float = 0.4
"""Fraction of total pit loss attributable to stationary time (~40%)."""

# =============================================================================
# Tyre Cliff Ages
# =============================================================================

CLIFF_AGES: dict[str, int] = {
    "SOFT": 12,
    "MEDIUM": 22,
    "HARD": 30,
    "INTERMEDIATE": 18,
    "WET": 18,
}
"""Compound cliff ages in tyre laps — single source of truth."""

# =============================================================================
# Pit Window
# =============================================================================

CLIFF_WINDOW_MARGIN: int = 5
"""Laps before/after cliff lap to bracket the pit window."""

HIGH_CLIFF_RISK_THRESHOLD: float = 0.7
"""Cliff risk score above which early pit is recommended."""

HIGH_CLIFF_EARLY_PIT_OFFSET: int = 5
"""Laps before cliff to target when cliff risk is high."""

MODERATE_CLIFF_RISK_THRESHOLD: float = 0.4
"""Cliff risk score above which a moderate early pit is recommended."""

MODERATE_CLIFF_EARLY_PIT_OFFSET: int = 2
"""Laps before cliff to target when cliff risk is moderate."""

CONFIDENCE_CLIFF_RISK_FACTOR: float = 0.5
"""Factor limiting confidence reduction from cliff risk (cap at 0.5 loss)."""

UNDERCUT_GAP_BUFFER: float = 3.0
"""Seconds: gap must be within pit_loss + this for undercut to be viable."""

UNDERCUT_MIN_GAP: float = 1.0
"""Minimum gap (s) for undercut consideration (closer = normal overtake viable)."""

FRESH_TYRE_BASE_ADVANTAGE: float = 1.5
"""Base pace advantage (s/lap) expected on fresh tyres vs worn."""

DEG_ADVANTAGE_MULTIPLIER: float = 3.0
"""Multiplier for degradation difference in fresh tyre advantage calculation."""

OVERCUT_DEG_THRESHOLD: float = 0.02
"""Minimum degradation advantage (s/lap) for overcut to be viable."""

OVERCUT_DEG_NORMALIZER: float = 0.05
"""Degradation normalizer for overcut confidence calculation."""

PIT_WINDOW_CONFIDENCE_WEIGHT: float = 0.6
"""Weight of confidence score in pit window ranking."""

PIT_WINDOW_TIMING_WEIGHT: float = 0.4
"""Weight of timing score in pit window ranking."""

CRITICAL_CLIFF_THRESHOLD: float = 0.85
"""Cliff risk above which immediate pit is forced (should_pit_now)."""

# =============================================================================
# Decision Engine
# =============================================================================

UNDERCUT_DEG_DELTA: float = 0.02
"""Degradation delta (s/lap) threshold to flag undercut/overcut opportunity."""

QUICK_REC_PIT_NOW_CLIFF_THRESHOLD: float = 0.8
"""Cliff risk threshold for 'PIT NOW' in quick recommendation."""

QUICK_REC_STAY_OUT_REMAINING_LAPS: int = 8
"""Remaining laps below which 'STAY OUT' is recommended (too late to pit)."""

QUICK_REC_CONSIDER_PIT_THRESHOLD: float = 0.5
"""Cliff risk threshold for 'CONSIDER PIT' in quick recommendation."""

DECISION_PIT_NOW_CONFIDENCE: float = 0.7
"""Confidence threshold above which CONSIDER_PIT is upgraded to PIT_NOW."""

EXTEND_STINT_REMAINING_LAPS: int = 10
"""Remaining laps threshold below which EXTEND_STINT may be recommended."""

EXTEND_STINT_TYRE_AGE: int = 15
"""Tyre age below which EXTEND_STINT is preferred over pitting."""

CLIFF_RISK_CONFIDENCE_FACTOR: float = 0.5
"""Multiplier applied to confidence via cliff risk in STAY_OUT cases."""

SC_PIT_CONFIDENCE: float = 0.95
"""Confidence for safety car pit opportunity recommendation."""

TRAFFIC_CONFIDENCE_THRESHOLD: float = 0.5
"""Traffic severity above which pit confidence is penalised."""

TRAFFIC_SEVERITY_MULTIPLIER: float = 0.3
"""Multiplier for confidence reduction from pit traffic."""

COMPOUND_SELECTION_LONG_LAP_THRESHOLD: int = 30
"""Remaining laps above which hard compound is preferred as next stint."""

COMPOUND_SELECTION_MED_LAP_THRESHOLD: int = 15
"""Remaining laps above which medium compound is preferred as next stint."""

# =============================================================================
# Multi-Stop Optimizer
# =============================================================================

MIN_STINT_LAPS: int = 8
"""Minimum viable stint length in laps (FIA practical minimum ~7-8 laps)."""

ONE_STOP_PIT_FRACTIONS: list[float] = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65]
"""Race fraction breakpoints at which to evaluate 1-stop pit timing."""

TWO_STOP_PIT_FRACTIONS: list[tuple[float, float]] = [
    (0.30, 0.65),
    (0.33, 0.67),
    (0.40, 0.70),
]
"""Race fraction pairs (pit1, pit2) for 2-stop strategy evaluation."""

LONG_RACE_THREE_STOP_THRESHOLD: int = 50
"""Total laps above which 3-stop strategies are generated."""

CONFIDENCE_MIN: float = 0.4
"""Minimum confidence returned by strategy comparison."""

CONFIDENCE_MAX: float = 0.95
"""Maximum confidence returned by strategy comparison."""

CONFIDENCE_GAP_DIVISOR: float = 10.0
"""Time gap (s) divisor in confidence calculation (10s gap → max confidence)."""

# =============================================================================
# Grid Simulator
# =============================================================================

GRID_SIM_DEFAULT_CLIFF_LAP: int = 25
"""Default tyre cliff lap used when no compound data is available in grid sim."""

GRID_SIM_GAP_MIN: float = 0.5
"""Minimum random gap-to-ahead (s) sampled in grid simulation."""

GRID_SIM_GAP_MAX: float = 5.0
"""Maximum random gap-to-ahead (s) sampled in grid simulation."""

GRID_SIM_NORMAL_PIT_LOSS: float = 20.0
"""Pit loss used in grid simulator under normal conditions."""

GRID_SIM_SC_PIT_LOSS: float = 12.0
"""Pit loss used in grid simulator during safety car (cheaper stop)."""

DEFAULT_SC_BASE_PROBABILITY: float = 0.2
"""Default safety car probability when no circuit-specific data is available."""

# =============================================================================
# Degradation / Calibration
# =============================================================================

TRACK_PRIORS_MIN_SAMPLES: int = 5
"""Minimum pit-stop samples required to trust track-learned pit loss."""

TRACK_PRIORS_CONFIDENCE_THRESHOLD: float = 0.3
"""Minimum prior confidence (0-1) to use track-learned warm-start params."""

TRACK_PRIORS_CONFIDENCE_DENOMINATOR: float = 10.0
"""Sample count that yields confidence = 1.0 in track prior normalization."""

# =============================================================================
# Degradation Models
# =============================================================================

DEFAULT_FORGETTING_FACTOR: float = 0.95
"""RLS model forgetting factor for tyre degradation tracking."""

RLS_INITIAL_COVARIANCE: float = 1000.0
"""Initial covariance for Recursive Least Squares model."""

# =============================================================================
# Weather
# =============================================================================

WEATHER_VERY_WET_MM: float = 5.0
"""Precipitation (mm) threshold to classify conditions as VERY_WET."""

WEATHER_WET_MM: float = 1.0
"""Precipitation (mm) threshold to classify conditions as WET."""

WEATHER_RAIN_PROBABLE_PCT: int = 60
"""Rain probability (%) above which rain is considered likely soon."""

WEATHER_PACE_DELTA_PIT_THRESHOLD: float = 3.0
"""Pace delta (s/lap) on wrong compound that triggers immediate weather pit."""

WEATHER_CONDITION_CHANGE_LAPS: int = 3
"""Laps-to-change threshold below which a forecast pit is triggered."""

WEATHER_RAIN_PREP_LAPS: int = 5
"""Laps until rain above which slick-to-intermediate pit is prepared."""

WEATHER_DRYING_PIT_LAPS: int = 3
"""Laps until dry above which intermediate-to-dry opportunity is flagged."""

WEATHER_SC_PROBABILITY_CAP: float = 0.9
"""Maximum adjusted safety car probability (90% cap)."""

WEATHER_SC_MULTIPLIERS: dict[str, float] = {
    "DRY": 1.0,
    "DAMP": 1.5,
    "WET": 2.0,
    "VERY_WET": 3.0,
}
"""Safety car probability multipliers per weather condition."""

# =============================================================================
# Traffic / Dirty Air
# =============================================================================

DIRTY_AIR_THRESHOLD_SECONDS: float = 3.0
"""Gap (s) below which dirty air begins affecting pace."""

DIRTY_AIR_MAX_PENALTY_SECONDS: float = 0.5
"""Maximum dirty air time penalty per lap (at very close proximity)."""

DIRTY_AIR_EFFECT_EXPONENT: int = 2
"""Exponent for non-linear dirty air proximity effect (quadratic = 2)."""

PIT_TRAFFIC_WINDOW_SECONDS: float = 2.0
"""Gap window (s) around predicted rejoin time for traffic counting."""

PIT_TRAFFIC_MAX_CAR_THRESHOLD: int = 4
"""Number of cars within traffic window that corresponds to maximum severity."""

# =============================================================================
# Fuel Model
# =============================================================================

STARTING_FUEL_KG: float = 110.0
"""Standard starting fuel load per FIA regulations (kg)."""

FUEL_BURN_RATE_KG_PER_LAP: float = 1.7
"""Average fuel burn rate (kg/lap)."""

FUEL_TIME_COST_PER_KG: float = 0.035
"""Lap time cost per kg of fuel (s/kg)."""

# =============================================================================
# Tyre Physics
# =============================================================================

WARMUP_RAMP_FACTOR: float = 0.5
"""Linear ramp factor for tyre warmup penalty per lap below warmup_laps."""

TYRE_CLIFF_SEVERITY_FACTOR: float = 0.1
"""Pre-factor in exponential cliff penalty: penalty = factor * (exp(severity*laps) - 1)."""

# =============================================================================
# Track Model
# =============================================================================

GRID_EVOLUTION_MULTIPLIER: float = 0.001
"""Track improvement (s) per total grid lap (rubber deposition proxy)."""

RACE_LEADER_EVOLUTION_FACTOR: float = 0.03
"""Track improvement (s) per race leader lap in simplified model."""

# =============================================================================
# Sensitivity Analysis
# =============================================================================

SENSITIVITY_DEG_MULTIPLIER: float = 5.0
"""Multiplier to convert deg_slope into a 0-1 sensitivity score."""

SENSITIVITY_MIN_FACTOR_SCORE: float = 0.1
"""Minimum score for a sensitivity factor to be included in output."""

SENSITIVITY_TYRE_AGE_NORMALIZER: float = 40.0
"""Tyre age (laps) that yields sensitivity score = 1.0."""

SENSITIVITY_SC_FACTOR_SCORE: float = 0.9
"""Fixed sensitivity score when safety car is active."""

SENSITIVITY_POSITION_THRESHOLD: int = 5
"""Position at or inside which track position becomes a negative factor."""

SENSITIVITY_MAX_TOP_FACTORS: int = 3
"""Maximum number of top sensitivity factors to return."""

# =============================================================================
# Monte Carlo
# =============================================================================

MC_START_INCIDENT_LAP_HIGH: int = 3
"""Lap number below which the high start-incident multiplier applies."""

MC_START_INCIDENT_LAP_MED: int = 5
"""Lap number below which the medium start-incident multiplier applies."""

MC_START_MULTIPLIER_HIGH: float = 3.0
"""SC probability multiplier for the first MC_START_INCIDENT_LAP_HIGH laps."""

MC_START_MULTIPLIER_MED: float = 1.5
"""SC probability multiplier for laps up to MC_START_INCIDENT_LAP_MED."""

MC_WET_MULTIPLIER: float = 2.5
"""SC probability multiplier in wet conditions."""

MC_SC_PER_LAP_CAP: float = 0.15
"""Maximum per-lap safety car probability (15% cap)."""

MC_DEFAULT_CIRCUIT_SC_RATE: float = 0.25
"""Fallback safety car rate when circuit is not in historical data."""

# =============================================================================
# API & Caching
# =============================================================================

DEFAULT_CACHE_TTL_SECONDS: int = 3600
"""Default cache time-to-live for API responses."""

DEFAULT_RATE_LIMIT_REQUESTS: int = 100
"""Default rate limit: max requests per window."""

# =============================================================================
# Physics
# =============================================================================

GAP_INTERPOLATION_FACTOR: float = 1.0
"""Seconds per position gap when time data is unavailable."""

LOW_CONFIDENCE_PHYSICS_ONLY: float = 0.3
"""Model confidence when using physics-only predictions (no live data)."""

MEDIUM_CONFIDENCE_DEFAULT: float = 0.5
"""Default model confidence for initial predictions."""
