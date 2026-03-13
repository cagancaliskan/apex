/**
 * Zustand store for race state management.
 * 
 * Centralized state management replacing prop drilling.
 * All WebSocket updates flow through this store.
 */

import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import type {
    RaceState,
    DriverState,
    WeatherData,
    SimulationSpeed,
    Session,
    RaceMessage,
    TrackConfig,
} from '../types';

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

// =============================================================================
// Store State Interface
// =============================================================================

interface RaceStore {
    // Connection state
    isConnected: boolean;
    connectionError: string | null;

    // Race state (from backend)
    sessionKey: number | null;
    sessionName: string;
    sessionType: string;
    currentLap: number;
    totalLaps: number | null;

    // Drivers
    drivers: Record<number, DriverState>;
    sortedDrivers: DriverState[];

    // Selected driver for telemetry
    selectedDriverNumber: number | null;
    selectedDriver: DriverState | null;

    // Weather
    weather: WeatherData | null;

    // Race status
    flags: string[];
    safetycar: boolean;
    virtualSafetyCar: boolean;
    redFlag: boolean;
    trackStatus: string;
    raceControlMessages: RaceMessage[];
    trackName: string;
    trackConfig: TrackConfig | null;

    // Simulation
    simulationSpeed: SimulationSpeed;
    isSimulationRunning: boolean;

    // Sessions list
    availableSessions: Session[];

    // Alerts
    alerts: Alert[];
    addAlert: (type: AlertType, message: string) => void;
    dismissAlert: (id: string) => void;

    // Actions
    setConnected: (connected: boolean) => void;
    setConnectionError: (error: string | null) => void;
    updateState: (state: Partial<RaceState>) => void;
    updateDrivers: (drivers: Record<number, DriverState>) => void;
    selectDriver: (driverNumber: number | null) => void;
    setSimulationSpeed: (speed: SimulationSpeed) => void;
    setSimulationRunning: (running: boolean) => void;
    setSessions: (sessions: Session[]) => void;
    reset: () => void;
}

// =============================================================================
// Initial State
// =============================================================================

const initialState = {
    isConnected: false,
    connectionError: null,
    sessionKey: null,
    sessionName: '',
    sessionType: '',
    currentLap: 0,
    totalLaps: null,
    drivers: {},
    sortedDrivers: [],
    selectedDriverNumber: null,
    selectedDriver: null,
    weather: null,
    flags: [] as string[],
    safetycar: false,
    virtualSafetyCar: false,
    redFlag: false,
    trackStatus: 'GREEN',
    raceControlMessages: [] as RaceMessage[],
    trackName: '',
    trackConfig: null as TrackConfig | null,
    simulationSpeed: 1 as SimulationSpeed,
    isSimulationRunning: false,
    availableSessions: [],
    alerts: [] as Alert[],
};

// =============================================================================
// Store Implementation
// =============================================================================

export const useRaceStore = create<RaceStore>()(
    devtools(
        subscribeWithSelector((set, get) => ({
            ...initialState,

            // Connection actions
            setConnected: (connected) => set({ isConnected: connected }),
            setConnectionError: (error) => set({ connectionError: error }),

            // State update from WebSocket
            updateState: (state) => {
                const updates: Partial<RaceStore> = {};

                if (state.session_key !== undefined) updates.sessionKey = state.session_key;
                if (state.session_name !== undefined) updates.sessionName = state.session_name;
                if (state.session_type !== undefined) updates.sessionType = state.session_type;
                if (state.current_lap !== undefined) updates.currentLap = state.current_lap;
                if (state.total_laps !== undefined) updates.totalLaps = state.total_laps;
                if (state.weather !== undefined) updates.weather = state.weather;
                if (state.track_name !== undefined) updates.trackName = state.track_name;
                if (state.flags !== undefined) {
                    // Backend sends flags as array; TS type may say string — normalize
                    const rawFlags = state.flags as unknown;
                    updates.flags = Array.isArray(rawFlags) ? rawFlags as string[] : (rawFlags ? [rawFlags as string] : []);
                }
                if (state.safety_car !== undefined) updates.safetycar = state.safety_car;
                if (state.virtual_safety_car !== undefined) updates.virtualSafetyCar = state.virtual_safety_car;
                if (state.red_flag !== undefined) updates.redFlag = state.red_flag;
                if (state.track_status !== undefined) updates.trackStatus = state.track_status as string;
                if (state.race_control_messages !== undefined) updates.raceControlMessages = state.race_control_messages;
                if (state.track_config !== undefined) updates.trackConfig = state.track_config as TrackConfig | null;

                if (state.drivers) {
                    // Backend sends drivers as an array; convert to Record keyed by driver_number
                    let driversRecord: Record<number, DriverState>;
                    if (Array.isArray(state.drivers)) {
                        driversRecord = {};
                        for (const d of state.drivers as unknown as DriverState[]) {
                            driversRecord[d.driver_number] = d;
                        }
                    } else {
                        driversRecord = state.drivers as unknown as Record<number, DriverState>;
                    }
                    updates.drivers = driversRecord;
                    updates.sortedDrivers = Object.values(driversRecord)
                        .filter(d => d.position !== null && d.position > 0)
                        .sort((a, b) => (a.position ?? 999) - (b.position ?? 999));

                    // Update selected driver if exists
                    const selectedNum = get().selectedDriverNumber;
                    if (selectedNum && driversRecord[selectedNum]) {
                        updates.selectedDriver = driversRecord[selectedNum];
                    }
                }

                set(updates);
            },

            // Quick driver update (for frequent telemetry)
            updateDrivers: (drivers) => {
                const sortedDrivers = Object.values(drivers)
                    .filter(d => d.position !== null && d.position > 0)
                    .sort((a, b) => (a.position ?? 999) - (b.position ?? 999));

                const selectedNum = get().selectedDriverNumber;
                const selectedDriver = selectedNum ? drivers[selectedNum] ?? null : null;

                set({ drivers, sortedDrivers, selectedDriver });
            },

            // Driver selection
            selectDriver: (driverNumber) => {
                const drivers = get().drivers;
                const selectedDriver = driverNumber ? drivers[driverNumber] ?? null : null;
                set({ selectedDriverNumber: driverNumber, selectedDriver });
            },

            // Simulation controls
            setSimulationSpeed: (speed) => set({ simulationSpeed: speed }),
            setSimulationRunning: (running) => set({ isSimulationRunning: running }),

            // Sessions
            setSessions: (sessions) => set({ availableSessions: sessions }),

            // Alert actions
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

            // Reset
            reset: () => set(initialState),
        })),
        { name: 'race-store' }
    )
);

// =============================================================================
// Selectors (for performance optimization)
// =============================================================================

export const selectDriverByNumber = (driverNumber: number) =>
    (state: RaceStore) => state.drivers[driverNumber];

export const selectLeader = (state: RaceStore) =>
    state.sortedDrivers[0] ?? null;

export const selectWeather = (state: RaceStore) => state.weather;

export const selectIsRaining = (state: RaceStore) =>
    state.weather?.is_raining ?? false;
