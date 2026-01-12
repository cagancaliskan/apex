/**
 * Core type definitions for the F1 Race Strategy Workbench.
 * 
 * These types mirror the backend Pydantic schemas and ensure
 * type safety across the frontend application.
 */

// =============================================================================
// Driver Types
// =============================================================================

export type TyreCompound = 'SOFT' | 'MEDIUM' | 'HARD' | 'INTERMEDIATE' | 'WET' | 'UNKNOWN';

export interface DriverState {
    driver_number: number;
    name_acronym: string | null;
    full_name: string | null;
    team_name: string | null;
    team_colour: string | null;
    position: number | null;

    // Timing
    current_lap: number;
    last_lap_time: number | null;
    best_lap_time: number | null;
    gap_to_leader: number | null;
    gap_to_ahead: number | null;

    // Sectors
    sector_1: number | null;
    sector_2: number | null;
    sector_3: number | null;

    // Telemetry
    speed: number;
    gear: number;
    throttle: number;
    brake: number;
    drs: number;

    // Position on track
    rel_dist: number | null;
    x: number | null;
    y: number | null;

    // Tyre info
    compound: TyreCompound | null;
    tyre_age: number;
    is_pit_out_lap: boolean;
    lap_in_stint: number;
    stint_start_lap: number;

    // Strategy metrics
    deg_slope: number;
    cliff_risk: number;
    pit_window_min: number;
    pit_window_max: number;
    pit_window_ideal: number;
    pit_recommendation: string;
    pit_confidence: number;
    pit_reason: string;
    undercut_threat: boolean;
    overcut_opportunity: boolean;

    // Physics Predictions
    predicted_pace: number[];
    predicted_rejoin_position: number;
    rejoin_traffic_severity: number;
}

// =============================================================================
// Weather Types
// =============================================================================

export interface WeatherData {
    track_temp: number;
    air_temp: number;
    humidity: number;
    wind_speed: number;
    wind_direction: string;
    rainfall: number;
    is_raining: boolean;
}

// =============================================================================
// Track Types
// =============================================================================

export interface TrackPoint {
    x: number;
    y: number;
}

export interface TrackBounds {
    x_min: number;
    x_max: number;
    y_min: number;
    y_max: number;
}

export interface DRSZone {
    start_x: number;
    start_y: number;
    end_x: number;
    end_y: number;
}

export interface TrackConfig {
    center_line: TrackPoint[];
    inner_edge: TrackPoint[];
    outer_edge: TrackPoint[];
    bounds: TrackBounds;
    drs_zones?: DRSZone[];
    // Legacy support if needed, or remove:
    // points?: TrackPoint[]; 
}

// =============================================================================
// Race State Types
// =============================================================================

export type TrackStatus = 'GREEN' | 'YELLOW' | 'RED' | 'SC' | 'VSC';

export interface RaceMessage {
    message: string;
    flag: string | null;
    scope: string | null;
    category: string | null;
    lap_number: number | null;
}

export interface RaceState {
    session_key: number;
    meeting_key: number;
    session_name: string;
    session_type: string;

    // Drivers indexed by driver_number
    drivers: Record<number, DriverState>;

    // Race progress
    current_lap: number;
    total_laps: number | null;

    // Status
    track_status?: TrackStatus; // 'GREEN', 'YELLOW', 'SC', etc.

    // Track & Weather
    track_config: TrackConfig | null;
    weather: WeatherData | null;

    // Messages
    race_control_messages: RaceMessage[];
}

// =============================================================================
// WebSocket Types
// =============================================================================

export type WebSocketMessageType =
    | 'state_update'
    | 'session_started'
    | 'session_stopped'
    | 'speed_set'
    | 'ping'
    | 'pong'
    | 'error';

export interface WebSocketMessage<T = unknown> {
    type: WebSocketMessageType;
    data?: T;
}

export interface StateUpdateMessage extends WebSocketMessage<RaceState> {
    type: 'state_update';
    data: RaceState;
}

// =============================================================================
// API Types
// =============================================================================

export interface Session {
    session_key: number;
    session_name: string;
    session_type: string;
    circuit: string;
    country: string;
    date: string;
    year: number;
    round_number: number;
}

export interface ApiResponse<T> {
    status: 'ok' | 'error';
    message?: string;
    data?: T;
}

// =============================================================================
// Simulation Types
// =============================================================================

export type SimulationSpeed = 1 | 5 | 10 | 20 | 50;

export interface SimulationState {
    isRunning: boolean;
    currentLap: number;
    totalLaps: number | null;
    speed: SimulationSpeed;
    year: number | null;
    round: number | null;
}

// =============================================================================
// UI Types
// =============================================================================

export interface SelectedDriver {
    driverNumber: number;
    showTelemetry: boolean;
}

export type ViewMode = 'live' | 'replay' | 'analysis';
