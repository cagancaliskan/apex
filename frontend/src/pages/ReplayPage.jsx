/**
 * Replay Page - playback cached race sessions with controls.
 */

import { useState, useEffect } from 'react'
import { Play, Pause, Square, SkipBack, SkipForward, FastForward } from 'lucide-react'
import DriverTable from '../components/DriverTable'
import StrategyPanel from '../components/StrategyPanel'

function ReplayPage() {
    const [sessions, setSessions] = useState([])
    const [selectedSession, setSelectedSession] = useState(null)
    const [replayState, setReplayState] = useState(null)
    const [speed, setSpeed] = useState(0.5)
    const [isPlaying, setIsPlaying] = useState(false)
    const [loading, setLoading] = useState(false)

    // Fetch available sessions
    useEffect(() => {
        fetch('/api/replay/sessions')
            .then(res => res.json())
            .then(data => setSessions(data.sessions || []))
            .catch(err => console.error('Failed to fetch sessions:', err))
    }, [])

    // Start replay
    const startReplay = async (sessionKey) => {
        setLoading(true)
        try {
            const res = await fetch(`/api/replay/${sessionKey}/start?speed=${speed}`, {
                method: 'POST'
            })
            const data = await res.json()
            setReplayState(data)
            setIsPlaying(true)
            setSelectedSession(sessionKey)
        } catch (err) {
            console.error('Failed to start replay:', err)
        }
        setLoading(false)
    }

    // Control replay
    const controlReplay = async (action, value = null) => {
        try {
            const url = `/api/replay/control?action=${action}${value !== null ? `&value=${value}` : ''}`
            const res = await fetch(url, { method: 'POST' })
            const data = await res.json()
            setReplayState(prev => ({ ...prev, ...data }))
            setIsPlaying(data.status === 'playing')
        } catch (err) {
            console.error('Replay control failed:', err)
        }
    }

    const togglePlay = () => {
        controlReplay(isPlaying ? 'pause' : 'play')
    }

    const changeSpeed = (newSpeed) => {
        setSpeed(newSpeed)
        controlReplay('speed', newSpeed)
    }

    return (
        <div className="animate-fade-in" style={{ padding: 'var(--space-lg)' }}>
            {/* Header */}
            <header style={{ marginBottom: 'var(--space-xl)' }}>
                <h1 style={{
                    fontSize: '1.5rem',
                    fontFamily: 'var(--font-display)',
                    marginBottom: 'var(--space-sm)',
                }}>
                    🔄 Race Replay
                </h1>
                <p className="text-muted">
                    Play back cached race sessions for analysis
                </p>
            </header>

            {/* Session Selector */}
            {!selectedSession && (
                <div className="card" style={{ maxWidth: '600px' }}>
                    <h3 className="card-title">Available Sessions</h3>

                    {sessions.length === 0 ? (
                        <p className="text-muted">
                            No cached sessions found. Run the download script first:
                            <br />
                            <code style={{
                                display: 'block',
                                marginTop: 'var(--space-sm)',
                                padding: 'var(--space-sm)',
                                background: 'var(--bg-tertiary)',
                                borderRadius: 'var(--radius-sm)',
                            }}>
                                python scripts/download_session.py --year 2023 --round 1
                            </code>
                        </p>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                            {sessions.map(session => (
                                <button
                                    key={session.session_key}
                                    onClick={() => startReplay(session.session_key)}
                                    disabled={loading}
                                    style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        padding: 'var(--space-md)',
                                        background: 'var(--bg-tertiary)',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        borderRadius: 'var(--radius-sm)',
                                        cursor: 'pointer',
                                        color: 'var(--text-primary)',
                                        transition: 'all 0.2s',
                                    }}
                                    onMouseEnter={e => e.target.style.borderColor = 'var(--accent-cyan)'}
                                    onMouseLeave={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
                                >
                                    <div>
                                        <div style={{ fontWeight: 600 }}>
                                            {session.country} - {session.session_name}
                                        </div>
                                        <div className="text-muted text-sm">
                                            {session.circuit}
                                        </div>
                                    </div>
                                    <Play size={20} />
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Playback Controls */}
            {selectedSession && (
                <>
                    <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                        {/* Session Info */}
                        <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginBottom: 'var(--space-md)',
                        }}>
                            <div>
                                <h3 style={{ margin: 0 }}>
                                    {replayState?.track_name || 'Loading...'}
                                </h3>
                                <span className="text-muted">
                                    Lap {replayState?.current_lap || 0} / {replayState?.total_laps || '?'}
                                </span>
                            </div>

                            <button
                                onClick={() => setSelectedSession(null)}
                                style={{
                                    background: 'transparent',
                                    border: '1px solid rgba(255,255,255,0.2)',
                                    color: 'var(--text-secondary)',
                                    padding: 'var(--space-xs) var(--space-sm)',
                                    borderRadius: 'var(--radius-sm)',
                                    cursor: 'pointer',
                                }}
                            >
                                Back to Sessions
                            </button>
                        </div>

                        {/* Timeline */}
                        <div style={{
                            height: '8px',
                            background: 'var(--bg-tertiary)',
                            borderRadius: '4px',
                            marginBottom: 'var(--space-md)',
                            overflow: 'hidden',
                        }}>
                            <div style={{
                                height: '100%',
                                width: `${((replayState?.current_lap || 0) / (replayState?.total_laps || 1)) * 100}%`,
                                background: 'linear-gradient(90deg, var(--accent-cyan), var(--accent-magenta))',
                                transition: 'width 0.3s ease',
                            }} />
                        </div>

                        {/* Controls */}
                        <div style={{
                            display: 'flex',
                            justifyContent: 'center',
                            alignItems: 'center',
                            gap: 'var(--space-md)',
                        }}>
                            <button
                                onClick={() => controlReplay('seek', 0)}
                                className="control-btn"
                                style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
                            >
                                <SkipBack size={24} />
                            </button>

                            <button
                                onClick={togglePlay}
                                style={{
                                    width: '48px',
                                    height: '48px',
                                    borderRadius: '50%',
                                    background: 'var(--accent-cyan)',
                                    border: 'none',
                                    color: 'black',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                            >
                                {isPlaying ? <Pause size={24} /> : <Play size={24} />}
                            </button>

                            <button
                                onClick={() => controlReplay('stop')}
                                className="control-btn"
                                style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
                            >
                                <Square size={24} />
                            </button>

                            {/* Speed Control */}
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 'var(--space-xs)',
                                marginLeft: 'var(--space-lg)',
                            }}>
                                <FastForward size={16} className="text-muted" />
                                {[0.1, 0.25, 0.5, 1, 2, 5].map(s => (
                                    <button
                                        key={s}
                                        onClick={() => changeSpeed(s)}
                                        style={{
                                            padding: 'var(--space-xs) var(--space-sm)',
                                            background: speed === s ? 'var(--accent-cyan)' : 'var(--bg-tertiary)',
                                            color: speed === s ? 'black' : 'var(--text-secondary)',
                                            border: 'none',
                                            borderRadius: 'var(--radius-sm)',
                                            cursor: 'pointer',
                                            fontSize: '0.8rem',
                                        }}
                                    >
                                        {s}x
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Dashboard content would go here */}
                    <div className="text-muted" style={{ textAlign: 'center', padding: 'var(--space-xl)' }}>
                        Replay running - watch the lap counter advance
                    </div>
                </>
            )}
        </div>
    )
}

export default ReplayPage
