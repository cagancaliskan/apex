/**
 * Telemetry Chart Component
 *
 * Multi-chart display for detailed telemetry analysis.
 * Shows speed, gear, throttle, and brake data over lap distance.
 *
 * @module components/TelemetryChart
 */

import { useMemo, type FC } from 'react';
import type { DriverState } from '../types';

// =============================================================================
// Types
// =============================================================================

interface DataPoint {
    [key: string]: number;
}

interface ChartPadding {
    top: number;
    right: number;
    bottom: number;
    left: number;
}

interface ChartProps {
    data?: DataPoint[];
    xKey: string;
    yKey: string;
    label: string;
    unit: string;
    color: string;
    height?: number;
    yMin?: number;
    yMax?: number;
    showGrid?: boolean;
}

interface ComparisonChartProps {
    driver1Data?: DataPoint[];
    driver2Data?: DataPoint[];
    xKey: string;
    yKey: string;
    label: string;
    driver1Color: string;
    driver2Color: string;
    height?: number;
    yMin?: number;
    yMax?: number;
}

interface ThrottleBrakeChartProps {
    data?: DataPoint[];
    height?: number;
}

interface TelemetryChartProps {
    telemetryData?: DataPoint[];
    comparisonData?: DataPoint[];
    driver?: DriverState | null;
    comparisonDriver?: DriverState | null;
    showSpeed?: boolean;
    showGear?: boolean;
    showThrottleBrake?: boolean;
    showDRS?: boolean;
    compact?: boolean;
}

// =============================================================================
// Helper Functions
// =============================================================================

function generatePath(
    data: DataPoint[] | undefined,
    xKey: string,
    yKey: string,
    width: number,
    height: number,
    yMin: number,
    yMax: number,
    padding: ChartPadding = { top: 10, right: 10, bottom: 20, left: 40 }
): string {
    if (!data || data.length === 0) return '';

    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    const xValues = data.map((d) => d[xKey]);
    const xMin = Math.min(...xValues);
    const xMax = Math.max(...xValues);
    const xRange = xMax - xMin || 1;
    const yRange = yMax - yMin || 1;

    let path = '';
    data.forEach((point, i) => {
        const x = padding.left + ((point[xKey] - xMin) / xRange) * chartWidth;
        const y = padding.top + chartHeight - ((point[yKey] - yMin) / yRange) * chartHeight;

        if (i === 0) {
            path += `M ${x} ${y}`;
        } else {
            path += ` L ${x} ${y}`;
        }
    });

    return path;
}

// =============================================================================
// Sub-Components
// =============================================================================

const Chart: FC<ChartProps> = ({ data, xKey, yKey, label, unit, color, height = 80, yMin = 0, yMax = 100, showGrid = true }) => {
    const width = 400;
    const padding = { top: 10, right: 10, bottom: 20, left: 45 };

    const path = useMemo(() => {
        return generatePath(data, xKey, yKey, width, height, yMin, yMax, padding);
    }, [data, xKey, yKey, width, height, yMin, yMax]);

    const yLabels = useMemo(() => {
        const count = 4;
        const labels = [];
        for (let i = 0; i <= count; i++) {
            const value = yMin + (yMax - yMin) * (i / count);
            labels.push({ value: Math.round(value), y: padding.top + (height - padding.top - padding.bottom) * (1 - i / count) });
        }
        return labels;
    }, [yMin, yMax, height]);

    return (
        <div className="telemetry-chart" style={{ marginBottom: 'var(--space-sm)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>{label}</span>
                <span style={{ fontSize: '0.7rem', color: color, fontFamily: 'var(--font-display)' }}>
                    {data && data.length > 0 ? `${data[data.length - 1]?.[yKey]?.toFixed?.(0) || 0}${unit}` : '-'}
                </span>
            </div>
            <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
                {showGrid && yLabels.map((l, i) => (
                    <g key={i}>
                        <line x1={padding.left} y1={l.y} x2={width - padding.right} y2={l.y} stroke="rgba(255,255,255,0.05)" strokeDasharray="2 4" />
                        <text x={padding.left - 5} y={l.y + 3} textAnchor="end" fill="var(--text-muted)" fontSize="9">{l.value}</text>
                    </g>
                ))}
                <rect x={padding.left} y={padding.top} width={width - padding.left - padding.right} height={height - padding.top - padding.bottom} fill="rgba(0,0,0,0.2)" rx={4} />
                {path && <path d={path} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />}
                {(!data || data.length === 0) && <text x={width / 2} y={height / 2} textAnchor="middle" fill="var(--text-muted)" fontSize="10">No data</text>}
            </svg>
        </div>
    );
};

const ComparisonChart: FC<ComparisonChartProps> = ({ driver1Data, driver2Data, xKey, yKey, label, driver1Color, driver2Color, height = 80, yMin = 0, yMax = 100 }) => {
    const width = 400;
    const padding = { top: 10, right: 10, bottom: 20, left: 45 };

    const path1 = useMemo(() => generatePath(driver1Data, xKey, yKey, width, height, yMin, yMax, padding), [driver1Data, xKey, yKey, height, yMin, yMax]);
    const path2 = useMemo(() => generatePath(driver2Data, xKey, yKey, width, height, yMin, yMax, padding), [driver2Data, xKey, yKey, height, yMin, yMax]);

    return (
        <div className="comparison-chart" style={{ marginBottom: 'var(--space-sm)' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: 4, display: 'block' }}>{label}</span>
            <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
                <rect x={padding.left} y={padding.top} width={width - padding.left - padding.right} height={height - padding.top - padding.bottom} fill="rgba(0,0,0,0.2)" rx={4} />
                {path1 && <path d={path1} fill="none" stroke={driver1Color} strokeWidth={2} opacity={0.8} />}
                {path2 && <path d={path2} fill="none" stroke={driver2Color} strokeWidth={2} opacity={0.8} strokeDasharray="4 2" />}
            </svg>
        </div>
    );
};

const ThrottleBrakeChart: FC<ThrottleBrakeChartProps> = ({ data, height = 60 }) => {
    const width = 400;
    const padding = { top: 5, right: 10, bottom: 5, left: 45 };

    const throttlePath = useMemo(() => generatePath(data, 'distance', 'throttle', width, height, 0, 100, padding), [data, height]);
    const brakePath = useMemo(() => generatePath(data, 'distance', 'brake', width, height, 0, 100, padding), [data, height]);

    return (
        <div className="throttle-brake-chart">
            <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: 4, display: 'block' }}>Throttle / Brake</span>
            <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
                <rect x={padding.left} y={padding.top} width={width - padding.left - padding.right} height={height - padding.top - padding.bottom} fill="rgba(0,0,0,0.2)" rx={4} />
                {throttlePath && <path d={`${throttlePath} L ${width - padding.right} ${height - padding.bottom} L ${padding.left} ${height - padding.bottom} Z`} fill="rgba(0, 255, 136, 0.2)" />}
                {brakePath && <path d={`${brakePath} L ${width - padding.right} ${height - padding.bottom} L ${padding.left} ${height - padding.bottom} Z`} fill="rgba(255, 0, 85, 0.2)" />}
                {throttlePath && <path d={throttlePath} fill="none" stroke="var(--accent-green)" strokeWidth={2} />}
                {brakePath && <path d={brakePath} fill="none" stroke="var(--status-red)" strokeWidth={2} />}
            </svg>
        </div>
    );
};

// =============================================================================
// Main Component
// =============================================================================

const TelemetryChart: FC<TelemetryChartProps> = ({
    telemetryData = [],
    comparisonData = null,
    driver = null,
    comparisonDriver = null,
    showSpeed = true,
    showGear = true,
    showThrottleBrake = true,
    showDRS = true,
    compact = false,
}) => {
    const chartHeight = compact ? 60 : 80;
    const displayData = useMemo(() => (telemetryData && telemetryData.length > 0 ? telemetryData : []), [telemetryData]);

    const driverColor = driver?.team_colour ? `#${driver.team_colour}` : 'var(--accent-cyan)';
    const comparisonColor = comparisonDriver?.team_colour ? `#${comparisonDriver.team_colour}` : 'var(--accent-magenta)';

    if (!driver && displayData.length === 0) {
        return (
            <div className="telemetry-chart-panel card" style={{ padding: 'var(--space-lg)', textAlign: 'center' }}>
                <span className="text-muted" style={{ fontSize: '0.75rem' }}>Select a driver to view telemetry</span>
            </div>
        );
    }

    return (
        <div className="telemetry-chart-panel card card-glow">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)', paddingBottom: 'var(--space-sm)', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                    <div style={{ width: 4, height: 20, backgroundColor: driverColor, borderRadius: 2 }} />
                    <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{driver?.name_acronym || 'Telemetry'}</span>
                </div>
                {comparisonDriver && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
                        <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>vs</span>
                        <div style={{ width: 3, height: 16, backgroundColor: comparisonColor, borderRadius: 2 }} />
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{comparisonDriver.name_acronym}</span>
                    </div>
                )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
                {showSpeed && (comparisonData ? (
                    <ComparisonChart driver1Data={displayData} driver2Data={comparisonData} xKey="distance" yKey="speed" label="Speed (km/h)" driver1Color={driverColor} driver2Color={comparisonColor} height={chartHeight} yMin={0} yMax={360} />
                ) : (
                    <Chart data={displayData} xKey="distance" yKey="speed" label="Speed" unit=" km/h" color={driverColor} height={chartHeight} yMin={0} yMax={360} />
                ))}
                {showGear && <Chart data={displayData} xKey="distance" yKey="gear" label="Gear" unit="" color="var(--accent-cyan)" height={compact ? 40 : 50} yMin={0} yMax={8} showGrid={false} />}
                {showThrottleBrake && <ThrottleBrakeChart data={displayData} height={compact ? 50 : 60} />}
                {showDRS && displayData.length > 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', padding: 'var(--space-xs) 0' }}>
                        <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>DRS Zones</span>
                        <div style={{ flex: 1, height: 8, background: 'var(--bg-tertiary)', borderRadius: 4, overflow: 'hidden' }}>
                            <div style={{ width: '15%', height: '100%', background: 'var(--accent-green)', marginLeft: '20%' }} />
                        </div>
                    </div>
                )}
            </div>

            {displayData.length === 0 && (
                <div style={{ textAlign: 'center', padding: 'var(--space-lg)', color: 'var(--text-muted)', fontSize: '0.75rem' }}>No telemetry data available</div>
            )}
        </div>
    );
};

export default TelemetryChart;
export { Chart, ComparisonChart, ThrottleBrakeChart, generatePath };
