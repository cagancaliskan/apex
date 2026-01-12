/**
 * Replay Page
 *
 * Playback cached race sessions with controls for speed,
 * seeking, and comprehensive race analysis.
 *
 * @module pages/ReplayPage
 */

import { useState, useEffect, type FC, type MouseEvent } from 'react';
import { Play, Pause, Square, SkipBack, FastForward } from 'lucide-react';
import DriverTable from '../components/DriverTable';
import StrategyPanel from '../components/StrategyPanel';
import TelemetryPanel from '../components/TelemetryPanel';
import RaceProgressBar from '../components/RaceProgressBar';
import WeatherWidget from '../components/WeatherWidget';
import TrackMap from '../components/TrackMap';
import TelemetryChart from '../components/TelemetryChart';
import type { DriverState, TrackStatus } from '../types';

// =============================================================================
// Types
// =============================================================================

interface Session {
    session_key: number;
    country: string;
    session_name: string;
    circuit: string;
}

interface ReplayState {
    track_name?: string;
    current_lap: number;
    total_laps: number;
    status?: string;
    drivers?: DriverState[];
    events?: any[];
    flag_periods?: any[];
    weather?: {
        track_temp?: number;
        air_temp?: number;
        humidity?: number;
        wind_speed?: number;
        wind_direction?: string;
        rainfall?: number;
        is_raining?: boolean;
    };
    trackData?: any;
    drs_zones?: any[];
    braking_zones?: any[];
    track_status?: TrackStatus;
}

// =============================================================================
// Component
// =============================================================================

const ReplayPage: FC = () => {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [selectedSession, setSelectedSession] = useState<number | null>(null);
    const [replayState, setReplayState] = useState<ReplayState | null>(null);
    const [speed, setSpeed] = useState(0.25);
    const [isPlaying, setIsPlaying] = useState(false);
    const [loading, setLoading] = useState(false);
    const [selectedDriver, setSelectedDriver] = useState<DriverState | null>(null);

    // Fetch available sessions
    useEffect(() => {
        fetch('/api/replay/sessions')
            .then((res) => res.json())
            .then((data) => setSessions(data.sessions || []))
            .catch((err) => console.error('Failed to fetch sessions:', err));
    }, []);

    const startReplay = async (sessionKey: number) => {
        setLoading(true);
        try {
            const res = await fetch(`/api/replay/${sessionKey}/start?speed=${speed}`, { method: 'POST' });
            const data = await res.json();
            setReplayState(data);
            setIsPlaying(true);
            setSelectedSession(sessionKey);
        } catch (err) {
            console.error('Failed to start replay:', err);
        }
        setLoading(false);
    };

    const controlReplay = async (action: string, value: number | null = null) => {
        try {
            const url = `/api/replay/control?action=${action}${value !== null ? `&value=${value}` : ''}`;
            const res = await fetch(url, { method: 'POST' });
            const data = await res.json();
            setReplayState((prev) => (prev ? { ...prev, ...data } : data));
            setIsPlaying(data.status === 'playing');
        } catch (err) {
            console.error('Replay control failed:', err);
        }
    };

    const togglePlay = () => controlReplay(isPlaying ? 'pause' : 'play');
    const changeSpeed = (newSpeed: number) => { setSpeed(newSpeed); controlReplay('speed', newSpeed); };

    const handleMouseEnter = (e: MouseEvent<HTMLButtonElement>) => { e.currentTarget.style.borderColor = 'var(--accent-cyan)'; };
    const handleMouseLeave = (e: MouseEvent<HTMLButtonElement>) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; };

    return (
        <div className="animate-fade-in" style={{ padding: 'var(--space-lg)' }}>
            <header style={{ marginBottom: 'var(--space-xl)' }}>
                <h1 style={{ fontSize: '1.5rem', fontFamily: 'var(--font-display)', marginBottom: 'var(--space-sm)' }}>🔄 Race Replay</h1>
                <p className="text-muted">Play back cached race sessions for analysis</p>
            </header>

            {/* Session Selector */}
            {!selectedSession && (
                <div className="card" style={{ maxWidth: '600px' }}>
                    <h3 className="card-title">Available Sessions</h3>
                    {sessions.length === 0 ? (
                        <p className="text-muted">
                            No cached sessions found. Run the download script first:
                            <br />
                            <code style={{ display: 'block', marginTop: 'var(--space-sm)', padding: 'var(--space-sm)', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)' }}>
                                python scripts/download_session.py --year 2023 --round 1
                            </code>
                        </p>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                            {sessions.map((session) => (
                                <button key={session.session_key} onClick={() => startReplay(session.session_key)} disabled={loading} onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--space-md)', background: 'var(--bg-tertiary)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', color: 'var(--text-primary)', transition: 'all 0.2s' }}>
                                    <div>
                                        <div style={{ fontWeight: 600 }}>{session.country} - {session.session_name}</div>
                                        <div className="text-muted text-sm">{session.circuit}</div>
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
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
                            <div>
                                <h3 style={{ margin: 0 }}>{replayState?.track_name || 'Loading...'}</h3>
                                <span className="text-muted">Lap {replayState?.current_lap || 0} / {replayState?.total_laps || '?'}</span>
                            </div>
                            <button onClick={() => setSelectedSession(null)} style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: 'var(--text-secondary)', padding: 'var(--space-xs) var(--space-sm)', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}>
                                Back to Sessions
                            </button>
                        </div>

                        {/* Timeline */}
                        <div style={{ height: '8px', background: 'var(--bg-tertiary)', borderRadius: '4px', marginBottom: 'var(--space-md)', overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${((replayState?.current_lap || 0) / (replayState?.total_laps || 1)) * 100}%`, background: 'linear-gradient(90deg, var(--accent-cyan), var(--accent-magenta))', transition: 'width 0.3s ease' }} />
                        </div>

                        {/* Controls */}
                        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 'var(--space-md)' }}>
                            <button onClick={() => controlReplay('seek', 0)} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}><SkipBack size={24} /></button>
                            <button onClick={togglePlay} style={{ width: '48px', height: '48px', borderRadius: '50%', background: 'var(--accent-cyan)', border: 'none', color: 'black', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                {isPlaying ? <Pause size={24} /> : <Play size={24} />}
                            </button>
                            <button onClick={() => controlReplay('stop')} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}><Square size={24} /></button>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)', marginLeft: 'var(--space-lg)', flexWrap: 'wrap' }}>
                                <FastForward size={16} className="text-muted" />
                                {[0.05, 0.1, 0.25, 0.5, 1, 2, 5].map((s) => (
                                    <button key={s} onClick={() => changeSpeed(s)} style={{ padding: 'var(--space-xs) var(--space-sm)', background: speed === s ? 'var(--accent-cyan)' : 'transparent', color: speed === s ? 'black' : 'var(--text-primary)', border: speed === s ? 'none' : '1px solid var(--text-muted)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '0.8rem', transition: 'all 0.2s' }}>
                                        {s}x
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <RaceProgressBar currentLap={replayState?.current_lap || 0} totalLaps={replayState?.total_laps || 0} events={replayState?.events || []} flagPeriods={replayState?.flag_periods || []} onSeek={(data: { lap?: number }) => controlReplay('seek', data.lap || 0)} showLapMarkers />

                    {/* Main Dashboard Grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 400px 350px', gap: 'var(--space-lg)', marginTop: 'var(--space-lg)' }}>
                        <div>
                            <h3 style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 'var(--space-md)' }}>Race Classification</h3>
                            <DriverTable drivers={replayState?.drivers || []} onDriverSelect={setSelectedDriver} selectedDriver={selectedDriver} />
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
                            <TrackMap
                                drivers={replayState?.drivers || []}
                                trackConfig={replayState?.trackData ? { ...replayState.trackData, drs_zones: replayState.drs_zones } : null}
                                selectedDriver={selectedDriver}
                                onDriverSelect={setSelectedDriver}
                                trackStatus={replayState?.track_status}
                            />
                            {selectedDriver && <TelemetryChart telemetryData={(selectedDriver as DriverState & { telemetry?: any[] }).telemetry || []} driver={selectedDriver} compact />}
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
                            <WeatherWidget weather={replayState?.weather} />
                            {selectedDriver && <TelemetryPanel driver={selectedDriver} />}
                            <StrategyPanel drivers={replayState?.drivers || []} selectedDriver={selectedDriver} />
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default ReplayPage;
