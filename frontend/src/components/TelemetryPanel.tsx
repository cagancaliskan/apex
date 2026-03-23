/**
 * Telemetry Panel Component — v2.1
 *
 * Real-time driver telemetry visualization.
 * Horizontal bar layout — no arc gauges, no glows.
 * Speed displayed as plain number. Compact mode for HUD strip.
 *
 * @module components/TelemetryPanel
 */

import type { FC } from 'react';
import type { DriverState } from '../types';
import styles from './TelemetryPanel.module.css';
import { DRS_ACTIVE_CODES, DRS_AVAILABLE_CODE } from '../config/constants';

// =============================================================================
// Types
// =============================================================================

interface DRSIndicatorProps {
    status: number;
    size?: 'small' | 'medium' | 'large';
}

interface TelemetryPanelProps {
    driver?: DriverState | null;
    compact?: boolean;
}

// =============================================================================
// Sub-Components
// =============================================================================

const DRSIndicator: FC<DRSIndicatorProps> = ({ status, size = 'medium' }) => {
    const isActive = DRS_ACTIVE_CODES.includes(status);
    const isAvailable = status === DRS_AVAILABLE_CODE;
    const dotSize = size === 'small' ? 7 : size === 'large' ? 14 : 10;
    const textSize = size === 'small' ? '0.6rem' : size === 'large' ? '0.8rem' : '0.7rem';

    const color = isActive ? 'var(--status-green)' : isAvailable ? 'var(--status-amber)' : 'var(--text-muted)';
    const label = isActive ? 'DRS' : isAvailable ? 'AVAIL' : 'DRS';

    return (
        <div className={styles.drsIndicator} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <div style={{ width: dotSize, height: dotSize, borderRadius: '50%', background: color }} />
            <span style={{ fontSize: textSize, color, fontWeight: 600, letterSpacing: '0.05em' }}>{label}</span>
        </div>
    );
};

// Horizontal bar for throttle/brake
interface HBarProps {
    value: number;
    color: string;
    label: string;
}

const HBar: FC<HBarProps> = ({ value, color, label }) => {
    const pct = Math.min(100, Math.max(0, value));
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, minWidth: '26px', letterSpacing: '0.04em' }}>{label}</span>
            <div className={styles.hBarTrack} style={{ flex: 1 }}>
                <div className={styles.hBarFill} style={{ width: `${pct}%`, background: color }} />
            </div>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-secondary)', minWidth: '32px', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                {Math.round(pct)}%
            </span>
        </div>
    );
};

// =============================================================================
// Main Component
// =============================================================================

const TelemetryPanel: FC<TelemetryPanelProps> = ({ driver, compact = false }) => {
    if (!driver) {
        return (
            <div className={`${styles.telemetryPanel} card`} style={{ padding: 'var(--space-md)', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Select a driver to view telemetry
            </div>
        );
    }

    const speed = driver.speed || 0;
    const gear = driver.gear || 0;
    const throttle = Math.min(100, Math.max(0, driver.throttle || 0) * 100);
    const brake = Math.min(100, Math.max(0, driver.brake || 0) * 100);
    const drs = driver.drs || 0;
    const teamColor = driver.team_colour ? `#${driver.team_colour}` : 'var(--color-info)';
    const gearDisplay = gear === 0 ? 'N' : gear === -1 ? 'R' : String(gear);

    if (compact) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '0 10px', height: '100%', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)', minWidth: '52px' }}>{Math.round(speed)} <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>km/h</span></span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.88rem', fontWeight: 700, color: 'var(--color-accent)', minWidth: '16px' }}>G{gearDisplay}</span>
                <DRSIndicator status={drs} size="small" />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', flex: 1, minWidth: 0 }}>
                    <HBar value={throttle} color="var(--status-green)" label="T" />
                    <HBar value={brake} color="var(--status-red)" label="B" />
                </div>
            </div>
        );
    }

    return (
        <div className={`${styles.telemetryPanel} card`} style={{ padding: 'var(--space-md)' }}>
            {/* Driver header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', paddingBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <div style={{ width: 3, height: 22, background: teamColor, borderRadius: 2, flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>{driver.name_acronym || `#${driver.driver_number}`}</div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{driver.team_name || '—'}</div>
                </div>
                <DRSIndicator status={drs} size="medium" />
            </div>

            {/* Speed + Gear row */}
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: '20px', marginBottom: '12px' }}>
                <div className={styles.speedReadout}>
                    <span className={styles.speedValue}>{Math.round(speed)}</span>
                    <span className={styles.speedUnit}>km/h</span>
                </div>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Gear</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.6rem', fontWeight: 700, color: 'var(--color-accent)', lineHeight: 1 }}>{gearDisplay}</div>
                </div>
            </div>

            {/* Throttle / Brake bars */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <HBar value={throttle} color="var(--status-green)" label="THR" />
                <HBar value={brake} color="var(--status-red)" label="BRK" />
            </div>

            {/* Sector Times */}
            {(driver.sector_1 != null || driver.sector_2 != null || driver.sector_3 != null) && (
                <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                    {(['sector_1', 'sector_2', 'sector_3'] as const).map((key, i) => {
                        const val = driver[key];
                        return (
                            <div key={key} style={{ flex: 1, textAlign: 'center' }}>
                                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' as const, marginBottom: '2px' }}>
                                    S{i + 1}
                                </div>
                                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: val != null ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                                    {val != null ? val.toFixed(3) : '—'}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export default TelemetryPanel;
// Keep named exports for backward compatibility with any ReplayPage/BacktestPage imports
export { DRSIndicator };
