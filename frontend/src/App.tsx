/**
 * Main Application Component — v2.1 Professional Shell
 *
 * Shell layout: 32px status bar + 28px tab bar + content area
 * Session management: slide-in drawer triggered by ≡ button
 * State: All race data flows through Zustand store
 *
 * @module App
 */

import { useState, useEffect, useCallback, useRef, type FC } from 'react';
import { Radio, RotateCcw, BarChart2, Trophy } from 'lucide-react';
import styles from './App.module.css';
import LiveDashboard from './pages/LiveDashboard';
import ReplayPage from './pages/ReplayPage';
import BacktestPage from './pages/BacktestPage';
import ChampionshipPage from './pages/ChampionshipPage';
import SessionSelector from './components/SessionSelector';
import { useRaceStore } from './store/raceStore';
import type { RaceState, WebSocketMessage } from './types';

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
    round_number?: number;
}

type ConnectionStatus = 'connected' | 'connecting' | 'disconnected';
type Page = 'live' | 'replay' | 'backtest' | 'championship';

// =============================================================================
// Helpers
// =============================================================================

function getFlagClass(flags: string[], safetycar: boolean, redFlag: boolean, vsc: boolean): string {
    if (redFlag) return 'red';
    if (safetycar) return 'sc';
    if (vsc) return 'vsc';
    if (flags.some(f => f === 'YELLOW' || f === 'DOUBLE_YELLOW')) return 'yellow';
    return 'green';
}

function getFlagLabel(flags: string[], safetycar: boolean, redFlag: boolean, vsc: boolean): string {
    if (redFlag) return 'RED FLAG';
    if (safetycar) return 'SAFETY CAR';
    if (vsc) return 'VSC';
    if (flags.some(f => f === 'YELLOW' || f === 'DOUBLE_YELLOW')) return 'YELLOW';
    return 'GREEN';
}

// =============================================================================
// Component
// =============================================================================

const App: FC = () => {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [selectedSession, setSelectedSession] = useState<Session | null>(null);
    const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
    const [isPolling, setIsPolling] = useState(false);
    const [currentPage, setCurrentPage] = useState<Page>('live');
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [simSpeed, setSimSpeed] = useState(1);
    const [liveSessions, setLiveSessions] = useState<Array<{ session_key: number; session_name: string; session_type: string; circuit: string; country: string }>>([]);
    const wsRef = useRef<WebSocket | null>(null);

    // Zustand store actions + state
    const updateState = useRaceStore(s => s.updateState);
    const setConnected = useRaceStore(s => s.setConnected);
    const setSimulationRunning = useRaceStore(s => s.setSimulationRunning);
    const isLiveMode = useRaceStore(s => s.isLiveMode);
    const liveConnectionQuality = useRaceStore(s => s.liveConnectionQuality);
    const alerts = useRaceStore(s => s.alerts);
    const dismissAlert = useRaceStore(s => s.dismissAlert);

    // Display values from store
    const trackName = useRaceStore(s => s.trackName);
    const sessionName = useRaceStore(s => s.sessionName);
    const currentLap = useRaceStore(s => s.currentLap);
    const totalLaps = useRaceStore(s => s.totalLaps);
    const weather = useRaceStore(s => s.weather);
    const flags = useRaceStore(s => s.flags);
    const safetycar = useRaceStore(s => s.safetycar);
    const redFlag = useRaceStore(s => s.redFlag);
    const vsc = useRaceStore(s => s.virtualSafetyCar);
    const hasData = useRaceStore(s => s.sortedDrivers.length > 0);

    // Fetch available sessions on mount
    useEffect(() => {
        fetchSessions();
    }, []);

    const fetchSessions = async () => {
        try {
            const response = await fetch('/api/sessions?year=2023');
            const data = await response.json();
            setSessions(data);
        } catch (error) {
            console.error('Failed to fetch sessions:', error);
        }
    };

    // WebSocket connection
    const connectWebSocket = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        setConnectionStatus('connecting');

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            setConnectionStatus('connected');
            setConnected(true);
        };

        ws.onmessage = (event) => {
            try {
                const message: WebSocketMessage<RaceState> = JSON.parse(event.data);
                if (message.type === 'state_update' && message.data) {
                    updateState(message.data);
                } else if (message.type === 'session_started') {
                    setIsPolling(true);
                    setSimulationRunning(true);
                } else if (message.type === 'session_stopped') {
                    setIsPolling(false);
                    setSimulationRunning(false);
                } else if (message.type === 'live_started') {
                    setIsPolling(true);
                    setSimulationRunning(true);
                    useRaceStore.getState().setLiveMode(true);
                } else if (message.type === 'live_stopped') {
                    setIsPolling(false);
                    setSimulationRunning(false);
                    useRaceStore.getState().setLiveMode(false);
                }
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        ws.onclose = () => {
            setConnectionStatus('disconnected');
            setConnected(false);
            setIsPolling(false);
            setSimulationRunning(false);
            setTimeout(() => {
                if (selectedSession) connectWebSocket();
            }, 3000);
        };

        ws.onerror = () => {
            setConnectionStatus('disconnected');
            setConnected(false);
        };
    }, [selectedSession, updateState, setConnected, setSimulationRunning]);

    useEffect(() => {
        if (selectedSession) connectWebSocket();
        return () => { wsRef.current?.close(); };
    }, [selectedSession, connectWebSocket]);

    const handleSessionSelect = (session: Session) => {
        setSelectedSession(session);
        setCurrentPage('live');
        setDrawerOpen(false);
    };

    const handleStartSession = () => {
        if (wsRef.current?.readyState === WebSocket.OPEN && selectedSession) {
            let roundNum = selectedSession.round_number;
            if (!roundNum) {
                const idx = sessions.findIndex(s => s.session_key === selectedSession.session_key);
                roundNum = idx >= 0 ? Math.floor(idx / 5) + 1 : 1;
            }
            wsRef.current.send(JSON.stringify({
                type: 'start_session',
                session_key: selectedSession.session_key,
                year: selectedSession.year || 2023,
                round_num: roundNum,
                interval: 3.0,
            }));
            setIsPolling(true);
        }
    };

    const handleStopSession = () => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'stop_session' }));
            setIsPolling(false);
        }
    };

    const handleSpeedChange = (speed: number) => {
        setSimSpeed(speed);
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'set_speed', speed }));
        }
    };

    const fetchLiveSessions = async () => {
        try {
            const response = await fetch('/api/live/sessions');
            const data = await response.json();
            setLiveSessions(data.sessions || []);
        } catch {
            setLiveSessions([]);
        }
    };

    const handleStartLive = (sessionKey?: number) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            const msg: Record<string, unknown> = { type: 'start_live' };
            if (sessionKey) msg.session_key = sessionKey;
            wsRef.current.send(JSON.stringify(msg));
            setIsPolling(true);
            setCurrentPage('live');
            setDrawerOpen(false);
        }
    };

    const handleStopLive = () => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'stop_live' }));
            setIsPolling(false);
        }
    };

    const flagClass = getFlagClass(flags, safetycar, redFlag, vsc);
    const flagLabel = getFlagLabel(flags, safetycar, redFlag, vsc);
    const displayName = trackName || (selectedSession?.circuit) || '—';
    const sessionLabel = sessionName || (selectedSession ? `${selectedSession.session_name} ${selectedSession.year}` : '');

    return (
        <div className="app-container">
            {/* Status Bar */}
            <div className={styles.statusBar}>
                <span className={`connection-dot ${connectionStatus}`} />
                <span className={styles.statusSep}>│</span>
                <span className={styles.statusItemPrimary}>{displayName}</span>
                {sessionLabel && (
                    <>
                        <span className={styles.statusSep}>│</span>
                        <span className={styles.statusItem}>{sessionLabel}</span>
                    </>
                )}
                {currentLap > 0 && (
                    <>
                        <span className={styles.statusSep}>│</span>
                        <span className={styles.statusItem}>
                            LAP <span style={{ color: 'var(--color-info)', fontWeight: 700 }}>{currentLap}</span>
                            <span style={{ color: 'var(--text-muted)' }}>/{totalLaps ?? '—'}</span>
                        </span>
                    </>
                )}
                <span className={styles.statusSep}>│</span>
                <span className={styles.statusItem}>
                    <span className={`flag-dot ${flagClass}`} />
                    {flagLabel}
                </span>
                {weather && (
                    <>
                        <span className={styles.statusSep}>│</span>
                        <span className={styles.statusItem}>
                            {Math.round(weather.air_temp ?? 0)}°C
                            <span style={{ color: 'var(--text-muted)', marginLeft: '4px' }}>{Math.round(weather.humidity ?? 0)}%H</span>
                            {weather.is_raining && <span style={{ color: 'var(--color-info)', marginLeft: '4px' }}>Rain</span>}
                        </span>
                    </>
                )}
                <span className={styles.statusSpacer} />

                {/* Live Badge or Speed Controls */}
                {isPolling && isLiveMode ? (
                    <>
                        <span className={styles.statusSep}>│</span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                            <span style={{
                                display: 'inline-block',
                                width: '8px',
                                height: '8px',
                                borderRadius: '50%',
                                background: liveConnectionQuality === 'poor' ? 'var(--status-amber)' : '#e10600',
                                animation: liveConnectionQuality !== 'poor' ? 'livePulse 1.5s ease-in-out infinite' : 'none',
                                boxShadow: '0 0 6px rgba(225, 6, 0, 0.6)',
                            }} />
                            <span style={{
                                fontSize: '0.65rem',
                                fontWeight: 700,
                                fontFamily: 'var(--font-mono)',
                                color: '#e10600',
                                letterSpacing: '0.08em',
                                textTransform: 'uppercase',
                            }}>
                                LIVE
                            </span>
                            {liveConnectionQuality !== 'good' && (
                                <span style={{
                                    fontSize: '0.55rem',
                                    color: liveConnectionQuality === 'poor' ? 'var(--status-red)' : 'var(--status-amber)',
                                    fontFamily: 'var(--font-mono)',
                                }}>
                                    ({liveConnectionQuality})
                                </span>
                            )}
                        </span>
                    </>
                ) : isPolling ? (
                    <>
                        <span className={styles.statusSep}>│</span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                            <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginRight: '2px' }}>Speed</span>
                            {[1, 2, 5, 10, 20].map(s => (
                                <button
                                    key={s}
                                    onClick={() => handleSpeedChange(s)}
                                    style={{
                                        padding: '1px 6px',
                                        fontSize: '0.65rem',
                                        fontWeight: simSpeed === s ? 700 : 400,
                                        fontFamily: 'var(--font-mono)',
                                        background: simSpeed === s ? 'var(--color-info)' : 'rgba(255,255,255,0.06)',
                                        color: simSpeed === s ? '#000' : 'var(--text-secondary)',
                                        border: simSpeed === s ? 'none' : '1px solid rgba(255,255,255,0.1)',
                                        borderRadius: '3px',
                                        cursor: 'pointer',
                                        transition: 'all 0.15s',
                                        lineHeight: 1.4,
                                    }}
                                >
                                    {s}x
                                </button>
                            ))}
                        </span>
                    </>
                ) : null}

                <button className={styles.menuBtn} onClick={() => setDrawerOpen(true)} title="Sessions">
                    ≡
                </button>
            </div>

            {/* Tab Bar */}
            <nav className={styles.tabBar}>
                <button className={`${styles.tabBtn}${currentPage === 'live' ? ` ${styles.tabBtnActive}` : ''}`} onClick={() => setCurrentPage('live')}>
                    <Radio size={14} />
                    Live
                </button>
                <button className={`${styles.tabBtn}${currentPage === 'replay' ? ` ${styles.tabBtnActive}` : ''}`} onClick={() => setCurrentPage('replay')}>
                    <RotateCcw size={14} />
                    Replay
                </button>
                <button className={`${styles.tabBtn}${currentPage === 'backtest' ? ` ${styles.tabBtnActive}` : ''}`} onClick={() => setCurrentPage('backtest')}>
                    <BarChart2 size={14} />
                    Backtest
                </button>
                <button className={`${styles.tabBtn}${currentPage === 'championship' ? ` ${styles.tabBtnActive}` : ''}`} onClick={() => setCurrentPage('championship')}>
                    <Trophy size={14} />
                    Championship
                </button>
            </nav>

            {/* Alert Strip */}
            {alerts.length > 0 && (
                <div className={styles.alertStrip}>
                    {alerts.map(a => (
                        <div key={a.id} className={styles.alertRow} data-alert-type={a.type.toLowerCase()}>
                            <span className={styles.alertBadge}>{a.type}</span>
                            <span className={styles.alertMsg}>{a.message}</span>
                            <button className={styles.alertDismiss} onClick={() => dismissAlert(a.id)}>×</button>
                        </div>
                    ))}
                </div>
            )}

            {/* Main Content */}
            <main className={styles.mainContent}>
                {currentPage === 'championship' ? (
                    <ChampionshipPage />
                ) : currentPage === 'replay' ? (
                    <ReplayPage />
                ) : currentPage === 'backtest' ? (
                    <BacktestPage />
                ) : hasData ? (
                    <LiveDashboard />
                ) : (
                    <EmptyState
                        selectedSession={selectedSession}
                        connectionStatus={connectionStatus}
                        isPolling={isPolling}
                        onOpenDrawer={() => setDrawerOpen(true)}
                    />
                )}
            </main>

            {/* Session Drawer */}
            {drawerOpen && (
                <>
                    <div className={styles.sessionDrawerOverlay} onClick={() => setDrawerOpen(false)} />
                    <div className={styles.sessionDrawer}>
                        <div className="session-drawer-header">
                            <span>Sessions</span>
                            <button onClick={() => setDrawerOpen(false)}>×</button>
                        </div>

                        {selectedSession && (
                            <>
                                <div className="session-drawer-active">
                                    <div className="active-circuit">{selectedSession.circuit}</div>
                                    <div className="active-details">{selectedSession.session_name} · {selectedSession.year}</div>
                                </div>
                                <div className="session-drawer-controls">
                                    {isPolling ? (
                                        <button className="btn btn-secondary" onClick={handleStopSession} style={{ flex: 1, fontSize: '0.8rem' }}>
                                            Stop
                                        </button>
                                    ) : (
                                        <button
                                            className="btn btn-primary"
                                            onClick={handleStartSession}
                                            disabled={connectionStatus !== 'connected'}
                                            style={{ flex: 1, fontSize: '0.8rem' }}
                                        >
                                            {connectionStatus === 'connecting' ? 'Connecting…' : 'Start'}
                                        </button>
                                    )}
                                </div>
                            </>
                        )}

                        {/* Live Sessions Section */}
                        <div className="session-drawer-list">
                            <div className="session-drawer-list-label" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <span>Live Sessions</span>
                                <button
                                    onClick={fetchLiveSessions}
                                    style={{ fontSize: '0.65rem', color: 'var(--color-info)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-mono)' }}
                                >
                                    Refresh
                                </button>
                            </div>
                            {isLiveMode ? (
                                <div style={{ padding: '8px 12px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                                        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#e10600', animation: 'livePulse 1.5s ease-in-out infinite' }} />
                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-primary)', fontWeight: 600 }}>Live tracking active</span>
                                    </div>
                                    <button className="btn btn-secondary" onClick={handleStopLive} style={{ width: '100%', fontSize: '0.8rem' }}>
                                        Stop Live
                                    </button>
                                </div>
                            ) : liveSessions.length > 0 ? (
                                liveSessions.map(ls => (
                                    <div
                                        key={ls.session_key}
                                        style={{ padding: '8px 12px', borderBottom: '1px solid rgba(255,255,255,0.06)', cursor: 'pointer' }}
                                        onClick={() => handleStartLive(ls.session_key)}
                                    >
                                        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>{ls.circuit} — {ls.session_name}</div>
                                        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>{ls.country} · {ls.session_type}</div>
                                    </div>
                                ))
                            ) : (
                                <div style={{ padding: '8px 12px', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                    No active sessions. Click Refresh to check.
                                </div>
                            )}
                        </div>

                        <div className="session-drawer-list">
                            <div className="session-drawer-list-label">Replay Sessions</div>
                            <SessionSelector
                                sessions={sessions}
                                selectedSession={selectedSession}
                                onSelect={handleSessionSelect}
                            />
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

// =============================================================================
// Empty State
// =============================================================================

interface EmptyStateProps {
    selectedSession: Session | null;
    connectionStatus: ConnectionStatus;
    isPolling: boolean;
    onOpenDrawer: () => void;
}

const EmptyState: FC<EmptyStateProps> = ({ selectedSession, connectionStatus, isPolling, onOpenDrawer }) => (
    <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        height: '100%', gap: '16px', textAlign: 'center', padding: '24px'
    }}>
        <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            {!selectedSession
                ? 'No session selected'
                : isPolling
                    ? 'Loading race data…'
                    : connectionStatus === 'connecting'
                        ? 'Connecting to server…'
                        : 'Session ready — press Start'}
        </div>
        {!selectedSession && (
            <button className="btn btn-primary" onClick={onOpenDrawer} style={{ fontSize: '0.8rem' }}>
                Select Session
            </button>
        )}
    </div>
);

export default App;
