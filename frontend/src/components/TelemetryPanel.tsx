/**
 * Telemetry Panel Component
 *
 * Real-time driver telemetry visualization.
 * Displays speed, gear, throttle/brake bars, and DRS status.
 *
 * @module components/TelemetryPanel
 */

import type { FC } from 'react';
import type { DriverState } from '../types';

// =============================================================================
// Types
// =============================================================================

interface DRSIndicatorProps {
    status: number;
    size?: 'small' | 'medium' | 'large';
}

interface VerticalBarProps {
    value: number;
    maxValue?: number;
    color: string;
    label: string;
    height?: number;
}

interface SpeedGaugeProps {
    speed: number;
    maxSpeed?: number;
}

interface GearIndicatorProps {
    gear: number;
}

interface TelemetryPanelProps {
    driver?: DriverState | null;
    compact?: boolean;
}

// =============================================================================
// Sub-Components
// =============================================================================

const DRSIndicator: FC<DRSIndicatorProps> = ({ status, size = 'medium' }) => {
    const isActive = [10, 12, 14].includes(status);
    const isAvailable = status === 8;

    const sizeClasses = { small: { dot: 8, text: '0.65rem' }, medium: { dot: 12, text: '0.75rem' }, large: { dot: 16, text: '0.875rem' } };
    const { dot, text } = sizeClasses[size];

    let color = 'var(--text-muted)', label = 'OFF', glow = 'none';
    if (isActive) { color = 'var(--accent-green)'; label = 'DRS'; glow = '0 0 8px var(--accent-green)'; }
    else if (isAvailable) { color = 'var(--accent-yellow)'; label = 'AVAIL'; glow = '0 0 5px var(--accent-yellow)'; }

    return (
        <div className="drs-indicator" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ width: dot, height: dot, borderRadius: '50%', backgroundColor: color, boxShadow: glow, transition: 'all 0.15s ease' }} />
            <span style={{ fontSize: text, color, fontWeight: 600, letterSpacing: '0.05em' }}>{label}</span>
        </div>
    );
};

const VerticalBar: FC<VerticalBarProps> = ({ value, maxValue = 100, color, label, height = 100 }) => {
    const percentage = Math.min(100, Math.max(0, (value / maxValue) * 100));
    return (
        <div className="vertical-bar" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>{label}</span>
            <div style={{ width: 24, height, backgroundColor: 'var(--bg-tertiary)', borderRadius: 4, overflow: 'hidden', position: 'relative' }}>
                <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: `${percentage}%`, backgroundColor: color, transition: 'height 0.1s ease', borderRadius: 4 }} />
            </div>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>{Math.round(value)}%</span>
        </div>
    );
};

const SpeedGauge: FC<SpeedGaugeProps> = ({ speed, maxSpeed = 360 }) => {
    const percentage = Math.min(100, (speed / maxSpeed) * 100);
    return (
        <div className="speed-gauge" style={{ position: 'relative', width: 120, height: 80 }}>
            <svg viewBox="0 0 100 60" style={{ width: '100%', height: '100%' }}>
                <path d="M 10 55 A 40 40 0 0 1 90 55" fill="none" stroke="var(--bg-tertiary)" strokeWidth="8" strokeLinecap="round" />
                <path d="M 10 55 A 40 40 0 0 1 90 55" fill="none" stroke="url(#speedGradient)" strokeWidth="8" strokeLinecap="round" strokeDasharray="126" strokeDashoffset={126 - (126 * percentage) / 100} style={{ transition: 'stroke-dashoffset 0.1s ease' }} />
                <defs>
                    <linearGradient id="speedGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="var(--accent-cyan)" />
                        <stop offset="100%" stopColor="var(--accent-magenta)" />
                    </linearGradient>
                </defs>
            </svg>
            <div style={{ position: 'absolute', bottom: 0, left: '50%', transform: 'translateX(-50%)', textAlign: 'center' }}>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1 }}>{Math.round(speed)}</div>
                <div style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', marginTop: 2 }}>km/h</div>
            </div>
        </div>
    );
};

const GearIndicator: FC<GearIndicatorProps> = ({ gear }) => {
    const gearDisplay = gear === 0 ? 'N' : gear === -1 ? 'R' : gear;
    return (
        <div className="gear-indicator" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', width: '60px' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Gear</span>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '2.5rem', fontWeight: 700, color: 'var(--accent-cyan)', lineHeight: 1, textShadow: '0 0 10px rgba(6, 249, 249, 0.3)' }}>{gearDisplay}</div>
        </div>
    );
};

// =============================================================================
// Main Component
// =============================================================================

const TelemetryPanel: FC<TelemetryPanelProps> = ({ driver, compact = false }) => {
    if (!driver) {
        return (
            <div className="telemetry-panel card" style={{ padding: 'var(--space-lg)', textAlign: 'center' }}>
                <p className="text-muted">Select a driver to view telemetry</p>
            </div>
        );
    }

    const { speed = 0, gear = 0, throttle = 0, brake = 0, drs = 0 } = driver;
    const normalizedBrake = brake > 1 ? brake : brake * 100;

    if (compact) {
        return (
            <div className="telemetry-panel-compact" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)', padding: 'var(--space-sm) var(--space-md)', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', height: '100%' }}>
                <span style={{ fontFamily: 'var(--font-display)', fontSize: '0.9rem' }}>{Math.round(speed)} km/h</span>
                <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>G{gear}</span>
                <DRSIndicator status={drs} size="small" />
                <div style={{ display: 'flex', gap: '4px', height: 20, alignItems: 'flex-end' }}>
                    <div style={{ width: 6, height: 20, background: 'var(--bg-card)', borderRadius: 2, overflow: 'hidden', position: 'relative' }}>
                        <div style={{ width: '100%', height: `${Math.min(100, throttle)}%`, background: 'var(--accent-green)', position: 'absolute', bottom: 0, left: 0 }} />
                    </div>
                    <div style={{ width: 6, height: 20, background: 'var(--bg-card)', borderRadius: 2, overflow: 'hidden', position: 'relative' }}>
                        <div style={{ width: '100%', height: `${Math.min(100, normalizedBrake)}%`, background: 'var(--status-red)', position: 'absolute', bottom: 0, left: 0 }} />
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="telemetry-panel card card-glow">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-md)', paddingBottom: 'var(--space-sm)', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                    <div style={{ width: 4, height: 24, backgroundColor: driver.team_colour ? `#${driver.team_colour}` : 'var(--accent-cyan)', borderRadius: 2 }} />
                    <div>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{driver.name_acronym || `#${driver.driver_number}`}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>{driver.team_name || 'Unknown Team'}</div>
                    </div>
                </div>
                <DRSIndicator status={drs} size="medium" />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto auto auto', gap: 'var(--space-lg)', alignItems: 'center' }}>
                <SpeedGauge speed={speed} />
                <GearIndicator gear={gear} />
                <VerticalBar value={throttle} color="var(--accent-green)" label="THR" height={80} />
                <VerticalBar value={normalizedBrake} color="var(--status-red)" label="BRK" height={80} />
            </div>
        </div>
    );
};

export default TelemetryPanel;
export { DRSIndicator, VerticalBar, SpeedGauge, GearIndicator };
