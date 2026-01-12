/**
 * Custom hook for simulation control.
 * 
 * Provides high-level API for:
 * - Loading race sessions
 * - Controlling playback speed
 * - Starting/stopping simulation
 */

import { useCallback, useState } from 'react';
import { useRaceStore } from '../store/raceStore';
import type { SimulationSpeed, Session } from '../types';

const API_BASE = `http://${window.location.hostname}:8000`;

interface UseSimulationReturn {
    // State
    isLoading: boolean;
    error: string | null;
    currentSpeed: SimulationSpeed;
    isRunning: boolean;

    // Actions
    loadSession: (year: number, round: number) => Promise<void>;
    stopSession: () => Promise<void>;
    setSpeed: (speed: SimulationSpeed) => Promise<void>;
    fetchSessions: (year?: number) => Promise<Session[]>;
}

export function useSimulation(): UseSimulationReturn {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const {
        simulationSpeed,
        isSimulationRunning,
        setSimulationSpeed,
        setSimulationRunning,
        setSessions,
    } = useRaceStore();

    // Load a race session
    const loadSession = useCallback(async (year: number, round: number) => {
        setIsLoading(true);
        setError(null);

        try {
            const response = await fetch(
                `${API_BASE}/api/simulation/load/${year}/${round}`,
                { method: 'POST' }
            );

            if (!response.ok) {
                throw new Error(`Failed to load session: ${response.statusText}`);
            }

            setSimulationRunning(true);
        } catch (e) {
            const message = e instanceof Error ? e.message : 'Failed to load session';
            setError(message);
            throw e;
        } finally {
            setIsLoading(false);
        }
    }, [setSimulationRunning]);

    // Stop current session
    const stopSession = useCallback(async () => {
        setIsLoading(true);
        setError(null);

        try {
            const response = await fetch(
                `${API_BASE}/api/simulation/stop`,
                { method: 'POST' }
            );

            if (!response.ok) {
                throw new Error(`Failed to stop session: ${response.statusText}`);
            }

            setSimulationRunning(false);
        } catch (e) {
            const message = e instanceof Error ? e.message : 'Failed to stop session';
            setError(message);
        } finally {
            setIsLoading(false);
        }
    }, [setSimulationRunning]);

    // Set playback speed
    const setSpeed = useCallback(async (speed: SimulationSpeed) => {
        try {
            const response = await fetch(
                `${API_BASE}/api/speed/${speed}`,
                { method: 'POST' }
            );

            if (!response.ok) {
                throw new Error(`Failed to set speed: ${response.statusText}`);
            }

            setSimulationSpeed(speed);
        } catch (e) {
            const message = e instanceof Error ? e.message : 'Failed to set speed';
            setError(message);
        }
    }, [setSimulationSpeed]);

    // Fetch available sessions
    const fetchSessions = useCallback(async (year?: number) => {
        try {
            const url = year
                ? `${API_BASE}/api/sessions?year=${year}`
                : `${API_BASE}/api/sessions`;

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`Failed to fetch sessions: ${response.statusText}`);
            }

            const sessions: Session[] = await response.json();
            setSessions(sessions);
            return sessions;
        } catch (e) {
            const message = e instanceof Error ? e.message : 'Failed to fetch sessions';
            setError(message);
            return [];
        }
    }, [setSessions]);

    return {
        isLoading,
        error,
        currentSpeed: simulationSpeed,
        isRunning: isSimulationRunning,
        loadSession,
        stopSession,
        setSpeed,
        fetchSessions,
    };
}
