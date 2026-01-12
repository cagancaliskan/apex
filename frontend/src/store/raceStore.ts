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
    Session
} from '../types';

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

    // Simulation
    simulationSpeed: SimulationSpeed;
    isSimulationRunning: boolean;

    // Sessions list
    availableSessions: Session[];

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
    simulationSpeed: 1 as SimulationSpeed,
    isSimulationRunning: false,
    availableSessions: [],
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

                if (state.drivers) {
                    updates.drivers = state.drivers;
                    updates.sortedDrivers = Object.values(state.drivers)
                        .filter(d => d.position !== null && d.position > 0)
                        .sort((a, b) => (a.position ?? 999) - (b.position ?? 999));

                    // Update selected driver if exists
                    const selectedNum = get().selectedDriverNumber;
                    if (selectedNum && state.drivers[selectedNum]) {
                        updates.selectedDriver = state.drivers[selectedNum];
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
