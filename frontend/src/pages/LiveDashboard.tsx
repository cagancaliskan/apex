/**
 * Live Dashboard Page
 *
 * Compact 2-panel race monitoring view:
 * - Left: Leaderboard + Weather
 * - Right: Track visualization + driver details
 *
 * @module pages/LiveDashboard
 */

import { useMemo, useState, type FC } from 'react';
import { Flag, Radio, ChevronDown } from 'lucide-react';
import DriverTable from '../components/DriverTable';
import StrategyPanel from '../components/StrategyPanel';
import TelemetryPanel from '../components/TelemetryPanel';
import TrackMap from '../components/TrackMap';
import WeatherWidget from '../components/WeatherWidget';
import type { RaceState, DriverState } from '../types';

// =============================================================================
// Types
// =============================================================================

interface Circuit {
    year: number;
    round: number;
    name: string;
    country: string;
}

interface SpeedOption {
    value: number;
    label: string;
}

interface LiveDashboardProps {
    raceState: RaceState;
    isPolling: boolean;
}

interface FlagStatus {
    label: string;
    className: string;
}

// =============================================================================
// Constants
// =============================================================================

const CIRCUITS: Circuit[] = [
    { year: 2023, round: 22, name: 'Abu Dhabi', country: 'UAE' },
    { year: 2023, round: 6, name: 'Monaco', country: 'Monaco' },
    { year: 2023, round: 10, name: 'Silverstone', country: 'UK' },
    { year: 2023, round: 14, name: 'Spa-Francorchamps', country: 'Belgium' },
    { year: 2023, round: 15, name: 'Monza', country: 'Italy' },
];

const SPEED_OPTIONS: SpeedOption[] = [
    { value: 1, label: '1x (Real-time)' },
    { value: 5, label: '5x' },
    { value: 10, label: '10x' },
    { value: 20, label: '20x' },
    { value: 50, label: '50x' },
];

// =============================================================================
// Helper Functions
// =============================================================================

const formatLapTime = (seconds?: number | null): string => {
    if (!seconds) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(3);
    return mins > 0 ? `${mins}:${secs.padStart(6, '0')}` : secs;
};

const getDriversArray = (drivers: Record<number, DriverState> | DriverState[]): DriverState[] => {
    return Array.isArray(drivers) ? drivers : Object.values(drivers || {});
};

// =============================================================================
// Component
// =============================================================================

const LiveDashboard: FC<LiveDashboardProps> = ({ raceState, isPolling }) => {
    const [selectedDriver, setSelectedDriver] = useState<DriverState | null>(null);
    const [selectedCircuit, setSelectedCircuit] = useState<Circuit>(CIRCUITS[0]);
    const [showCircuitDropdown, setShowCircuitDropdown] = useState(false);
    const [speedMultiplier, setSpeedMultiplier] = useState(10);

    const handleSpeedChange = async (speed: number) => {
        try {
            await fetch(`/api/simulation/speed/${speed}`, { method: 'POST' });
            setSpeedMultiplier(speed);
        } catch (error) {
            console.error('Failed to set speed:', error);
        }
    };

    const stats = useMemo(() => {
        if (!raceState?.drivers) return null;
        const drivers = getDriversArray(raceState.drivers);
        const lapTimes = drivers.filter((d) => d.last_lap_time && d.last_lap_time > 0).map((d) => d.last_lap_time!);
        return {
            leader: drivers.find((d) => d.position === 1),
            fastestLap: lapTimes.length > 0 ? Math.min(...lapTimes) : null,
        };
    }, [raceState]);

    const currentSelectedDriver = useMemo(() => {
        if (!selectedDriver || !raceState?.drivers) return null;
        const drivers = getDriversArray(raceState.drivers);
        return drivers.find((d) => d.driver_number === selectedDriver.driver_number) || selectedDriver;
    }, [selectedDriver, raceState?.drivers]);

    const getFlagStatus = (): FlagStatus => {
        const state = raceState as RaceState & { red_flag?: boolean; safety_car?: boolean; virtual_safety_car?: boolean; flags?: string[] };
        if (state.red_flag) return { label: 'RED FLAG', className: 'red' };
        if (state.safety_car) return { label: 'SAFETY CAR', className: 'sc' };
        if (state.virtual_safety_car) return { label: 'VSC', className: 'vsc' };
        if (state.flags?.includes('YELLOW')) return { label: 'YELLOW', className: 'yellow' };
        return { label: 'GREEN', className: 'green' };
    };

    const flagStatus = getFlagStatus();
    const driversArray = getDriversArray(raceState.drivers);

    return (
        <div className="live-dashboard animate-fade-in" style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Header Bar */}
            <header className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--space-sm) var(--space-md)', background: 'var(--bg-secondary)', borderBottom: '1px solid rgba(255,255,255,0.05)', flexShrink: 0 }}>
                {/* Circuit Selector */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-lg)' }}>
                    <div style={{ position: 'relative' }}>
                        <button onClick={() => setShowCircuitDropdown(!showCircuitDropdown)} style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 'var(--radius-sm)', padding: 'var(--space-xs) var(--space-sm)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
                            <div style={{ textAlign: 'left' }}>
                                <div style={{ fontSize: '0.9rem', fontWeight: 600, fontFamily: 'var(--font-display)', color: 'var(--text-primary)' }}>{selectedCircuit.name}</div>
                                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>{selectedCircuit.year} • {selectedCircuit.country}</div>
                            </div>
                            <ChevronDown size={14} color="var(--text-muted)" />
                        </button>
                        {showCircuitDropdown && (
                            <div style={{ position: 'absolute', top: '100%', left: 0, marginTop: '4px', background: 'var(--bg-secondary)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 'var(--radius-sm)', zIndex: 100, minWidth: '180px', boxShadow: '0 4px 12px rgba(0,0,0,0.4)' }}>
                                {CIRCUITS.map((circuit) => (
                                    <button key={`${circuit.year}-${circuit.round}`} onClick={() => { setSelectedCircuit(circuit); setShowCircuitDropdown(false); }} style={{ display: 'block', width: '100%', padding: 'var(--space-sm)', background: selectedCircuit.round === circuit.round ? 'rgba(0, 212, 190, 0.1)' : 'transparent', border: 'none', textAlign: 'left', cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                        <div style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--text-primary)' }}>{circuit.name}</div>
                                        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>{circuit.country}</div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Stats */}
                <div style={{ display: 'flex', gap: 'var(--space-xl)', alignItems: 'center' }}>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Leader</div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'var(--font-display)', color: 'var(--accent-cyan)' }}>{stats?.leader?.name_acronym || '-'}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Fastest Lap</div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'var(--font-display)', color: 'var(--accent-magenta)' }}>{formatLapTime(stats?.fastestLap)}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Lap</div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'var(--font-display)' }}>
                            <span style={{ color: 'var(--text-primary)' }}>{raceState.current_lap || 0}</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>/{raceState.total_laps || '?'}</span>
                        </div>
                    </div>
                </div>

                {/* Speed Control */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Speed</span>
                    <div style={{ display: 'flex', gap: '2px' }}>
                        {SPEED_OPTIONS.map((option) => (
                            <button key={option.value} onClick={() => handleSpeedChange(option.value)} style={{ padding: '4px 8px', fontSize: '0.7rem', fontWeight: speedMultiplier === option.value ? 700 : 400, background: speedMultiplier === option.value ? 'var(--accent-cyan)' : 'rgba(255,255,255,0.05)', color: speedMultiplier === option.value ? 'var(--bg-primary)' : 'var(--text-secondary)', border: 'none', borderRadius: 'var(--radius-xs)', cursor: 'pointer', transition: 'all 0.15s ease' }}>
                                {option.value}x
                            </button>
                        ))}
                    </div>
                </div>

                {/* Status */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
                    <div className={`status-badge ${flagStatus.className}`} style={{ padding: '4px 10px', fontSize: '0.7rem' }}>
                        <Flag size={10} /> {flagStatus.label}
                    </div>
                    {isPolling && (
                        <div className="status-badge green" style={{ padding: '4px 10px', fontSize: '0.7rem', animation: 'pulse 2s infinite' }}>
                            <Radio size={10} /> LIVE
                        </div>
                    )}
                </div>
            </header>

            {/* Main 2-Panel Layout */}
            <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '360px 1fr', gap: 'var(--space-md)', padding: 'var(--space-md)', minHeight: 0, overflow: 'hidden' }}>
                {/* Left Panel */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', minHeight: 0, overflow: 'hidden' }}>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', letterSpacing: '0.1em', textTransform: 'uppercase', paddingLeft: 'var(--space-sm)', flexShrink: 0 }}>Leaderboard</div>
                    <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
                        <DriverTable drivers={driversArray} fastestLap={stats?.fastestLap} onDriverSelect={setSelectedDriver} selectedDriver={selectedDriver} compact />
                    </div>
                    <div style={{ flexShrink: 0 }}>
                        <WeatherWidget weather={raceState.weather} compact />
                    </div>
                </div>

                {/* Right Panel */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', minHeight: 0, overflow: 'hidden' }}>
                    <div style={{ flex: 1, minHeight: '200px', overflow: 'hidden' }}>
                        <TrackMap
                            drivers={driversArray}
                            trackConfig={raceState.track_config}
                            selectedDriver={selectedDriver}
                            onDriverSelect={setSelectedDriver}
                            trackStatus={raceState.track_status || 'GREEN'}
                        />
                    </div>
                    <div style={{ flexShrink: 0, height: currentSelectedDriver ? '450px' : '50px', transition: 'height 0.2s ease' }}>
                        {currentSelectedDriver ? (
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)', height: '100%' }}>
                                <TelemetryPanel driver={currentSelectedDriver} compact={false} />
                                <StrategyPanel drivers={driversArray} selectedDriver={currentSelectedDriver} compact={false} />
                            </div>
                        ) : (
                            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', border: '1px dashed rgba(255,255,255,0.1)', borderRadius: 'var(--radius-md)' }}>
                                Click on a driver to view telemetry and strategy
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Progress Bar */}
            <div style={{ flexShrink: 0, height: '4px', background: 'var(--bg-tertiary)' }}>
                <div style={{ height: '100%', width: `${((raceState.current_lap || 0) / (raceState.total_laps || 1)) * 100}%`, background: 'linear-gradient(90deg, var(--accent-cyan), var(--accent-magenta))', transition: 'width 0.5s ease' }} />
            </div>
        </div>
    );
};

export default LiveDashboard;
