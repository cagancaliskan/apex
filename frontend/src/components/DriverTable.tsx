/**
 * Driver Table Component
 *
 * Displays live race standings with telemetry, timing, and strategy data.
 * Supports both compact (mobile) and full (desktop) layouts.
 *
 * @module components/DriverTable
 */

import { useMemo, type FC, type CSSProperties } from 'react';
import type { DriverState } from '../types';
import { formatLapTime, formatGap, getTyreLabel, getTyreClass } from '../utils';

// =============================================================================
// Types
// =============================================================================

interface DriverTableProps {
    /** Array of driver states sorted by position */
    drivers: DriverState[];
    /** Fastest lap time in session (for purple highlighting) */
    fastestLap?: number | null;
    /** Callback when driver row is clicked */
    onDriverSelect?: (driver: DriverState) => void;
    /** Currently selected driver for highlighting */
    selectedDriver?: DriverState | null;
    /** Use compact layout for narrow viewports */
    compact?: boolean;
}

interface DegradationDisplay {
    text: string;
    color: string;
}

interface CliffRiskDisplay {
    width: number;
    color: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format degradation slope with severity-based color coding.
 *
 * @param slope - Degradation slope in seconds per lap
 * @returns Display object with formatted text and CSS color
 */
function formatDegSlope(slope: number | undefined): DegradationDisplay {
    if (!slope || slope === 0) {
        return { text: '-', color: 'var(--text-muted)' };
    }

    const text = `${(slope * 1000).toFixed(0)}ms`;
    let color = 'var(--status-green)';

    if (slope > 0.05) color = 'var(--status-yellow)';
    if (slope > 0.08) color = 'var(--accent-orange)';
    if (slope > 0.10) color = 'var(--status-red)';

    return { text, color };
}

/**
 * Format cliff risk as visual progress indicator.
 *
 * @param risk - Cliff risk probability (0-1)
 * @returns Display object with width percentage and color, or null if no risk
 */
function formatCliffRisk(risk: number | undefined): CliffRiskDisplay | null {
    if (!risk || risk === 0) return null;

    const width = Math.min(100, Math.round(risk * 100));
    let color = 'var(--status-green)';

    if (risk > 0.5) color = 'var(--status-yellow)';
    if (risk > 0.8) color = 'var(--status-red)';

    return { width, color };
}

/**
 * Determine DRS display state from numeric value.
 *
 * @param drs - DRS status code from telemetry
 * @returns CSS class name for DRS indicator
 */
function getDrsState(drs: number): 'active' | 'available' | 'off' {
    if ([10, 12, 14].includes(drs)) return 'active';
    if (drs === 8) return 'available';
    return 'off';
}

// =============================================================================
// Component
// =============================================================================

/**
 * Driver standings table with live telemetry and timing data.
 *
 * Features:
 * - Live position updates with team colors
 * - Real-time speed, gear, DRS, throttle/brake
 * - Gap to leader and interval timing
 * - Tyre compound and age tracking
 * - Degradation and cliff risk indicators
 * - Predicted pace display
 *
 * @example
 * ```tsx
 * <DriverTable
 *   drivers={sortedDrivers}
 *   onDriverSelect={handleSelect}
 *   selectedDriver={selected}
 * />
 * ```
 */
const DriverTable: FC<DriverTableProps> = ({
    drivers,
    fastestLap: _fastestLap,
    onDriverSelect,
    selectedDriver,
    compact = false,
}) => {
    // Calculate fastest lap for purple highlighting
    const fastestLapTime = useMemo(() => {
        if (!drivers || drivers.length === 0) return null;
        const times = drivers
            .map((d) => d.last_lap_time)
            .filter((t): t is number => t !== null && t !== undefined && t > 0);
        return times.length > 0 ? Math.min(...times) : null;
    }, [drivers]);

    // Empty state
    if (!drivers || drivers.length === 0) {
        return (
            <div className="card" style={{ textAlign: 'center', padding: 'var(--space-xl)' }}>
                <p className="text-muted">No driver data available</p>
            </div>
        );
    }

    // Compact layout for mobile/narrow views
    if (compact) {
        return <CompactTable drivers={drivers} selectedDriver={selectedDriver} onDriverSelect={onDriverSelect} />;
    }

    return (
        <div className="card" style={{ overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto' }}>
                <table className="driver-table">
                    <thead>
                        <tr>
                            <th style={{ width: '50px' }}>Pos</th>
                            <th>Driver</th>
                            <th style={{ width: '60px' }}>Speed</th>
                            <th style={{ width: '40px' }}>Gear</th>
                            <th style={{ width: '45px' }}>DRS</th>
                            <th style={{ width: '40px' }}>THR/BRK</th>
                            <th style={{ width: '90px' }}>Gap</th>
                            <th style={{ width: '100px' }}>Last Lap</th>
                            <th style={{ width: '80px' }}>Tyre</th>
                            <th style={{ width: '70px' }}>Deg</th>
                            <th style={{ width: '100px' }}>Pred +5</th>
                            <th style={{ width: '60px' }}>Risk</th>
                        </tr>
                    </thead>
                    <tbody>
                        {drivers.map((driver, index) => (
                            <DriverRow
                                key={driver.driver_number}
                                driver={driver}
                                index={index}
                                fastestLapTime={fastestLapTime}
                                isSelected={selectedDriver?.driver_number === driver.driver_number}
                                onSelect={onDriverSelect}
                            />
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

// =============================================================================
// Sub-components
// =============================================================================

interface DriverRowProps {
    driver: DriverState;
    index: number;
    fastestLapTime: number | null;
    isSelected: boolean;
    onSelect?: (driver: DriverState) => void;
}

/**
 * Individual driver row with full telemetry display.
 */
const DriverRow: FC<DriverRowProps> = ({ driver, index, fastestLapTime, isSelected, onSelect }) => {
    const isPersonalBest = driver.last_lap_time && driver.best_lap_time && driver.last_lap_time === driver.best_lap_time;
    const isFastestLap = driver.last_lap_time === fastestLapTime;
    const deg = formatDegSlope(driver.deg_slope);
    const cliff = formatCliffRisk(driver.cliff_risk);
    const drsState = getDrsState(driver.drs || 0);

    const rowStyle: CSSProperties = {
        animationDelay: `${index * 30}ms`,
        backgroundColor: isSelected ? 'rgba(255, 255, 255, 0.05)' : undefined,
        cursor: 'pointer',
    };

    return (
        <tr onClick={() => onSelect?.(driver)} style={rowStyle} className={isSelected ? 'selected' : ''}>
            <td className="position-cell">{driver.position}</td>
            <td>
                <div className="driver-cell">
                    <div className="team-color" style={{ backgroundColor: `#${driver.team_colour || 'FFFFFF'}` }} />
                    <div>
                        <div className="driver-name">{driver.name_acronym || `#${driver.driver_number}`}</div>
                        <div className="driver-team">{driver.team_name || 'Unknown'}</div>
                    </div>
                </div>
            </td>
            <td className="speed-cell telemetry-cell">{driver.speed ? `${Math.round(driver.speed)}` : '-'}</td>
            <td className="gear-cell telemetry-cell">{driver.gear !== undefined ? `G${driver.gear}` : '-'}</td>
            <td className="telemetry-cell">
                <div className={`mini-drs ${drsState}`} title={`DRS ${drsState.charAt(0).toUpperCase() + drsState.slice(1)}`} />
            </td>
            <td className="telemetry-cell">
                <div className="mini-bars">
                    <div className="mini-bar">
                        <div className="mini-bar-fill throttle" style={{ height: `${driver.throttle || 0}%` }} />
                    </div>
                    <div className="mini-bar">
                        <div
                            className="mini-bar-fill brake"
                            style={{ height: `${driver.brake > 1 ? driver.brake : (driver.brake || 0) * 100}%` }}
                        />
                    </div>
                </div>
            </td>
            <td className="gap-cell">
                {driver.position === 1 ? (
                    <span style={{ color: 'var(--accent-cyan)' }}>LEADER</span>
                ) : (
                    formatGap(driver.gap_to_leader)
                )}
            </td>
            <td className={`lap-time-cell ${isFastestLap ? 'best' : isPersonalBest ? 'personal-best' : ''}`}>
                {formatLapTime(driver.last_lap_time)}
            </td>
            <td>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
                    <span className={`tyre-badge ${getTyreClass(driver.compound)}`}>{getTyreLabel(driver.compound)}</span>
                    <span className="tyre-age">L{driver.lap_in_stint || driver.tyre_age || 0}</span>
                </div>
            </td>
            <td style={{ fontFamily: 'var(--font-display)', fontSize: '0.8rem', color: deg.color }}>{deg.text}</td>
            <td className="lap-time-cell" style={{ opacity: 0.8 }}>
                -
            </td>
            <td>
                {cliff ? (
                    <div
                        style={{
                            width: '40px',
                            height: '6px',
                            background: 'var(--bg-tertiary)',
                            borderRadius: '3px',
                            overflow: 'hidden',
                        }}
                    >
                        <div
                            style={{
                                width: `${cliff.width}%`,
                                height: '100%',
                                background: cliff.color,
                                transition: 'width 0.3s ease',
                            }}
                        />
                    </div>
                ) : (
                    <span className="text-muted">-</span>
                )}
            </td>
        </tr>
    );
};

interface CompactTableProps {
    drivers: DriverState[];
    selectedDriver?: DriverState | null;
    onDriverSelect?: (driver: DriverState) => void;
}

/**
 * Compact table layout for mobile and narrow viewports.
 */
const CompactTable: FC<CompactTableProps> = ({ drivers, selectedDriver, onDriverSelect }) => (
    <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
        <div style={{ overflowX: 'auto' }}>
            <table className="driver-table compact">
                <thead>
                    <tr>
                        <th style={{ width: '35px' }}>P</th>
                        <th>Driver</th>
                        <th style={{ width: '70px' }}>Gap</th>
                        <th style={{ width: '50px' }}>Spd</th>
                        <th style={{ width: '50px' }}>Tyre</th>
                    </tr>
                </thead>
                <tbody>
                    {drivers.map((driver) => {
                        const isSelected = selectedDriver?.driver_number === driver.driver_number;
                        const gapDisplay =
                            driver.position === 0 || driver.position === null
                                ? 'DNF'
                                : driver.position === 1
                                    ? 'LEADER'
                                    : driver.gap_to_leader && driver.gap_to_leader > 0
                                        ? `+${driver.gap_to_leader.toFixed(3)}`
                                        : '+0.000';

                        return (
                            <tr
                                key={driver.driver_number}
                                style={{
                                    backgroundColor: isSelected ? 'rgba(255, 255, 255, 0.08)' : undefined,
                                    cursor: 'pointer',
                                }}
                                onClick={() => onDriverSelect?.(driver)}
                            >
                                <td style={{ fontWeight: 600, fontSize: '0.85rem' }}>{driver.position}</td>
                                <td>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <div
                                            style={{
                                                width: '3px',
                                                height: '16px',
                                                borderRadius: '1px',
                                                backgroundColor: `#${driver.team_colour || 'FFFFFF'}`,
                                            }}
                                        />
                                        <span style={{ fontFamily: 'var(--font-display)', fontSize: '0.8rem', fontWeight: 500 }}>
                                            {driver.name_acronym || `#${driver.driver_number}`}
                                        </span>
                                    </div>
                                </td>
                                <td
                                    style={{
                                        fontSize: '0.75rem',
                                        color:
                                            driver.position === 1
                                                ? 'var(--accent-cyan)'
                                                : driver.position === 0
                                                    ? 'var(--text-muted)'
                                                    : 'var(--text-secondary)',
                                    }}
                                >
                                    {gapDisplay}
                                </td>
                                <td
                                    style={{
                                        fontSize: '0.75rem',
                                        fontFamily: 'var(--font-display)',
                                        color: driver.speed > 300 ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                                    }}
                                >
                                    {driver.speed ? Math.round(driver.speed) : '-'}
                                </td>
                                <td>
                                    <span
                                        className={`tyre-badge ${getTyreClass(driver.compound)}`}
                                        style={{ fontSize: '0.65rem', padding: '2px 5px' }}
                                    >
                                        {getTyreLabel(driver.compound)}
                                        {driver.lap_in_stint || driver.tyre_age || 0}
                                    </span>
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    </div>
);

export default DriverTable;
