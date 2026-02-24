/**
 * Live Dashboard - Professional Race Engineering Interface (v6)
 *
 * Dense, functional layout modeled on ATLAS/TCDS pit wall tools.
 * No decorative glows, no gaming aesthetics. Every pixel is data.
 *
 * Layout:
 * - 48px sidebar rail (icon-only)
 * - 44px top bar (session info)
 * - Main grid: 460px left | 1fr right
 *   - Left: leaderboard + strategy strip + race control
 *   - Right: track map + telemetry + driver HUD
 *
 * @module pages/LiveDashboard
 */

import { useState, useRef, useEffect, useMemo, type FC } from 'react';
import TrackMap from '../components/TrackMap';
import WeatherWidget from '../components/WeatherWidget';
import type { RaceState, DriverState } from '../types';

// =============================================================================
// Constants & Helpers
// =============================================================================

const getDriversArray = (drivers: Record<number, DriverState> | DriverState[]): DriverState[] => {
    return Array.isArray(drivers) ? drivers : Object.values(drivers || {});
};

const comparePositions = (a: DriverState, b: DriverState): number => {
    const posA = typeof a.position === 'number' && a.position > 0 ? a.position : 999;
    const posB = typeof b.position === 'number' && b.position > 0 ? b.position : 999;
    return posA - posB;
};

const fmtGap = (gap: number | undefined | null): string => {
    if (gap == null) return '-';
    return `+${gap.toFixed(3)}`;
};

const fmtLap = (t: number | undefined | null): string => {
    if (!t || t <= 0) return '-';
    const min = Math.floor(t / 60);
    const sec = (t % 60).toFixed(3);
    return min > 0 ? `${min}:${sec.padStart(6, '0')}` : sec;
};

const TYRE_COLORS: Record<string, string> = {
    SOFT: '#ff0000', MEDIUM: '#ffd700', HARD: '#ffffff',
    INTERMEDIATE: '#00ff00', WET: '#0066ff',
};

// =============================================================================
// Main Component
// =============================================================================

const LiveDashboard: FC = () => {
    const [raceState, setRaceState] = useState<RaceState | null>(null);
    const [selectedDriver, setSelectedDriver] = useState<DriverState | null>(null);
    const wsRef = useRef<WebSocket | null>(null);

    // WebSocket setup
    useEffect(() => {
        const wsUrl = typeof import.meta !== 'undefined' && 'env' in import.meta
            ? ((import.meta as any).env.VITE_WS_URL || 'ws://localhost:8000/ws')
            : 'ws://localhost:8000/ws';
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'state_update') {
                setRaceState(msg.data);
                if (!selectedDriver && msg.data.drivers) {
                    const drivers = getDriversArray(msg.data.drivers);
                    if (drivers.length > 0) setSelectedDriver(drivers[0]);
                }
            }
        };

        return () => ws.close();
    }, []);

    const driversArray = useMemo(() => {
        if (!raceState) return [];
        return getDriversArray(raceState.drivers).sort(comparePositions);
    }, [raceState]);

    const currentLap = raceState?.current_lap || 0;
    const trackConfig = raceState?.track_config || null;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-primary)' }}>
            {/* Top Bar */}
            <div style={{
                height: 'var(--topbar-height)', background: 'var(--bg-secondary)',
                borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex',
                alignItems: 'center', padding: '0 var(--space-md)', gap: 'var(--space-lg)', zIndex: 50
            }}>
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <div style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                            {raceState?.track_name || 'Loading...'}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                            {raceState?.session_name || '—'}
                        </div>
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-lg)', fontFamily: 'var(--font-mono)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>L</span>
                        <span style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-info)' }}>{currentLap}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>/{raceState?.total_laps || '—'}</span>
                    </div>
                </div>
                {raceState?.weather && <WeatherWidget weather={raceState.weather} />}
            </div>

            {/* Main Grid */}
            <div style={{
                flex: 1, display: 'grid', gridTemplateColumns: '460px 1fr', gap: 'var(--space-md)',
                padding: 'var(--space-md)', overflow: 'hidden'
            }}>
                {/* Left Column: Leaderboard + Strategy + Race Control */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', overflow: 'hidden' }}>
                    {/* Leaderboard Rows */}
                    <div style={{
                        flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: '2px',
                        borderRadius: 'var(--radius-lg)', background: 'var(--bg-card)', padding: '2px',
                        border: '1px solid rgba(255,255,255,0.05)'
                    }}>
                        {driversArray.map((d) => {
                            const isSelected = selectedDriver?.driver_number === d.driver_number;
                            const teamColor = d.team_colour ? `#${d.team_colour}` : '#ffffff';
                            const tyreC = TYRE_COLORS[d.compound || 'MEDIUM'];
                            const gap = d.gap_to_leader;

                            return (
                                <div key={d.driver_number} onClick={() => setSelectedDriver(d)} style={{
                                    padding: 'var(--space-sm) var(--space-md)', cursor: 'pointer',
                                    background: isSelected ? 'rgba(88,166,255,0.1)' : 'transparent',
                                    borderLeft: isSelected ? '2px solid var(--color-info)' : '2px solid transparent',
                                    display: 'grid', gridTemplateColumns: '28px 1fr 56px 68px 44px 44px 44px 32px',
                                    gap: '8px', alignItems: 'center', fontSize: '0.85rem', transition: 'all 100ms',
                                    borderRadius: '3px', height: '38px'
                                }}>
                                    <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, textAlign: 'center' }}>
                                        {d.position || '—'}
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0 }}>
                                        <div style={{ width: '4px', height: '24px', background: teamColor, borderRadius: '2px', flexShrink: 0 }} />
                                        <span style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {d.name_acronym || d.driver_number}
                                        </span>
                                    </div>
                                    <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                                        {fmtGap(gap)}
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                        <div style={{
                                            width: '26px', height: '26px', borderRadius: 'var(--radius-full)',
                                            background: tyreC, color: 'black', fontWeight: 700, fontSize: '0.65rem',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
                                        }}>
                                            {(d.compound || 'MEDIUM')[0]}
                                        </div>
                                    </div>
                                    {[d.sector_1, d.sector_2, d.sector_3].map((s, i) => (
                                        <div key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                            {s ? fmtLap(s) : '—'}
                                        </div>
                                    ))}
                                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                        {d.current_lap || 0}
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Strategy Strip */}
                    <div style={{
                        height: '150px', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)',
                        border: '1px solid rgba(255,255,255,0.05)', padding: '8px', display: 'flex', gap: '6px'
                    }}>
                        {selectedDriver ? (
                            <>
                                <div style={{
                                    padding: '8px 12px', background: 'var(--bg-tertiary)', borderRadius: '3px',
                                    display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'center', flex: 0.5
                                }}>
                                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Tyre</div>
                                    <div style={{
                                        width: '44px', height: '44px', borderRadius: 'var(--radius-full)',
                                        background: TYRE_COLORS[selectedDriver.compound || 'MEDIUM'],
                                        color: 'black', fontWeight: 700, fontSize: '1.1rem',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                                    }}>
                                        {(selectedDriver.compound || 'MEDIUM')[0]}
                                    </div>
                                </div>

                                <div style={{
                                    padding: '8px 12px', background: 'var(--bg-tertiary)', borderRadius: '3px',
                                    display: 'flex', flexDirection: 'column', gap: '4px', flex: 1, justifyContent: 'center'
                                }}>
                                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Pit Window</div>
                                    <div style={{
                                        fontFamily: 'var(--font-mono)', fontSize: '1.3rem', fontWeight: 700,
                                        color: selectedDriver.pit_window_min === 0 ? 'var(--text-muted)' : 'var(--color-info)'
                                    }}>
                                        {selectedDriver.pit_window_min === 0 ? '—' : `L${selectedDriver.pit_window_min}`}
                                    </div>
                                </div>

                                <div style={{
                                    padding: '8px 12px', background: 'var(--bg-tertiary)', borderRadius: '3px',
                                    display: 'flex', flexDirection: 'column', gap: '4px', flex: 1, justifyContent: 'center'
                                }}>
                                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Fuel</div>
                                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.3rem', fontWeight: 700 }}>
                                        {(selectedDriver.fuel_remaining_kg || 0).toFixed(1)}kg
                                    </div>
                                </div>

                                <div style={{
                                    padding: '8px 12px', background: 'var(--bg-tertiary)', borderRadius: '3px',
                                    display: 'flex', flexDirection: 'column', gap: '4px', flex: 0.8, justifyContent: 'center'
                                }}>
                                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Model</div>
                                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.3rem', fontWeight: 700 }}>
                                        {Math.round((selectedDriver.model_confidence || 0) * 100)}%
                                    </div>
                                </div>
                            </>
                        ) : null}
                    </div>

                    {/* Race Control */}
                    <div style={{
                        height: '116px', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)',
                        border: '1px solid rgba(255,255,255,0.05)', padding: 'var(--space-md)', overflow: 'auto'
                    }}>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: 'var(--space-sm)' }}>
                            Race Control
                        </div>
                        {raceState?.race_control_messages && raceState.race_control_messages.length > 0 ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
                                {[...raceState.race_control_messages].reverse().slice(0, 5).map((msg, i) => (
                                    <div key={i} style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.3 }}>
                                        {msg.message}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>No messages</div>
                        )}
                    </div>
                </div>

                {/* Right Column */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', overflow: 'hidden' }}>
                    <div style={{ flex: 1, background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid rgba(255,255,255,0.05)', overflow: 'hidden' }}>
                        <TrackMap drivers={driversArray} trackConfig={trackConfig} selectedDriver={selectedDriver} showDRS={true} />
                    </div>
                    {selectedDriver && (
                        <div style={{
                            background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)',
                            border: '1px solid rgba(255,255,255,0.05)', padding: 'var(--space-md)', height: '120px',
                            display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 'var(--space-md)', overflow: 'auto'
                        }}>
                            <div><div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '4px' }}>Driver</div><div style={{ fontSize: '0.9rem', fontWeight: 600 }}>{selectedDriver.name_acronym}</div></div>
                            <div><div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '4px' }}>Speed</div><div style={{ fontSize: '0.9rem', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{selectedDriver.speed || 0}</div></div>
                            <div><div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '4px' }}>Gear</div><div style={{ fontSize: '0.9rem', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{selectedDriver.gear || '—'}</div></div>
                            <div><div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '4px' }}>THR</div><div style={{ position: 'relative', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px' }}><div style={{ height: '100%', width: `${(selectedDriver.throttle || 0) * 100}%`, background: 'var(--status-green)' }} /></div></div>
                            <div><div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '4px' }}>BRK</div><div style={{ position: 'relative', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px' }}><div style={{ height: '100%', width: `${(selectedDriver.brake || 0) * 100}%`, background: 'var(--status-red)' }} /></div></div>
                            <div><div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '4px' }}>DRS</div><div style={{ width: '12px', height: '12px', borderRadius: '50%', background: selectedDriver.drs === 1 ? 'var(--status-green)' : 'var(--text-muted)' }} /></div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default LiveDashboard;
