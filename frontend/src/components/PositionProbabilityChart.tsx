/**
 * Position Probability Chart
 * 
 * Visualizes Monte Carlo simulation results showing the probability
 * distribution of finishing positions.
 * 
 * New in v3.0.1 (Nice-to-have feature)
 */

import type { FC } from 'react';

interface PositionProbability {
    position: number;
    probability: number;
}

interface PositionProbabilityChartProps {
    /** Array of position probabilities from Monte Carlo simulation */
    probabilities: PositionProbability[];
    /** Current race position */
    currentPosition?: number;
    /** Compact display mode */
    compact?: boolean;
}

/**
 * Get color for position
 */
function getPositionColor(position: number): string {
    if (position === 1) return '#ffd700'; // Gold
    if (position === 2) return '#c0c0c0'; // Silver
    if (position === 3) return '#cd7f32'; // Bronze
    if (position <= 10) return 'var(--color-info)';
    return 'var(--text-muted)';
}

/**
 * Position Probability Chart Component
 * 
 * Displays a horizontal bar chart of finishing position probabilities.
 */
const PositionProbabilityChart: FC<PositionProbabilityChartProps> = ({
    probabilities,
    currentPosition,
    compact = false
}) => {
    // Sort by position
    const sortedProbs = [...probabilities].sort((a, b) => a.position - b.position);

    // Find max probability for scaling
    const maxProb = Math.max(...sortedProbs.map(p => p.probability), 0.01);

    // Calculate expected position
    const expectedPosition = sortedProbs.reduce(
        (sum, p) => sum + p.position * p.probability,
        0
    );

    if (sortedProbs.length === 0) {
        return (
            <div style={{
                padding: 'var(--space-md)',
                textAlign: 'center',
                color: 'var(--text-muted)',
                fontSize: '0.75rem'
            }}>
                No simulation data available
            </div>
        );
    }

    return (
        <div style={{ marginTop: 'var(--space-md)' }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 'var(--space-sm)'
            }}>
                <span style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                }}>
                    Position Probabilities
                </span>
                <span style={{
                    fontFamily: 'var(--font-sans)',
                    fontSize: '0.85rem',
                    color: 'var(--color-info)'
                }}>
                    E[P] = {expectedPosition.toFixed(1)}
                </span>
            </div>

            <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: compact ? '2px' : '4px'
            }}>
                {sortedProbs
                    .filter(p => p.probability > 0.01) // Only show >1% probability
                    .slice(0, compact ? 5 : 10)
                    .map(({ position, probability }) => (
                        <div
                            key={position}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 'var(--space-xs)'
                            }}
                        >
                            {/* Position label */}
                            <span style={{
                                width: '24px',
                                fontFamily: 'var(--font-sans)',
                                fontSize: compact ? '0.7rem' : '0.8rem',
                                fontWeight: position === currentPosition ? 700 : 400,
                                color: position === currentPosition ? 'var(--color-info)' : 'var(--text-secondary)'
                            }}>
                                P{position}
                            </span>

                            {/* Bar */}
                            <div style={{
                                flex: 1,
                                height: compact ? '12px' : '16px',
                                background: 'var(--bg-tertiary)',
                                borderRadius: 'var(--radius-sm)',
                                overflow: 'hidden',
                                position: 'relative'
                            }}>
                                <div
                                    style={{
                                        height: '100%',
                                        width: `${(probability / maxProb) * 100}%`,
                                        background: `linear-gradient(90deg, ${getPositionColor(position)}, ${getPositionColor(position)}88)`,
                                        borderRadius: 'var(--radius-sm)',
                                        transition: 'width 0.3s ease'
                                    }}
                                />
                                {/* Probability text inside bar */}
                                <span style={{
                                    position: 'absolute',
                                    right: '4px',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    fontSize: compact ? '0.55rem' : '0.65rem',
                                    fontWeight: 600,
                                    color: probability > maxProb * 0.5 ? 'rgba(0,0,0,0.7)' : 'var(--text-muted)'
                                }}>
                                    {(probability * 100).toFixed(0)}%
                                </span>
                            </div>
                        </div>
                    ))}
            </div>

            {/* Legend */}
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                gap: 'var(--space-md)',
                marginTop: 'var(--space-sm)',
                fontSize: '0.6rem',
                color: 'var(--text-muted)'
            }}>
                <span>🥇 Win</span>
                <span>🥈 Podium</span>
                <span>🏁 Points</span>
            </div>
        </div>
    );
};

export default PositionProbabilityChart;
