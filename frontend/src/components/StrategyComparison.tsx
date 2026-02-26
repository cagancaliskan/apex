/**
 * Strategy Comparison Component
 *
 * Will display 1-stop vs 2-stop strategy comparison with expected outcomes
 * once wired to backend Monte Carlo simulation results.
 */

import type { FC } from 'react';

interface StrategyComparisonProps {
    currentPosition: number;
}

const StrategyComparison: FC<StrategyComparisonProps> = ({ currentPosition: _currentPosition }) => {
    return (
        <div style={{ marginTop: 'var(--space-md)' }}>
            <div style={{
                fontSize: '0.75rem',
                color: 'var(--text-muted)',
                marginBottom: 'var(--space-xs)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
            }}>
                Strategy Comparison
            </div>
            <div style={{
                padding: 'var(--space-sm)',
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.7rem',
                color: 'var(--text-muted)',
                textAlign: 'center',
            }}>
                Monte Carlo analysis requires additional lap data
            </div>
        </div>
    );
};

export default StrategyComparison;
