/**
 * Centralized constants for the F1 Race Strategy Dashboard.
 *
 * Single source of truth for all magic numbers, strings, and configuration
 * values used across frontend components and pages.
 */

// =============================================================================
// API Endpoints
// =============================================================================

export const API_SESSIONS = '/api/sessions';
export const API_BACKTEST_RUN = '/api/backtest/run';
export const API_LIVE_SESSIONS = '/api/live/sessions';
export const API_REPLAY_SESSIONS = '/api/replay/sessions';
export const API_CHAMPIONSHIP_CALENDAR = (year: number) =>
    `/api/championship/calendar/${year}`;
export const API_CHAMPIONSHIP_SIMULATE = '/api/championship/simulate';
export const WS_PATH = '/ws';

// =============================================================================
// Tyre Colors — single source of truth
// (removes duplication across utils/index.ts, LiveDashboard, StrategyPanel)
// =============================================================================

export const TYRE_COLORS: Record<string, string> = {
    SOFT: '#ff2222',
    MEDIUM: '#ffcc00',
    HARD: '#ffffff',
    INTERMEDIATE: '#44dd44',
    WET: '#4488ff',
};

export const TYRE_TEXT_COLORS: Record<string, string> = {
    SOFT: '#ffffff',
    MEDIUM: '#000000',
    HARD: '#000000',
    INTERMEDIATE: '#000000',
    WET: '#ffffff',
};

// =============================================================================
// DRS Status Codes
// (removes duplication between TelemetryPanel and DriverTable)
// =============================================================================

/** Status codes that indicate DRS is actively deployed. */
export const DRS_ACTIVE_CODES = [10, 12, 14];

/** Status code that indicates DRS is available but not yet deployed. */
export const DRS_AVAILABLE_CODE = 8;

// =============================================================================
// Timing & Connection
// =============================================================================

/** Delay (ms) before attempting WebSocket reconnection. */
export const WS_RECONNECT_DELAY_MS = 3000;

/** Duration (ms) before an alert is automatically dismissed. */
export const ALERT_AUTO_DISMISS_MS = 10000;

/** Window (ms) within which an alert is considered "new" for deduplication. */
export const ALERT_NEWNESS_THRESHOLD_MS = 100;

/** Window (ms) for alert deduplication in the store. */
export const ALERT_DEDUP_WINDOW_MS = 30000;

/** Gap (s) above which live connection quality is classified as "poor". */
export const LIVE_CONNECTION_POOR_THRESHOLD_S = 15;

/** Gap (s) above which live connection quality is classified as "degraded". */
export const LIVE_CONNECTION_DEGRADED_THRESHOLD_S = 8;

/** Session tick interval in seconds. */
export const SESSION_TICK_SECONDS = 3.0;

// =============================================================================
// Simulation & Replay
// =============================================================================

/** Available simulation speed multipliers. */
export const SIMULATION_SPEEDS = [1, 2, 5, 10, 20];

/** Available replay speed multipliers. */
export const REPLAY_SPEEDS = [0.05, 0.1, 0.25, 0.5, 1, 2, 5];

/** Simulation count options offered in the Championship page. */
export const CHAMPIONSHIP_SIMULATION_COUNTS = [50, 100, 200, 500];

// =============================================================================
// Strategy Thresholds
// (mirrors backend values for UI colour-coding logic)
// =============================================================================

/** Degradation slope (s/lap) above which HIGH degradation warning is shown. */
export const DEG_HIGH_THRESHOLD = 0.08;

/** Degradation slope (s/lap) above which MEDIUM degradation warning is shown. */
export const DEG_MED_THRESHOLD = 0.05;

/** Ordered deg slope thresholds for colour mapping: [green→amber, amber→red]. */
export const DEG_COLOR_THRESHOLDS = [0.05, 0.08, 0.10];

/** Cliff risk above which CRITICAL (red) colour is shown. */
export const CLIFF_RISK_CRITICAL = 0.8;

/** Cliff risk above which WARNING (amber) colour is shown. */
export const CLIFF_RISK_WARNING = 0.4;

/** Ordered cliff risk thresholds for colour mapping: [green→amber, amber→red]. */
export const CLIFF_RISK_COLOR_THRESHOLDS = [0.5, 0.8];

/** Lap lookahead offset (negative = before window opens) for pit window row highlight. */
export const PIT_WINDOW_LAP_LOOKAHEAD = -2;

/** Lap gap used to calculate the end of the pit window lookahead range. */
export const PIT_WINDOW_LAP_GAP = 5;

/** Overtake probability (%) above which the "HIGH" label is shown. */
export const OVERTAKE_HIGH_PROBABILITY_PCT = 60;

// =============================================================================
// Weather Thresholds
// =============================================================================

/** Precipitation (mm) above which "heavy rain" icon/label is used. */
export const WEATHER_HEAVY_RAIN_MM = 2;

/** Humidity (%) above which "high humidity" condition is flagged. */
export const WEATHER_HIGH_HUMIDITY_PCT = 80;

/** Humidity (%) above which "moderate humidity" condition is flagged. */
export const WEATHER_MED_HUMIDITY_PCT = 50;

// =============================================================================
// Race / Session Defaults
// =============================================================================

/** Fallback total laps when race data is not yet available. */
export const DEFAULT_RACE_LAPS = 60;

/** Default pit stop time loss in seconds (mirrors backend DEFAULT_PIT_LOSS_SECONDS). */
export const DEFAULT_PIT_LOSS_SECONDS = 22.0;

/** Default season year for session selection and API calls. */
export const DEFAULT_YEAR = 2023;

/** Interval between lap marker ticks on the race progress bar. */
export const LAP_MARKER_INTERVAL = 5;

/** SVG padding (px) used in the track map transform. */
export const TRACK_MAP_PADDING = 20;

/** Minimum rendered width (px) of the track map SVG. */
export const TRACK_MAP_MIN_WIDTH = 200;

/** Minimum rendered height (px) of the track map SVG. */
export const TRACK_MAP_MIN_HEIGHT = 150;

// =============================================================================
// Medal / Position Colors
// =============================================================================

export const MEDAL_COLORS = {
    gold: '#ffd700',
    silver: '#c0c0c0',
    bronze: '#cd7f32',
} as const;

// =============================================================================
// Championship / Season Data
// =============================================================================

/** Available F1 seasons for year selection (until the backend provides this list). */
export const AVAILABLE_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025];

/** Strategy stop-count options shown in the backtest page. */
export const STRATEGY_OPTIONS = ['1-stop', '2-stop', '3-stop'];
