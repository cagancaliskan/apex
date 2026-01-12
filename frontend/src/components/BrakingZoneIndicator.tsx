/**
 * Braking Zone Indicator Component
 *
 * Visual indicator showing braking intensity.
 * Can be used standalone or within TrackMap.
 *
 * @module components/BrakingZoneIndicator
 */

import type { FC, ReactElement } from 'react';

// =============================================================================
// Types
// =============================================================================

interface MiniBrakingIndicatorProps {
    brakeValue: number;
    size?: 'small' | 'medium' | 'large';
}

interface BrakingZoneMarkerProps {
    x: number;
    y: number;
    intensity?: number;
    label?: string;
}

interface BrakingIntensityBarProps {
    value: number;
    maxValue?: number;
    orientation?: 'vertical' | 'horizontal';
    showLabel?: boolean;
    height?: number;
    width?: number;
}

interface ThrottleBrakeIndicatorProps {
    throttle?: number;
    brake?: number;
    height?: number;
}

// =============================================================================
// Components
// =============================================================================

const MiniBrakingIndicator: FC<MiniBrakingIndicatorProps> = ({ brakeValue, size = 'small' }) => {
    const normalizedValue = brakeValue > 1 ? brakeValue : brakeValue * 100;
    const sizes = { small: { width: 6, height: 16 }, medium: { width: 8, height: 24 }, large: { width: 12, height: 32 } };
    const { width, height } = sizes[size];

    let intensityClass = '';
    if (normalizedValue > 80) intensityClass = 'intensity-high';
    else if (normalizedValue > 40) intensityClass = 'intensity-medium';
    else if (normalizedValue > 0) intensityClass = 'intensity-low';

    return (
        <div className="braking-indicator" style={{ width, height }} title={`Brake: ${Math.round(normalizedValue)}%`}>
            <div className={`braking-indicator-fill ${intensityClass}`} style={{ height: `${normalizedValue}%` }} />
        </div>
    );
};

const BrakingZoneMarker: FC<BrakingZoneMarkerProps> = ({ x, y, intensity = 1, label }): ReactElement => {
    const radius = 4 + intensity * 4;
    const alpha = 0.5 + intensity * 0.3;

    return (
        <g className="braking-zone-marker" transform={`translate(${x}, ${y})`}>
            <circle r={radius + 4} fill={`rgba(255, 0, 85, ${alpha * 0.3})`}>
                <animate attributeName="r" values={`${radius + 2};${radius + 6};${radius + 2}`} dur="1s" repeatCount="indefinite" />
            </circle>
            <circle r={radius} fill={`rgba(255, 0, 85, ${alpha})`} stroke="rgba(255, 255, 255, 0.5)" strokeWidth={1} />
            {label && (<text y={radius + 12} textAnchor="middle" fill="var(--text-secondary)" fontSize="9" fontWeight="bold">{label}</text>)}
        </g>
    );
};

const BrakingIntensityBar: FC<BrakingIntensityBarProps> = ({ value, maxValue = 100, orientation = 'vertical', showLabel = true, height = 80, width = 24 }) => {
    const percentage = Math.min(100, Math.max(0, (value / maxValue) * 100));
    let color = 'var(--accent-orange)';
    if (percentage > 80) color = '#ff0000';
    else if (percentage > 60) color = '#ff3300';
    else if (percentage > 40) color = '#ff6600';
    else if (percentage > 20) color = '#ff9933';

    if (orientation === 'horizontal') {
        return (
            <div className="braking-intensity-bar horizontal" style={{ width: '100%', height: width }}>
                {showLabel && <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>BRAKE</span>}
                <div style={{ height: width, background: 'var(--bg-tertiary)', borderRadius: width / 2, overflow: 'hidden', position: 'relative' }}>
                    <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${percentage}%`, background: color, borderRadius: width / 2, transition: 'width 0.1s ease', boxShadow: percentage > 50 ? `0 0 8px ${color}` : 'none' }} />
                </div>
            </div>
        );
    }

    return (
        <div className="braking-intensity-bar vertical" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
            {showLabel && <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Brake</span>}
            <div style={{ width, height, background: 'var(--bg-tertiary)', borderRadius: 4, overflow: 'hidden', position: 'relative' }}>
                <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: `${percentage}%`, background: color, borderRadius: 4, transition: 'height 0.1s ease', boxShadow: percentage > 50 ? `0 0 8px ${color}` : 'none' }} />
            </div>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>{Math.round(value)}%</span>
        </div>
    );
};

const ThrottleBrakeIndicator: FC<ThrottleBrakeIndicatorProps> = ({ throttle = 0, brake = 0, height = 80 }) => {
    const normalizedBrake = brake > 1 ? brake : brake * 100;
    return (
        <div className="throttle-brake-indicator" style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>THR</span>
                <div style={{ width: 20, height, background: 'var(--bg-tertiary)', borderRadius: 4, overflow: 'hidden', position: 'relative' }}>
                    <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: `${throttle}%`, background: 'var(--accent-green)', borderRadius: 4, transition: 'height 0.1s ease' }} />
                </div>
                <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>{Math.round(throttle)}%</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>BRK</span>
                <div style={{ width: 20, height, background: 'var(--bg-tertiary)', borderRadius: 4, overflow: 'hidden', position: 'relative' }}>
                    <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: `${normalizedBrake}%`, background: normalizedBrake > 80 ? '#ff0000' : 'var(--status-red)', borderRadius: 4, transition: 'height 0.1s ease', boxShadow: normalizedBrake > 80 ? '0 0 8px rgba(255, 0, 0, 0.5)' : 'none' }} />
                </div>
                <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>{Math.round(normalizedBrake)}%</span>
            </div>
        </div>
    );
};

export default BrakingIntensityBar;
export { MiniBrakingIndicator, BrakingZoneMarker, BrakingIntensityBar, ThrottleBrakeIndicator };
