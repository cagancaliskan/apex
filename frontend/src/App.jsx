import { useState, useEffect, useCallback, useRef } from 'react'
import LiveDashboard from './pages/LiveDashboard'
import ReplayPage from './pages/ReplayPage'
import SessionSelector from './components/SessionSelector'
import { Activity, Wifi, WifiOff, Radio, PlayCircle } from 'lucide-react'

function App() {
    const [raceState, setRaceState] = useState(null)
    const [sessions, setSessions] = useState([])
    const [selectedSession, setSelectedSession] = useState(null)
    const [connectionStatus, setConnectionStatus] = useState('disconnected')
    const [isPolling, setIsPolling] = useState(false)
    const [currentPage, setCurrentPage] = useState('live') // 'live' or 'replay'
    const wsRef = useRef(null)

    // Fetch available sessions on mount
    useEffect(() => {
        fetchSessions()
    }, [])

    const fetchSessions = async () => {
        try {
            const response = await fetch('/api/sessions?year=2023')
            const data = await response.json()
            setSessions(data)
        } catch (error) {
            console.error('Failed to fetch sessions:', error)
        }
    }

    // WebSocket connection
    const connectWebSocket = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return
        }

        setConnectionStatus('connecting')

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsUrl = `${protocol}//${window.location.host}/ws`

        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => {
            console.log('WebSocket connected')
            setConnectionStatus('connected')
        }

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data)

                if (message.type === 'state_update') {
                    setRaceState(message.data)
                } else if (message.type === 'session_started') {
                    setIsPolling(true)
                } else if (message.type === 'session_stopped') {
                    setIsPolling(false)
                }
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error)
            }
        }

        ws.onclose = () => {
            console.log('WebSocket disconnected')
            setConnectionStatus('disconnected')
            setIsPolling(false)

            // Attempt reconnection after 3 seconds
            setTimeout(() => {
                if (selectedSession) {
                    connectWebSocket()
                }
            }, 3000)
        }

        ws.onerror = (error) => {
            console.error('WebSocket error:', error)
            setConnectionStatus('disconnected')
        }
    }, [selectedSession])

    // Connect WebSocket when session is selected
    useEffect(() => {
        if (selectedSession) {
            connectWebSocket()
        }

        return () => {
            if (wsRef.current) {
                wsRef.current.close()
            }
        }
    }, [selectedSession, connectWebSocket])

    const handleSessionSelect = (session) => {
        setSelectedSession(session)
        setRaceState(null)
        setCurrentPage('live')
    }

    const handleStartSession = () => {
        if (wsRef.current?.readyState === WebSocket.OPEN && selectedSession) {
            wsRef.current.send(JSON.stringify({
                type: 'start_session',
                session_key: selectedSession.session_key,
                interval: 3.0 // Slower for readability
            }))
            setIsPolling(true)
        }
    }

    const handleStopSession = () => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'stop_session' }))
            setIsPolling(false)
        }
    }

    return (
        <div className="app-container">
            {/* Sidebar */}
            <aside className="sidebar">
                <div className="flex items-center gap-md mb-xl">
                    <div className="text-gradient" style={{ fontSize: '1.5rem' }}>
                        <Activity size={28} strokeWidth={2.5} />
                    </div>
                    <div>
                        <h1 style={{ fontSize: '1rem', fontFamily: 'var(--font-display)' }}>
                            <span className="text-gradient">RSW</span>
                        </h1>
                        <p className="text-xs text-muted">Race Strategy Workbench</p>
                    </div>
                </div>

                {/* Navigation Tabs */}
                <div className="flex gap-sm mb-lg">
                    <button
                        onClick={() => setCurrentPage('live')}
                        className={`btn ${currentPage === 'live' ? 'btn-primary' : 'btn-secondary'}`}
                        style={{ flex: 1, fontSize: '0.8rem' }}
                    >
                        <Radio size={14} /> Live
                    </button>
                    <button
                        onClick={() => setCurrentPage('replay')}
                        className={`btn ${currentPage === 'replay' ? 'btn-primary' : 'btn-secondary'}`}
                        style={{ flex: 1, fontSize: '0.8rem' }}
                    >
                        <PlayCircle size={14} /> Replay
                    </button>
                </div>

                {/* Connection Status */}
                <div className="card-glass mb-lg" style={{ padding: 'var(--space-md)' }}>
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-muted">CONNECTION</span>
                        <div className="flex items-center gap-sm">
                            <span className={`connection-dot ${connectionStatus}`}></span>
                            <span className="text-xs" style={{ textTransform: 'capitalize' }}>
                                {connectionStatus}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Session Controls */}
                {selectedSession && (
                    <div className="mb-lg">
                        <div className="session-option active mb-md">
                            <div className="session-name">{selectedSession.circuit}</div>
                            <div className="session-details">
                                {selectedSession.session_name} • {selectedSession.year}
                            </div>
                        </div>

                        {isPolling ? (
                            <button className="btn btn-secondary" onClick={handleStopSession} style={{ width: '100%' }}>
                                <Radio size={16} />
                                Stop Session
                            </button>
                        ) : (
                            <button className="btn btn-primary" onClick={handleStartSession} style={{ width: '100%' }}>
                                <Radio size={16} />
                                Start Session
                            </button>
                        )}
                    </div>
                )}

                {/* Session Selector */}
                <div style={{ flex: 1, overflow: 'auto' }}>
                    <h4 className="text-xs text-muted mb-md" style={{ letterSpacing: '0.1em' }}>
                        AVAILABLE SESSIONS
                    </h4>
                    <SessionSelector
                        sessions={sessions}
                        selectedSession={selectedSession}
                        onSelect={handleSessionSelect}
                    />
                </div>
            </aside>

            {/* Main Content */}
            <main className="main-content">
                {currentPage === 'replay' ? (
                    <ReplayPage />
                ) : raceState && raceState.drivers?.length > 0 ? (
                    <LiveDashboard
                        raceState={raceState}
                        isPolling={isPolling}
                    />
                ) : (
                    <div className="flex flex-col items-center justify-center" style={{
                        height: '80vh',
                        textAlign: 'center'
                    }}>
                        <div className="text-gradient" style={{ fontSize: '4rem', marginBottom: 'var(--space-lg)' }}>
                            <Activity size={80} strokeWidth={1.5} />
                        </div>
                        <h2 style={{ marginBottom: 'var(--space-md)' }}>
                            {selectedSession ? 'Ready to Go' : 'Select a Session'}
                        </h2>
                        <p className="text-muted" style={{ maxWidth: '400px' }}>
                            {selectedSession
                                ? 'Click "Start Session" in the sidebar to begin live tracking.'
                                : 'Choose a race session from the sidebar to view race data and strategy analysis.'}
                        </p>
                    </div>
                )}
            </main>
        </div>
    )
}

export default App
