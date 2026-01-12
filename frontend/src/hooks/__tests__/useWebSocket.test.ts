/**
 * useWebSocket Hook Tests
 *
 * Tests the WebSocket connection management hook.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// Mock WebSocket
class MockWebSocket {
    static instances: MockWebSocket[] = [];

    readyState = 0;
    onopen: (() => void) | null = null;
    onclose: (() => void) | null = null;
    onmessage: ((event: { data: string }) => void) | null = null;
    onerror: (() => void) | null = null;

    constructor(public url: string) {
        MockWebSocket.instances.push(this);
    }

    send = vi.fn();
    close = vi.fn(() => {
        this.readyState = 3;
        this.onclose?.();
    });

    simulateOpen() {
        this.readyState = 1;
        this.onopen?.();
    }

    simulateMessage(data: object) {
        this.onmessage?.({ data: JSON.stringify(data) });
    }

    simulateClose() {
        this.readyState = 3;
        this.onclose?.();
    }

    simulateError() {
        this.onerror?.();
    }

    static clear() {
        MockWebSocket.instances = [];
    }

    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSING = 2;
    static CLOSED = 3;
}

// Store original WebSocket
const originalWebSocket = globalThis.WebSocket;

describe('useWebSocket', () => {
    beforeEach(() => {
        MockWebSocket.clear();
        vi.useFakeTimers();
        // @ts-expect-error Mock WebSocket
        globalThis.WebSocket = MockWebSocket;
    });

    afterEach(() => {
        vi.useRealTimers();
        globalThis.WebSocket = originalWebSocket;
    });

    it('creates WebSocket connection on mount', async () => {
        // Dynamically import to get fresh module
        const { useWebSocket } = await import('../useWebSocket');

        renderHook(() => useWebSocket({ url: 'ws://localhost:8000/ws' }));

        expect(MockWebSocket.instances.length).toBe(1);
        expect(MockWebSocket.instances[0].url).toBe('ws://localhost:8000/ws');
    });

    it('sets connected to true when socket opens', async () => {
        const { useWebSocket } = await import('../useWebSocket');

        const { result } = renderHook(() => useWebSocket({ url: 'ws://localhost:8000/ws' }));

        act(() => {
            MockWebSocket.instances[0].simulateOpen();
        });

        expect(result.current.isConnected).toBe(true);
    });

    it('sets connected to false when socket closes', async () => {
        const { useWebSocket } = await import('../useWebSocket');

        const { result } = renderHook(() => useWebSocket({ url: 'ws://localhost:8000/ws' }));

        act(() => {
            MockWebSocket.instances[0].simulateOpen();
        });

        expect(result.current.isConnected).toBe(true);

        act(() => {
            MockWebSocket.instances[0].simulateClose();
        });

        expect(result.current.isConnected).toBe(false);
    });

    it('attempts reconnection after disconnect', async () => {
        const { useWebSocket } = await import('../useWebSocket');

        renderHook(() => useWebSocket({ url: 'ws://localhost:8000/ws' }));

        const initialInstances = MockWebSocket.instances.length;

        act(() => {
            MockWebSocket.instances[0].simulateOpen();
            MockWebSocket.instances[0].simulateClose();
        });

        // Advance timers for reconnection
        act(() => {
            vi.advanceTimersByTime(4000); // Default reconnectDelay is 3000ms
        });

        expect(MockWebSocket.instances.length).toBeGreaterThan(initialInstances);
    });

    it('calls send on WebSocket when connected', async () => {
        const { useWebSocket } = await import('../useWebSocket');

        const { result } = renderHook(() => useWebSocket({ url: 'ws://localhost:8000/ws' }));

        act(() => {
            MockWebSocket.instances[0].simulateOpen();
        });

        act(() => {
            result.current.send({ type: 'test', data: 'hello' });
        });

        expect(MockWebSocket.instances[0].send).toHaveBeenCalledWith(
            JSON.stringify({ type: 'test', data: 'hello' })
        );
    });

    it('does not send when disconnected', async () => {
        const { useWebSocket } = await import('../useWebSocket');

        const { result } = renderHook(() => useWebSocket({ url: 'ws://localhost:8000/ws' }));

        // Don't open the connection

        act(() => {
            result.current.send({ type: 'test' });
        });

        expect(MockWebSocket.instances[0].send).not.toHaveBeenCalled();
    });

    it('cleans up on unmount', async () => {
        const { useWebSocket } = await import('../useWebSocket');

        const { unmount } = renderHook(() => useWebSocket({ url: 'ws://localhost:8000/ws' }));

        act(() => {
            MockWebSocket.instances[0].simulateOpen();
        });

        unmount();

        expect(MockWebSocket.instances[0].close).toHaveBeenCalled();
    });
});

