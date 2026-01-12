/**
 * Track Map Component
 *
 * 2D track visualization with live car positions rendered via SVG.
 * Uses real track geometry from FastF1 API with responsive sizing.
 *
 * Features:
 * - Real-time car position updates
 * - DRS zone highlighting
 * - Track status indicators (green/yellow/SC/VSC)
 * - Responsive layout via ResizeObserver
 *
 * @module components/TrackMap
 */

import { useRef, useEffect, useMemo, useCallback, useState, type FC, type CSSProperties } from 'react';
import type { DriverState, TrackConfig, TrackBounds, DRSZone, TrackPoint, TrackStatus } from '../types';

// =============================================================================
// Types
// =============================================================================

interface TrackMapProps {
    /** Array of drivers with position data */
    drivers?: DriverState[];
    /** Track geometry from backend */
    trackConfig?: TrackConfig | null;
    /** Currently selected driver for highlighting */
    selectedDriver?: DriverState | null;
    /** Callback when driver marker is clicked */
    onDriverSelect?: (driver: DriverState) => void;
    /** Whether to show DRS zones */
    showDRS?: boolean;
    /** Current track status for coloring */
    trackStatus?: TrackStatus;
}

interface CarPosition {
    driver: DriverState;
    x: number;
    y: number;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Transform real X/Y coordinates to SVG viewport coordinates.
 *
 * @param point - Real track coordinates
 * @param bounds - Track boundary box
 * @param width - SVG viewport width
 * @param height - SVG viewport height
 * @param padding - Padding around track
 * @returns Transformed SVG coordinates
 */
function transformCoords(
    point: TrackPoint,
    bounds: TrackBounds,
    width: number,
    height: number,
    padding = 20
): TrackPoint {
    const { x_min, x_max, y_min, y_max } = bounds;
    const trackWidth = x_max - x_min;
    const trackHeight = y_max - y_min;

    const scaleX = (width - padding * 2) / trackWidth;
    const scaleY = (height - padding * 2) / trackHeight;
    const scale = Math.min(scaleX, scaleY);

    const offsetX = (width - trackWidth * scale) / 2;
    const offsetY = (height - trackHeight * scale) / 2;

    return {
        x: offsetX + (point.x - x_min) * scale,
        y: offsetY + (point.y - y_min) * scale,
    };
}

/**
 * Create SVG path from track points.
 */
/**
 * Create SVG path from track points.
 */
function createTrackPathFromPoints(
    points: TrackPoint[] | undefined,
    bounds: TrackBounds,
    width: number,
    height: number
): string {
    if (!points || points.length < 2) return '';

    const transformed = points.map((p) => transformCoords(p, bounds, width, height));

    let path = `M ${transformed[0].x} ${transformed[0].y}`;
    for (let i = 1; i < transformed.length; i++) {
        path += ` L ${transformed[i].x} ${transformed[i].y}`;
    }
    path += ' Z';

    return path;
}

// =============================================================================
// Sub-Components
// =============================================================================

interface CarMarkerProps {
    driver: DriverState;
    x: number;
    y: number;
    isSelected: boolean;
    onClick: () => void;
}

/**
 * Car marker positioned on track.
 */
const CarMarker: FC<CarMarkerProps> = ({ driver, x, y, isSelected, onClick }) => {
    const teamColor = driver.team_colour ? `#${driver.team_colour}` : '#FFFFFF';

    return (
        <g
            transform={`translate(${x}, ${y})`}
            onClick={onClick}
            style={{ cursor: 'pointer', transition: 'transform 0.05s linear', willChange: 'transform' }}
        >
            {isSelected && (
                <circle r={10} fill="none" stroke={teamColor} strokeWidth={2} opacity={0.5}>
                    <animate attributeName="r" values="10;14;10" dur="1s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.5;0.2;0.5" dur="1s" repeatCount="indefinite" />
                </circle>
            )}
            <circle r={5} fill={teamColor} stroke="#000" strokeWidth={1} />
            <text y={-10} textAnchor="middle" fill="white" fontSize="8" fontWeight="bold" fontFamily="var(--font-display)">
                {driver.name_acronym || driver.driver_number}
            </text>
        </g>
    );
};

interface DRSZoneHighlightProps {
    zone: DRSZone;
    bounds: TrackBounds;
    width: number;
    height: number;
}

/**
 * DRS zone highlight on track.
 */
const DRSZoneHighlight: FC<DRSZoneHighlightProps> = ({ zone, bounds, width, height }) => {
    const start = transformCoords({ x: zone.start_x, y: zone.start_y }, bounds, width, height);
    const end = transformCoords({ x: zone.end_x, y: zone.end_y }, bounds, width, height);

    return (
        <line
            x1={start.x}
            y1={start.y}
            x2={end.x}
            y2={end.y}
            stroke="rgba(0, 255, 136, 0.8)"
            strokeWidth={6}
            strokeLinecap="round"
            opacity={0.7}
        >
            <animate attributeName="opacity" values="0.5;0.9;0.5" dur="2s" repeatCount="indefinite" />
        </line>
    );
};

// =============================================================================
// Main Component
// =============================================================================

/**
 * 2D track visualization with live car positions.
 *
 * Renders real track geometry from FastF1 with responsive sizing
 * and real-time position updates.
 */
const TrackMap: FC<TrackMapProps> = ({
    drivers = [],
    trackConfig,
    selectedDriver = null,
    onDriverSelect,
    showDRS = true,
    trackStatus = 'GREEN',
}) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [dimensions, setDimensions] = useState({ width: 400, height: 280 });
    const [geometry, setGeometry] = useState<TrackConfig | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Responsive: observe container size
    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        const observer = new ResizeObserver((entries) => {
            const entry = entries[0];
            if (entry) {
                const { width, height } = entry.contentRect;
                setDimensions({
                    width: Math.max(200, width - 16),
                    height: Math.max(150, height - 60),
                });
            }
        });

        observer.observe(container);
        return () => observer.disconnect();
    }, []);

    const { width, height } = dimensions;

    // Use track geometry from props
    useEffect(() => {
        if (!trackConfig) {
            setError('No track data available');
            setLoading(false);
            return;
        }

        setGeometry(trackConfig);
        setLoading(false);
        setError(null);
    }, [trackConfig]);

    // Generate track paths from geometry
    const { trackPath, innerPath, outerPath, bounds } = useMemo(() => {
        if (!geometry) {
            return { trackPath: '', innerPath: '', outerPath: '', bounds: null };
        }

        return {
            trackPath: createTrackPathFromPoints(geometry.center_line, geometry.bounds, width, height),
            innerPath: createTrackPathFromPoints(geometry.inner_edge, geometry.bounds, width, height),
            outerPath: createTrackPathFromPoints(geometry.outer_edge, geometry.bounds, width, height),
            bounds: geometry.bounds,
        };
    }, [geometry, width, height]);

    // Calculate car positions using real X/Y coordinates
    const carPositions = useMemo((): CarPosition[] => {
        if (!drivers || drivers.length === 0 || !bounds) return [];

        return drivers
            .map((driver): CarPosition | null => {
                if (driver.rel_dist === null || driver.rel_dist === undefined) {
                    return null;
                }

                // Use real x/y from telemetry if available
                if (driver.x !== undefined && driver.x !== null && driver.y !== undefined && driver.y !== null) {
                    const pos = transformCoords({ x: driver.x, y: driver.y }, bounds, width, height);
                    return { driver, x: pos.x, y: pos.y };
                }

                // Fallback: interpolate along center line
                if (geometry?.center_line && driver.rel_dist !== undefined) {
                    const relDist = driver.rel_dist || 0;
                    const points = geometry.center_line;
                    const idx = Math.floor(relDist * (points.length - 1));
                    const point = points[Math.min(idx, points.length - 1)];
                    const pos = transformCoords(point, bounds, width, height);
                    return { driver, x: pos.x, y: pos.y };
                }

                return null;
            })
            .filter((pos): pos is CarPosition => pos !== null);
    }, [drivers, geometry, bounds, width, height]);

    // Track color based on status
    const trackColor = useMemo(() => {
        const colors: Record<TrackStatus, string> = {
            GREEN: '#444444',
            YELLOW: 'rgba(255, 208, 0, 0.9)',
            RED: 'rgba(255, 0, 85, 0.9)',
            SC: 'rgba(255, 165, 0, 0.9)',
            VSC: 'rgba(255, 140, 0, 0.7)',
        };
        return colors[trackStatus] || colors.GREEN;
    }, [trackStatus]);

    const handleCarClick = useCallback(
        (driver: DriverState) => {
            onDriverSelect?.(driver);
        },
        [onDriverSelect]
    );

    // Loading state
    if (loading) {
        return (
            <div
                ref={containerRef}
                className="track-map card"
                style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading track geometry...</div>
            </div>
        );
    }

    // No geometry - show placeholder
    if (!geometry) {
        return (
            <div
                ref={containerRef}
                className="track-map card"
                style={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: 'var(--space-md)',
                }}
            >
                <svg width="60%" height="50%" viewBox="0 0 200 150" preserveAspectRatio="xMidYMid meet">
                    <ellipse cx="100" cy="75" rx="80" ry="55" fill="none" stroke="#333" strokeWidth="12" />
                    <ellipse cx="100" cy="75" rx="80" ry="55" fill="none" stroke="#555" strokeWidth="4" />
                </svg>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: 'var(--space-sm)' }}>
                    {error || 'Select a session to load track'}
                </div>
            </div>
        );
    }

    const containerStyle: CSSProperties = {
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        padding: 'var(--space-sm)',
        overflow: 'hidden',
    };

    const headerStyle: CSSProperties = {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 'var(--space-xs)',
        paddingBottom: 'var(--space-xs)',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        flexShrink: 0,
    };

    return (
        <div ref={containerRef} className="track-map card card-glow" style={containerStyle}>
            {/* Header */}
            <div style={headerStyle}>
                <span
                    style={{
                        fontSize: '0.65rem',
                        color: 'var(--text-tertiary)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                    }}
                >
                    Track
                </span>
                <div style={{ display: 'flex', gap: 'var(--space-xs)' }}>
                    {showDRS && <span style={{ fontSize: '0.55rem', color: 'var(--accent-green)' }}>● DRS</span>}
                    <span
                        style={{
                            fontSize: '0.55rem',
                            color: trackStatus === 'GREEN' ? 'var(--status-green)' : 'var(--status-yellow)',
                            fontWeight: 600,
                        }}
                    >
                        {trackStatus}
                    </span>
                </div>
            </div>

            {/* SVG Track */}
            <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
                <svg
                    width="100%"
                    height="100%"
                    viewBox={`0 0 ${width} ${height}`}
                    preserveAspectRatio="xMidYMid meet"
                    style={{ display: 'block' }}
                >
                    <defs>
                        <filter id="trackGlow" x="-20%" y="-20%" width="140%" height="140%">
                            <feGaussianBlur stdDeviation="2" result="blur" />
                            <feMerge>
                                <feMergeNode in="blur" />
                                <feMergeNode in="SourceGraphic" />
                            </feMerge>
                        </filter>
                    </defs>

                    {/* Track surface */}
                    <path d={outerPath} fill="rgba(40, 40, 40, 0.5)" stroke="none" />

                    {/* Inner edge */}
                    <path d={innerPath} fill="none" stroke="#333" strokeWidth={2} />

                    {/* Outer edge */}
                    <path d={outerPath} fill="none" stroke={trackColor} strokeWidth={2} />

                    {/* Center racing line */}
                    <path d={trackPath} fill="none" stroke="rgba(100, 100, 100, 0.5)" strokeWidth={1} strokeDasharray="4 4" />

                    {/* DRS Zones */}
                    {showDRS &&
                        geometry.drs_zones?.map((zone, idx) => (
                            <DRSZoneHighlight key={idx} zone={zone} bounds={bounds!} width={width} height={height} />
                        ))}

                    {/* Car markers */}
                    {carPositions.map(({ driver, x, y }) => (
                        <CarMarker
                            key={driver.driver_number}
                            driver={driver}
                            x={x}
                            y={y}
                            isSelected={selectedDriver?.driver_number === driver.driver_number}
                            onClick={() => handleCarClick(driver)}
                        />
                    ))}
                </svg>
            </div>

            {/* Driver count */}
            <div
                style={{
                    textAlign: 'center',
                    fontSize: '0.6rem',
                    color: 'var(--text-muted)',
                    marginTop: 'var(--space-xs)',
                    flexShrink: 0,
                }}
            >
                {carPositions.length > 0 ? `${carPositions.length} drivers on track` : 'Waiting for positions...'}
            </div>
        </div>
    );
};

export default TrackMap;
export { CarMarker, DRSZoneHighlight, transformCoords, createTrackPathFromPoints };
export type { TrackPoint, TrackBounds, DRSZone };
