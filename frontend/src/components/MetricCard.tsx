/**
 * Metric Card Component
 *
 * Displays a key statistic with optional delta indicator and icon.
 *
 * @module components/MetricCard
 */

import type { FC, ComponentType } from 'react';

// =============================================================================
// Types
// =============================================================================

interface MetricCardProps {
    /** Label text */
    label: string;
    /** Main value to display */
    value: string | number;
    /** Change delta (optional) */
    delta?: string | number;
    /** Delta direction */
    deltaType?: 'positive' | 'negative';
    /** Accent color */
    color?: 'cyan' | 'green' | 'red' | 'orange' | 'purple';
    /** Optional icon component */
    icon?: ComponentType<{ size?: number; style?: React.CSSProperties }>;
}

// =============================================================================
// Component
// =============================================================================

/**
 * Card displaying a labeled metric value with optional change indicator.
 */
const MetricCard: FC<MetricCardProps> = ({ label, value, delta, deltaType, color = 'cyan', icon: Icon }) => {
    return (
        <div className="metric-card card-glow">
            <div className="flex items-center justify-between">
                <span className="label">{label}</span>
                {Icon && <Icon size={18} style={{ color: `var(--accent-${color})`, opacity: 0.7 }} />}
            </div>
            <div className={`value ${color}`}>{value}</div>
            {delta && (
                <div className={`delta ${deltaType}`}>
                    {deltaType === 'positive' ? '↑' : '↓'} {delta}
                </div>
            )}
        </div>
    );
};

export default MetricCard;
