// Test setup for Vitest
import '@testing-library/jest-dom'

// Mock fetch
global.fetch = vi.fn()

// Mock WebSocket
global.WebSocket = vi.fn(() => ({
    send: vi.fn(),
    close: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
}))
