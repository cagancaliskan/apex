/**
 * DRS Zone Overlay Component
 *
 * Visual overlay showing DRS zones on track.
 *
 * @module components/DRSZoneOverlay
 */

import type { FC, ReactElement } from 'react';

// =============================================================================
// Types
// =============================================================================

interface DRSZoneSegmentProps {
    startPercent: number;
    endPercent: number;
    trackPath: string;
    animated?: boolean;
}

interface DRSDetectionMarkerProps {
    x: number;
    y: number;
    label?: string;
}

interface DRSActivationMarkerProps {
    x: number;
    y: number;
}

interface DRSStatusIndicatorProps {
    status: number;
    size?: 'small' | 'medium' | 'large';
}

interface DRSZone {
    start?: number;
    end?: number;
    startPercent?: number;
    endPercent?: number;
}

interface DRSZoneBarProps {
    zones?: Array<{ start: number; end: number }>;
    currentPosition?: number;
    width?: string | number;
}

interface DRSZoneOverlayProps {
    zones?: DRSZone[];
    trackPath?: string;
    width?: number;
    height?: number;
    animated?: boolean;
}

// =============================================================================
// Components
// =============================================================================

const DRSZoneSegment: FC<DRSZoneSegmentProps> = ({ startPercent, endPercent, trackPath, animated = true }) => {
    const length = endPercent - startPercent;
    return (
        <path d={trackPath} fill="none" stroke="var(--accent-green)" strokeWidth={8} strokeLinecap="round" strokeDasharray={`${length} ${100 - length}`} strokeDashoffset={-startPercent} opacity={0.6}>
            {animated && <animate attributeName="opacity" values="0.4;0.8;0.4" dur="2s" repeatCount="indefinite" />}
        </path>
    );
};

const DRSDetectionMarker: FC<DRSDetectionMarkerProps> = ({ x, y, label }): ReactElement => (
    <g className="drs-detection-marker" transform={`translate(${x}, ${y})`}>
        <circle r={6} fill="none" stroke="var(--accent-green)" strokeWidth={2} strokeDasharray="4 2" />
        <circle r={3} fill="var(--accent-green)" />
        {label && <text y={-12} textAnchor="middle" fill="var(--accent-green)" fontSize="8" fontWeight="bold">{label}</text>}
    </g>
);

const DRSActivationMarker: FC<DRSActivationMarkerProps> = ({ x, y }): ReactElement => (
    <g className="drs-activation-marker" transform={`translate(${x}, ${y})`}>
        <rect x={-4} y={-8} width={8} height={16} fill="var(--accent-green)" rx={2}>
            <animate attributeName="opacity" values="0.6;1;0.6" dur="1.5s" repeatCount="indefinite" />
        </rect>
        <text y={20} textAnchor="middle" fill="var(--accent-green)" fontSize="7" fontWeight="bold">DRS</text>
    </g>
);

const DRSStatusIndicator: FC<DRSStatusIndicatorProps> = ({ status, size = 'medium' }) => {
    const isActive = [10, 12, 14].includes(status);
    const isAvailable = status === 8;
    const sizes = { small: { dot: 8, fontSize: '0.6rem', padding: '2px 6px' }, medium: { dot: 10, fontSize: '0.7rem', padding: '4px 8px' }, large: { dot: 14, fontSize: '0.8rem', padding: '6px 12px' } };
    const { dot, fontSize, padding } = sizes[size];

    let backgroundColor = 'var(--bg-tertiary)', dotColor = 'var(--text-muted)', textColor = 'var(--text-muted)', label = 'DRS OFF', glow = 'none';
    if (isActive) { backgroundColor = 'rgba(0, 255, 136, 0.1)'; dotColor = 'var(--accent-green)'; textColor = 'var(--accent-green)'; label = 'DRS OPEN'; glow = '0 0 8px var(--accent-green)'; }
    else if (isAvailable) { backgroundColor = 'rgba(255, 208, 0, 0.1)'; dotColor = 'var(--accent-yellow)'; textColor = 'var(--accent-yellow)'; label = 'DRS READY'; glow = '0 0 5px var(--accent-yellow)'; }

    return (
        <div className={`drs-status-indicator ${isActive ? 'active' : ''}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding, background: backgroundColor, borderRadius: 'var(--radius-full)', transition: 'all 0.2s ease' }}>
            <div style={{ width: dot, height: dot, borderRadius: '50%', backgroundColor: dotColor, boxShadow: glow, transition: 'all 0.2s ease' }} />
            <span style={{ fontSize, color: textColor, fontWeight: 600, letterSpacing: '0.05em' }}>{label}</span>
        </div>
    );
};

const DRSZoneBar: FC<DRSZoneBarProps> = ({ zones = [], currentPosition = 0, width = '100%' }) => (
    <div className="drs-zone-bar" style={{ width }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>DRS Zones</span>
            <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>{zones.length} zone{zones.length !== 1 ? 's' : ''}</span>
        </div>
        <div style={{ height: 8, background: 'var(--bg-tertiary)', borderRadius: 4, overflow: 'hidden', position: 'relative' }}>
            {zones.map((zone, index) => <div key={index} style={{ position: 'absolute', left: `${zone.start}%`, width: `${zone.end - zone.start}%`, top: 0, bottom: 0, background: 'var(--accent-green)', opacity: 0.6 }} />)}
            <div style={{ position: 'absolute', left: `${currentPosition}%`, top: -2, bottom: -2, width: 3, background: 'white', borderRadius: 2, transform: 'translateX(-50%)', transition: 'left 0.1s ease' }} />
        </div>
    </div>
);

const DRSZoneOverlay: FC<DRSZoneOverlayProps> = ({ zones = [], trackPath, animated = true }) => {
    if (!zones || zones.length === 0 || !trackPath) return null;
    return (
        <g className="drs-zone-overlay">
            {zones.map((zone, index) => <DRSZoneSegment key={index} startPercent={zone.start || zone.startPercent || 0} endPercent={zone.end || zone.endPercent || 0} trackPath={trackPath} animated={animated} />)}
        </g>
    );
};

export default DRSZoneOverlay;
export { DRSZoneSegment, DRSDetectionMarker, DRSActivationMarker, DRSStatusIndicator, DRSZoneBar };
