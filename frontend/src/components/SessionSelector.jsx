/**
 * Session selector component for choosing race sessions.
 */

function SessionSelector({ sessions, selectedSession, onSelect }) {
    // Group sessions by year and country
    const raceSessionsOnly = sessions.filter(s => s.session_name === 'Race')

    // Sort by date descending
    const sortedSessions = [...raceSessionsOnly].sort((a, b) =>
        new Date(b.date) - new Date(a.date)
    )

    if (sortedSessions.length === 0) {
        return (
            <div className="text-muted text-sm" style={{ padding: 'var(--space-md)' }}>
                Loading sessions...
            </div>
        )
    }

    return (
        <div className="session-selector">
            {sortedSessions.slice(0, 10).map(session => (
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
    )
}

export default SessionSelector
