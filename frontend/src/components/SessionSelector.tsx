/**
 * Session Selector Component
 *
 * Dropdown for choosing available race sessions, sorted by date.
 *
 * @module components/SessionSelector
 */

import type { FC } from 'react';

// =============================================================================
// Types
// =============================================================================

interface Session {
    session_key: number;
    year: number;
    circuit: string;
    country: string;
    session_name: string;
    date: string;
}

interface SessionSelectorProps {
    /** Available sessions */
    sessions: Session[];
    /** Currently selected session */
    selectedSession: Session | null;
    /** Callback when session is selected */
    onSelect: (session: Session) => void;
}

// =============================================================================
// Component
// =============================================================================

/**
 * Session selector showing available race sessions.
 */
const SessionSelector: FC<SessionSelectorProps> = ({ sessions, selectedSession, onSelect }) => {
    // Filter to race sessions only
    const raceSessionsOnly = sessions.filter((s) => s.session_name === 'Race');

    // Sort by date descending
    const sortedSessions = [...raceSessionsOnly].sort(
        (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
    );

    if (sortedSessions.length === 0) {
        return (
            <div className="text-muted text-sm" style={{ padding: 'var(--space-md)' }}>
                Loading sessions...
            </div>
        );
    }

    return (
        <div className="session-selector">
            {sortedSessions.slice(0, 10).map((session) => (
                <div
                    key={session.session_key}
                    className={`session-option ${selectedSession?.session_key === session.session_key ? 'active' : ''}`}
                    onClick={() => onSelect(session)}
                >
                    <div className="session-name">{session.circuit}</div>
                    <div className="session-details">
                        {session.country} • {new Date(session.date).toLocaleDateString()}
                    </div>
                </div>
            ))}
        </div>
    );
};

export default SessionSelector;
