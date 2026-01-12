/**
 * Custom hook for WebSocket connection management.
 * 
 * Handles:
 * - Connection lifecycle
 * - Auto-reconnection
 * - Message parsing
 * - Heartbeat ping/pong
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useRaceStore } from '../store/raceStore';
import type { WebSocketMessage, RaceState } from '../types';

interface UseWebSocketOptions {
    url?: string;
    reconnectDelay?: number;
    maxReconnectAttempts?: number;
    heartbeatInterval?: number;
}

interface UseWebSocketReturn {
    isConnected: boolean;
    error: string | null;
    send: (message: object) => void;
    reconnect: () => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
    const {
        url = `ws://${window.location.hostname}:8000/ws`,
        reconnectDelay = 3000,
        maxReconnectAttempts = 5,
        heartbeatInterval = 30000,
    } = options;

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectAttempts = useRef(0);
    const heartbeatTimer = useRef<number | null>(null);

    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const { updateState, setConnected, setConnectionError } = useRaceStore();

    // Handle incoming messages
    const handleMessage = useCallback((event: MessageEvent) => {
        try {
            const message: WebSocketMessage = JSON.parse(event.data);

            switch (message.type) {
                case 'state_update':
                    if (message.data) {
                        updateState(message.data as RaceState);
                    }
                    break;

                case 'pong':
                    // Heartbeat acknowledged
                    break;

                case 'session_started':
                    useRaceStore.getState().setSimulationRunning(true);
                    break;

                case 'session_stopped':
                    useRaceStore.getState().setSimulationRunning(false);
                    break;

                case 'error':
                    console.error('WebSocket error:', message.data);
                    setError(String(message.data));
                    break;

                default:
                    console.log('Unknown message type:', message.type);
            }
        } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
        }
    }, [updateState]);

    // Start heartbeat
    const startHeartbeat = useCallback(() => {
        if (heartbeatTimer.current) {
            clearInterval(heartbeatTimer.current);
        }

        heartbeatTimer.current = setInterval(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ type: 'ping' }));
            }
        }, heartbeatInterval);
    }, [heartbeatInterval]);

    // Stop heartbeat
    const stopHeartbeat = useCallback(() => {
        if (heartbeatTimer.current) {
            clearInterval(heartbeatTimer.current);
            heartbeatTimer.current = null;
        }
    }, []);

    // Connect to WebSocket
    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return;
        }

        try {
            wsRef.current = new WebSocket(url);

            wsRef.current.onopen = () => {
                console.log('WebSocket connected');
                setIsConnected(true);
                setConnected(true);
                setError(null);
                setConnectionError(null);
                reconnectAttempts.current = 0;
                startHeartbeat();
            };

            wsRef.current.onmessage = handleMessage;

            wsRef.current.onerror = (event) => {
                console.error('WebSocket error:', event);
                setError('Connection error');
                setConnectionError('Connection error');
            };

            wsRef.current.onclose = () => {
                console.log('WebSocket disconnected');
                setIsConnected(false);
                setConnected(false);
                stopHeartbeat();

                // Auto-reconnect
                if (reconnectAttempts.current < maxReconnectAttempts) {
                    reconnectAttempts.current++;
                    console.log(`Reconnecting... (${reconnectAttempts.current}/${maxReconnectAttempts})`);
                    setTimeout(connect, reconnectDelay);
                } else {
                    setError('Max reconnection attempts reached');
                    setConnectionError('Max reconnection attempts reached');
                }
            };
        } catch (e) {
            console.error('Failed to create WebSocket:', e);
            setError('Failed to connect');
        }
    }, [url, handleMessage, startHeartbeat, stopHeartbeat, setConnected, setConnectionError, reconnectDelay, maxReconnectAttempts]);

    // Send message
    const send = useCallback((message: object) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected, cannot send message');
        }
    }, []);

    // Reconnect manually
    const reconnect = useCallback(() => {
        reconnectAttempts.current = 0;
        if (wsRef.current) {
            wsRef.current.close();
        }
        connect();
    }, [connect]);

    // Connect on mount, cleanup on unmount
    useEffect(() => {
        connect();

        return () => {
            stopHeartbeat();
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [connect, stopHeartbeat]);

    return { isConnected, error, send, reconnect };
}
