/**
 * Live Dashboard — v2.1 Professional Race Engineering Interface
 *
 * 3-column layout: Leaderboard | Track+Telemetry | Strategy Console
 * State sourced from Zustand store (no local WebSocket).
 * Alert banner for SC, red flag, PIT_NOW, and undercut threats.
 *
 * @module pages/LiveDashboard
 */

import { useState, useEffect, useMemo, type FC } from 'react';
import TrackMap from '../components/TrackMap';
import StrategyPanel from '../components/StrategyPanel';
import { useRaceStore } from '../store/raceStore';
import { useAlerts } from '../hooks';
import type { DriverState } from '../types';
import styles from './LiveDashboard.module.css';

// =============================================================================
// Constants & Helpers
// =============================================================================

const TYRE_COLORS: Record<string, string> = {
    SOFT: '#ff0000',
    MEDIUM: '#ffd700',
    HARD: '#e8e8e8',
    INTERMEDIATE: '#39d353',
    WET: '#0080ff',
};

const TYRE_TEXT_COLORS: Record<string, string> = {
    SOFT: '#ffffff',
    MEDIUM: '#000000',
    HARD: '#000000',
    INTERMEDIATE: '#000000',
    WET: '#ffffff',
};

function fmtGap(gap: number | undefined | null): string {
    if (gap == null) return '—';
    if (gap === 0) return 'LEADER';
    return `+${gap.toFixed(3)}`;
}

function fmtLap(t: number | undefined | null): string {
    if (!t || t <= 0) return '—';
    const min = Math.floor(t / 60);
    const sec = (t % 60).toFixed(3);
    return min > 0 ? `${min}:${sec.padStart(6, '0')}` : sec;
}

function getRowUrgencyClass(d: DriverState, currentLap: number, s: typeof styles): string {
    if (d.pit_recommendation === 'PIT_NOW') return s.lbRowPitNow;
    if (d.undercut_threat) return s.lbRowThreat;
    if (
        d.pit_window_min && d.pit_window_min > 0 &&
        currentLap >= d.pit_window_min - 2 &&
        currentLap <= (d.pit_window_max ?? (d.pit_window_min + 5))
    ) return s.lbRowWindow;
    return '';
}

// =============================================================================
// Main Component
// =============================================================================

const LiveDashboard: FC = () => {
    // All data from Zustand store — no local WebSocket
    const sortedDrivers = useRaceStore(s => s.sortedDrivers);
    const selectedDriver = useRaceStore(s => s.selectedDriver);
    const selectDriver = useRaceStore(s => s.selectDriver);
    const currentLap = useRaceStore(s => s.currentLap);
    const totalLaps = useRaceStore(s => s.totalLaps);
    const raceControlMessages = useRaceStore(s => s.raceControlMessages);
    const trackConfig = useRaceStore(s => s.trackConfig);

    // Alert generation (state lives in raceStore, strip rendered in App.tsx)
    useAlerts();

    // Keyboard shortcut: 1-9 select driver by position
    useEffect(() => {
        const handleKey = (e: KeyboardEvent) => {
            if (e.target instanceof HTMLInputElement) return;
            const n = parseInt(e.key, 10);
            if (n >= 1 && n <= 9 && sortedDrivers[n - 1]) {
                selectDriver(sortedDrivers[n - 1].driver_number);
            }
            if (e.key === '0' && sortedDrivers[9]) {
                selectDriver(sortedDrivers[9].driver_number);
            }
        };
        window.addEventListener('keydown', handleKey);
        return () => window.removeEventListener('keydown', handleKey);
    }, [sortedDrivers, selectDriver]);

    // Auto-select leader on first load
    useEffect(() => {
        if (!selectedDriver && sortedDrivers.length > 0) {
            selectDriver(sortedDrivers[0].driver_number);
        }
    }, [sortedDrivers, selectedDriver, selectDriver]);

    // Sector delta calculation (vs session fastest per sector)
    const sectorBests = useMemo(() => {
        const s1 = Math.min(...sortedDrivers.map(d => d.sector_1 || Infinity).filter(v => v < Infinity));
        const s2 = Math.min(...sortedDrivers.map(d => d.sector_2 || Infinity).filter(v => v < Infinity));
        const s3 = Math.min(...sortedDrivers.map(d => d.sector_3 || Infinity).filter(v => v < Infinity));
        return { s1, s2, s3 };
    }, [sortedDrivers]);

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-primary)' }}>
            {/* 3-Column Grid */}
            <div className="dashboard-grid" style={{ flex: 1 }}>
                {/* Column 1: Leaderboard + Race Control */}
                <div className={styles.colLeaderboard}>
                    <Leaderboard
                        drivers={sortedDrivers}
                        selectedDriver={selectedDriver}
                        onSelect={selectDriver}
                        currentLap={currentLap}
                    />
                    <RaceControlPanel messages={raceControlMessages} />
                </div>

                {/* Column 2: Track Map + Telemetry HUD */}
                <div className={styles.colCenter}>
                    <div style={{ flex: 1, background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.05)', overflow: 'hidden', minHeight: 0 }}>
                        <TrackMap
                            drivers={sortedDrivers}
                            trackConfig={trackConfig}
                            selectedDriver={selectedDriver}
                            showDRS={true}
                        />
                    </div>
                    <TelemetryHUD driver={selectedDriver} sectorBests={sectorBests} />
                </div>

                {/* Column 3: Strategy Console */}
                <div className={styles.colStrategy}>
                    <div style={{ flex: 1, background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.05)', overflow: 'auto' }}>
                        <StrategyPanel
                            drivers={sortedDrivers}
                            selectedDriver={selectedDriver ?? undefined}
                            compact={false}
                            currentLap={currentLap}
                            totalLaps={totalLaps ?? undefined}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

// =============================================================================
// Leaderboard Sub-Component
// =============================================================================

interface LeaderboardProps {
    drivers: DriverState[];
    selectedDriver: DriverState | null;
    onSelect: (n: number | null) => void;
    currentLap: number;
}

const Leaderboard: FC<LeaderboardProps> = ({ drivers, selectedDriver, onSelect, currentLap }) => {
    const [showInt, setShowInt] = useState(false);

    return (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.05)', overflow: 'hidden', minHeight: 0 }}>
            {/* Header */}
            <div style={{ height: '24px', display: 'flex', alignItems: 'center', padding: '0 8px', gap: '6px', background: 'var(--bg-tertiary)', borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 }}>
                <span style={{ fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)', flex: 1 }}>Leaderboard</span>
                <button
                    onClick={() => setShowInt(v => !v)}
                    style={{ fontSize: '0.62rem', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--color-info)', background: 'rgba(88,166,255,0.1)', border: '1px solid rgba(88,166,255,0.2)', borderRadius: '2px', padding: '1px 6px', cursor: 'pointer', letterSpacing: '0.04em' }}
                >
                    {showInt ? 'INT' : 'GAP'}
                </button>
            </div>

            {/* Column headers */}
            <div style={{ height: '20px', display: 'grid', gridTemplateColumns: '22px 5px 44px 1fr 54px 28px 8px', gap: '4px', alignItems: 'center', padding: '0 6px', borderBottom: '1px solid rgba(255,255,255,0.04)', flexShrink: 0 }}>
                {['P', '', 'Driver', showInt ? 'INT' : 'GAP', 'Tyre', 'Lap', ''].map((h, i) => (
                    <div key={i} style={{ fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', textAlign: i === 3 ? 'right' : 'left', fontFamily: 'var(--font-mono)' }}>{h}</div>
                ))}
            </div>

            {/* Rows */}
            <div style={{ flex: 1, overflow: 'auto' }}>
                {drivers.map(d => {
                    const isSelected = selectedDriver?.driver_number === d.driver_number;
                    const teamColor = d.team_colour ? `#${d.team_colour}` : '#666';
                    const compound = d.compound || 'MEDIUM';
                    const tyreColor = TYRE_COLORS[compound] ?? '#fff';
                    const tyreTxtColor = TYRE_TEXT_COLORS[compound] ?? '#000';
                    const urgencyClass = getRowUrgencyClass(d, currentLap, styles);
                    const gapVal = showInt ? d.gap_to_ahead : d.gap_to_leader;
                    const posClass = d.position === 1 ? styles.posP1
                        : d.position === 2 ? styles.posP2
                        : d.position === 3 ? styles.posP3
                        : styles.posRest;
                    const gapDisplay = d.position === 1
                        ? 'LEADER'
                        : `▼ ${fmtGap(gapVal)}`;

                    return (
                        <div
                            key={d.driver_number}
                            onClick={() => onSelect(d.driver_number)}
                            className={[urgencyClass, isSelected ? styles.lbRowSelected : ''].filter(Boolean).join(' ')}
                            style={{
                                height: 'var(--row-height)',
                                display: 'grid',
                                gridTemplateColumns: '22px 5px 44px 1fr 54px 28px 8px',
                                gap: '4px',
                                alignItems: 'center',
                                padding: '0 6px',
                                cursor: 'pointer',
                                borderBottom: '1px solid rgba(255,255,255,0.025)',
                                transition: 'background 80ms',
                            }}
                        >
                            {/* Position */}
                            <div className={posClass} style={{ fontSize: '0.78rem', textAlign: 'center' }}>
                                {d.position || '—'}
                            </div>

                            {/* Team color bar */}
                            <div style={{ width: '3px', height: '16px', background: teamColor, borderRadius: '1px' }} />

                            {/* Driver name */}
                            <div style={{ fontWeight: 600, fontSize: '0.78rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {d.name_acronym || d.driver_number}
                            </div>

                            {/* Gap */}
                            <div
                                className={d.position !== 1 ? styles.gapLosing : undefined}
                                style={{ fontSize: '0.72rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: d.position === 1 ? 'var(--text-muted)' : undefined }}
                            >
                                {gapDisplay}
                            </div>

                            {/* Tyre badge + age */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                                <div style={{ width: '18px', height: '18px', borderRadius: '50%', background: tyreColor, color: tyreTxtColor, fontSize: '0.6rem', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                                    {compound[0]}
                                </div>
                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                                    {d.tyre_age ?? d.lap_in_stint ?? 0}
                                </span>
                            </div>

                            {/* Current lap */}
                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-tertiary)', textAlign: 'center' }}>
                                {d.current_lap || 0}
                            </div>

                            {/* Status: in-pit dot + undercut/overcut icons */}
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '2px' }}>
                                {d.in_pit && <div className={styles.inPitDot} />}
                                {d.undercut_threat && (
                                    <span title="Undercut threat" style={{ color: 'var(--status-amber)', fontSize: '0.75rem' }}>⬇</span>
                                )}
                                {d.overcut_opportunity && (
                                    <span title="Overcut opportunity" style={{ color: 'var(--status-green)', fontSize: '0.75rem' }}>⬆</span>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

// =============================================================================
// Race Control Panel
// =============================================================================

interface RaceControlProps {
    messages: Array<{ message: string; flag?: string | null; lap_number?: number | null }>;
}

const RaceControlPanel: FC<RaceControlProps> = ({ messages }) => (
    <div style={{ height: '108px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.05)', overflow: 'hidden', flexShrink: 0 }}>
        <div style={{ height: '22px', display: 'flex', alignItems: 'center', padding: '0 8px', background: 'var(--bg-tertiary)', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            <span style={{ fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)' }}>Race Control</span>
        </div>
        <div style={{ overflow: 'auto', height: 'calc(100% - 22px)', padding: '4px 8px' }}>
            {messages && messages.length > 0 ? (
                [...messages].reverse().slice(0, 8).map((msg, i) => (
                    <div key={i} style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', lineHeight: 1.4, padding: '1px 0', borderBottom: i < 7 ? '1px solid rgba(255,255,255,0.025)' : 'none' }}>
                        {msg.lap_number != null && (
                            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginRight: '6px', fontSize: '0.65rem' }}>
                                L{msg.lap_number}
                            </span>
                        )}
                        {msg.message}
                    </div>
                ))
            ) : (
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', padding: '4px 0' }}>No messages</div>
            )}
        </div>
    </div>
);

// =============================================================================
// Telemetry HUD Strip
// =============================================================================

interface TelemetryHUDProps {
    driver: DriverState | null;
    sectorBests: { s1: number; s2: number; s3: number };
}

const TelemetryHUD: FC<TelemetryHUDProps> = ({ driver, sectorBests }) => {
    if (!driver) return (
        <div style={{ height: '56px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.05)', flexShrink: 0 }} />
    );

    const thr = Math.min(100, Math.max(0, (driver.throttle || 0) * 100));
    const brk = Math.min(100, Math.max(0, (driver.brake || 0) * 100));
    const drsActive = [10, 12, 14].includes(driver.drs || 0);
    const drsAvail = driver.drs === 8;

    const sectorDelta = (val: number | null | undefined, best: number): { delta: string; cls: string } => {
        if (!val || !isFinite(best)) return { delta: '—', cls: styles.noData };
        const diff = val - best;
        if (Math.abs(diff) < 0.001) return { delta: fmtLap(val), cls: styles.faster };
        return {
            delta: `${diff > 0 ? '+' : ''}${diff.toFixed(3)}`,
            cls: diff < 0 ? styles.faster : diff < 0.3 ? styles.slower : styles.muchSlower
        };
    };

    const s1 = sectorDelta(driver.sector_1, sectorBests.s1);
    const s2 = sectorDelta(driver.sector_2, sectorBests.s2);
    const s3 = sectorDelta(driver.sector_3, sectorBests.s3);

    return (
        <div style={{ height: '56px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.05)', padding: '0 10px', flexShrink: 0, display: 'flex', alignItems: 'center', gap: '14px', overflow: 'hidden' }}>
            {/* Driver name */}
            <div style={{ fontWeight: 600, fontSize: '0.78rem', color: 'var(--text-secondary)', flexShrink: 0, fontFamily: 'var(--font-mono)' }}>
                {driver.name_acronym}
            </div>

            <div style={{ width: '1px', height: '24px', background: 'rgba(255,255,255,0.1)', flexShrink: 0 }} />

            {/* Speed */}
            <div className={styles.speedReadout} style={{ flexShrink: 0 }}>
                <span className={styles.speedValue} style={{ fontSize: '1.3rem' }}>{Math.round(driver.speed || 0)}</span>
                <span className={styles.speedUnit}>km/h</span>
            </div>

            {/* Gear */}
            <div style={{ flexShrink: 0, textAlign: 'center' }}>
                <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>G</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '1rem', color: 'var(--color-info)', lineHeight: 1 }}>
                    {driver.gear || '—'}
                </div>
            </div>

            <div style={{ width: '1px', height: '24px', background: 'rgba(255,255,255,0.1)', flexShrink: 0 }} />

            {/* Throttle */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, flexShrink: 0 }}>THR</span>
                <div className={styles.hBarTrack} style={{ flex: 1 }}>
                    <div className={`${styles.hBarFill} ${styles.throttle}`} style={{ width: `${thr}%` }} />
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-secondary)', flexShrink: 0, minWidth: '26px', textAlign: 'right' }}>{Math.round(thr)}%</span>
            </div>

            {/* Brake */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, flexShrink: 0 }}>BRK</span>
                <div className={styles.hBarTrack} style={{ flex: 1 }}>
                    <div className={`${styles.hBarFill} ${styles.brake}`} style={{ width: `${brk}%` }} />
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-secondary)', flexShrink: 0, minWidth: '26px', textAlign: 'right' }}>{Math.round(brk)}%</span>
            </div>

            {/* DRS */}
            <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: '4px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: drsActive ? 'var(--status-green)' : drsAvail ? 'var(--status-amber)' : 'var(--text-muted)' }} />
                <span style={{ fontSize: '0.6rem', color: drsActive ? 'var(--status-green)' : drsAvail ? 'var(--status-amber)' : 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                    {drsActive ? 'DRS' : drsAvail ? 'AVAIL' : 'DRS'}
                </span>
            </div>

            <div style={{ width: '1px', height: '24px', background: 'rgba(255,255,255,0.1)', flexShrink: 0 }} />

            {/* Sector deltas */}
            <div style={{ display: 'flex', gap: '10px', flexShrink: 0 }}>
                {[['S1', s1], ['S2', s2], ['S3', s3]].map(([label, sec]) => {
                    const { delta, cls } = sec as { delta: string; cls: string };
                    return (
                        <div key={label as string} style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label as string}</div>
                            <div className={`${styles.sectorDelta} ${cls}`} style={{ fontSize: '0.68rem' }}>{delta}</div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default LiveDashboard;
