/**
 * Tyre Life Chart Component
 * 
 * Visualizes predicted tyre performance (pace degradation) over future laps.
 * Highlights the "Cliff" phase where performance drops exponentially.
 */

import { useMemo, type FC } from 'react';
import type { DriverState } from '../types';

interface TyreLifeChartProps {
    driver: DriverState;
    height?: number;
}

const TyreLifeChart: FC<TyreLifeChartProps> = ({ driver, height = 120 }) => {
    const data = driver.predicted_pace;

    // If no prediction, show placeholder
    if (!data || data.length === 0) {
        return (
            <div className="tyre-life-chart card" style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span className="text-muted" style={{ fontSize: '0.75rem' }}>No prediction available</span>
            </div>
        );
    }

    const width = 300;
    const padding = { top: 10, right: 10, bottom: 20, left: 30 };

    // Calculate Scales
    const minPace = Math.min(...data);
    const maxPace = Math.max(...data);
    const paceRange = maxPace - minPace || 1;

    // Generate Path
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    const points = useMemo(() => {
        return data.map((pace, i) => {
            const x = padding.left + (i / (data.length - 1)) * chartWidth;
            // Invert Y because lower pace (smaller number) is BETTER (higher up)
            // Wait, normally graphs show value. 
            // If yMin (fastest) is at bottom, and yMax (slowest) is at top?
            // Usually graphical charts: Y axis goes up. Higher value = Higher Y.
            // So Slower (Higher Time) = Higher Y.
            const normalizedPace = (pace - minPace) / paceRange;
            const y = padding.top + chartHeight - (normalizedPace * chartHeight);
            return `${x},${y}`;
        }).join(' ');
    }, [data, minPace, paceRange, chartWidth, chartHeight]);

    return (
        <div className="tyre-life-chart" style={{ marginTop: 'var(--space-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-secondary)' }}>PREDICTED PACE (NEXT 5 LAPS)</span>
                <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-display)', color: 'var(--accent-cyan)' }}>
                    +{((data[data.length - 1] - data[0])).toFixed(3)}s
                </span>
            </div>

            <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
                {/* Background Grid */}
                <rect x={padding.left} y={padding.top} width={chartWidth} height={chartHeight} fill="rgba(0,0,0,0.2)" rx={4} />

                {/* The Line */}
                <polyline
                    points={points}
                    fill="none"
                    stroke="var(--accent-cyan)"
                    strokeWidth="2"
                    vectorEffect="non-scaling-stroke"
                />

                {/* Cliff Warning Zone if slope is high */}
                {data[data.length - 1] - data[0] > 0.5 && (
                    <rect
                        x={width - 50}
                        y={padding.top}
                        width={40}
                        height={chartHeight}
                        fill="url(#cliffGradient)"
                        opacity="0.3"
                    />
                )}

                <defs>
                    <linearGradient id="cliffGradient" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="transparent" />
                        <stop offset="100%" stopColor="var(--status-red)" />
                    </linearGradient>
                </defs>

                {/* Labels */}
                <text x={padding.left - 5} y={padding.top + 10} textAnchor="end" fontSize="8" fill="var(--text-muted)">
                    {minPace.toFixed(1)}
                </text>
                <text x={padding.left - 5} y={height - padding.bottom} textAnchor="end" fontSize="8" fill="var(--text-muted)">
                    {maxPace.toFixed(1)}
                </text>
            </svg>
        </div>
    );
};

export default TyreLifeChart;
