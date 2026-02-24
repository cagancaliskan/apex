/**
 * TopBar Component
 * 
 * Compact header bar with session info, race stats,
 * flag status, and connection indicators.
 */

import { type FC, useMemo } from 'react';
import { Flag, Radio, WifiOff } from 'lucide-react';
import type { RaceState, DriverState } from '../types';

interface TopBarProps {
    raceState: RaceState;
    isConnected: boolean;
    onSpeedChange?: (speed: number) => void;
    currentSpeed?: number;
}

const SPEED_OPTIONS = [1, 5, 10, 20, 50];

const formatLapTime = (seconds?: number | null): string => {
    if (!seconds) return '--:--.---';
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(3);
    return mins > 0 ? `${mins}:${secs.padStart(6, '0')}` : secs;
};

const getDriversArray = (drivers: Record<number, DriverState> | DriverState[]): DriverState[] => {
    return Array.isArray(drivers) ? drivers : Object.values(drivers || {});
};

const TopBar: FC<TopBarProps> = ({
    raceState,
    isConnected,
    onSpeedChange,
    currentSpeed = 10
}) => {
    const stats = useMemo(() => {
        if (!raceState?.drivers) return null;
        const drivers = getDriversArray(raceState.drivers);
        const lapTimes = drivers
            .filter((d) => d.last_lap_time && d.last_lap_time > 0)
            .map((d) => d.last_lap_time!);

        const leader = drivers.find((d) => d.position === 1);
        const fastestLapTime = lapTimes.length > 0 ? Math.min(...lapTimes) : null;
        const fastestDriver = fastestLapTime
            ? drivers.find(d => d.last_lap_time === fastestLapTime)
            : null;

        return {
            leader,
            fastestLap: fastestLapTime,
            fastestDriver,
            totalDrivers: drivers.length,
        };
    }, [raceState]);

    const getFlagStatus = () => {
        const state = raceState as RaceState & {
            red_flag?: boolean;
            safety_car?: boolean;
            virtual_safety_car?: boolean;
            flags?: string[]
        };
        if (state.red_flag) return { label: 'RED FLAG', className: 'red' };
        if (state.safety_car) return { label: 'SAFETY CAR', className: 'sc' };
        if (state.virtual_safety_car) return { label: 'VSC', className: 'vsc' };
        if (state.flags?.includes('YELLOW')) return { label: 'YELLOW', className: 'yellow' };
        return { label: 'GREEN', className: 'green' };
    };

    const flagStatus = getFlagStatus();

    return (
        <header className="topbar">
            {/* Left: Session Info */}
            <div className="topbar-left">
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <div style={{
                        fontFamily: 'var(--font-sans)',
                        fontSize: '1rem',
                        fontWeight: 600,
                        color: 'var(--text-primary)'
                    }}>
                        {raceState.session_name || 'Race Session'}
                    </div>
                    <div style={{
                        fontSize: '0.7rem',
                        color: 'var(--text-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em'
                    }}>
                        {raceState.session_type || 'LIVE'}
                    </div>
                </div>
            </div>

            {/* Center: Stats */}
            <div className="topbar-center">
                {/* Lap Counter */}
                <div className="topbar-stat">
                    <span className="topbar-stat-label">Lap</span>
                    <div className="lap-display">
                        <span className="current">{raceState.current_lap || 0}</span>
                        <span className="separator">/</span>
                        <span className="total">{raceState.total_laps || '??'}</span>
                    </div>
                </div>

                {/* Leader */}
                <div className="topbar-stat">
                    <span className="topbar-stat-label">Leader</span>
                    <span className="topbar-stat-value accent">
                        {stats?.leader?.name_acronym || '---'}
                    </span>
                </div>

                {/* Fastest Lap */}
                <div className="topbar-stat">
                    <span className="topbar-stat-label">Fastest</span>
                    <span className="topbar-stat-value highlight">
                        {formatLapTime(stats?.fastestLap)}
                    </span>
                </div>

                {/* Drivers */}
                <div className="topbar-stat">
                    <span className="topbar-stat-label">Drivers</span>
                    <span className="topbar-stat-value">
                        {stats?.totalDrivers || 0}
                    </span>
                </div>
            </div>

            {/* Right: Status & Controls */}
            <div className="topbar-right">
                {/* Speed Control */}
                {onSpeedChange && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{
                            fontSize: '0.65rem',
                            color: 'var(--text-muted)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em'
                        }}>
                            Speed
                        </span>
                        <div style={{ display: 'flex', gap: '2px' }}>
                            {SPEED_OPTIONS.map((speed) => (
                                <button
                                    key={speed}
                                    onClick={() => onSpeedChange(speed)}
                                    style={{
                                        padding: '4px 8px',
                                        fontSize: '0.7rem',
                                        fontWeight: currentSpeed === speed ? 600 : 400,
                                        background: currentSpeed === speed
                                            ? 'var(--color-info)'
                                            : 'rgba(255, 255, 255, 0.05)',
                                        color: currentSpeed === speed
                                            ? 'var(--bg-primary)'
                                            : 'var(--text-secondary)',
                                        border: 'none',
                                        borderRadius: '4px',
                                        cursor: 'pointer',
                                        transition: 'all 0.15s ease'
                                    }}
                                >
                                    {speed}x
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Flag Status */}
                <div
                    className={`status-badge ${flagStatus.className}`}
                    style={{ padding: '4px 10px', fontSize: '0.7rem' }}
                >
                    <Flag size={10} />
                    <span style={{ marginLeft: '4px' }}>{flagStatus.label}</span>
                </div>

                {/* Connection Status */}
                <div
                    className={`status-badge ${isConnected ? 'green' : 'red'}`}
                    style={{ padding: '4px 10px', fontSize: '0.7rem' }}
                >
                    {isConnected ? (
                        <>
                            <Radio size={10} />
                            <span style={{ marginLeft: '4px' }}>LIVE</span>
                        </>
                    ) : (
                        <>
                            <WifiOff size={10} />
                            <span style={{ marginLeft: '4px' }}>OFFLINE</span>
                        </>
                    )}
                </div>
            </div>
        </header>
    );
};

export default TopBar;
