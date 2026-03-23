/**
 * Strategy Comparison — Stay Out vs Pit Now
 *
 * Uses available driver data (deg_slope, predicted_pace, pit window)
 * to show a two-column comparison of staying out vs pitting now.
 */

import { useMemo, type FC } from 'react';
import type { DriverState } from '../types';
import { DEFAULT_RACE_LAPS, DEFAULT_PIT_LOSS_SECONDS } from '../config/constants';

interface StrategyComparisonProps {
    driver: DriverState;
    totalLaps?: number;
}

const FRESH_TYRE_PACE_GAIN = 0.8; // Seconds per lap gained on fresh tyres (approx)

const StrategyComparison: FC<StrategyComparisonProps> = ({ driver, totalLaps = DEFAULT_RACE_LAPS }) => {
    const analysis = useMemo(() => {
        const degSlope = driver.deg_slope ?? 0;
        const tyreAge = driver.tyre_age ?? driver.lap_in_stint ?? 0;
        const currentLap = tyreAge; // approximate
        const lapsRemaining = Math.max(1, totalLaps - currentLap);
        const cliffRisk = driver.cliff_risk ?? 0;

        // Stay out: cumulative degradation cost over remaining laps
        // Each future lap degrades by degSlope more than the current pace
        const stayOutCost = degSlope * lapsRemaining * (lapsRemaining + 1) / 2;

        // Pit now: fixed pit loss, but gain fresh tyre advantage
        const freshTyreGain = FRESH_TYRE_PACE_GAIN * Math.min(lapsRemaining, 15);
        const pitNowCost = DEFAULT_PIT_LOSS_SECONDS - freshTyreGain;

        const stayOutBetter = stayOutCost < pitNowCost;

        return {
            lapsRemaining,
            degSlope,
            cliffRisk,
            stayOutCost,
            pitNowCost,
            stayOutBetter,
            hasSufficientData: degSlope > 0 || (driver.predicted_pace && driver.predicted_pace.length > 0),
        };
    }, [driver, totalLaps]);

    if (!analysis.hasSufficientData) {
        return (
            <div style={{ marginTop: 'var(--space-md)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: 'var(--space-xs)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
                    Strategy Comparison
                </div>
                <div style={{ padding: 'var(--space-sm)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', fontSize: '0.65rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                    Waiting for degradation data
                </div>
            </div>
        );
    }

    return (
        <div style={{ marginTop: 'var(--space-md)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: 'var(--space-xs)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
                Strategy Comparison
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
                {/* Stay Out */}
                <div style={{
                    padding: '8px',
                    background: 'var(--bg-elevated)',
                    borderRadius: 'var(--radius-sm)',
                    borderLeft: `3px solid ${analysis.stayOutBetter ? 'var(--status-green)' : 'var(--status-amber)'}`,
                }}>
                    <div style={{ fontSize: '0.65rem', fontWeight: 700, color: analysis.stayOutBetter ? 'var(--status-green)' : 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>
                        Stay Out
                    </div>
                    <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginBottom: '3px' }}>Est. deg cost</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                        +{analysis.stayOutCost.toFixed(1)}s
                    </div>
                    <div style={{ marginTop: '6px', fontSize: '0.55rem', fontFamily: 'var(--font-mono)', padding: '2px 4px', borderRadius: '2px', display: 'inline-block', background: analysis.cliffRisk > 0.5 ? 'rgba(248,81,73,0.12)' : 'rgba(255,255,255,0.05)', color: analysis.cliffRisk > 0.5 ? 'var(--status-red)' : 'var(--text-muted)' }}>
                        {analysis.cliffRisk > 0.5 ? 'CLIFF RISK' : `${analysis.lapsRemaining}L left`}
                    </div>
                </div>

                {/* Pit Now */}
                <div style={{
                    padding: '8px',
                    background: 'var(--bg-elevated)',
                    borderRadius: 'var(--radius-sm)',
                    borderLeft: `3px solid ${!analysis.stayOutBetter ? 'var(--status-green)' : 'var(--status-amber)'}`,
                }}>
                    <div style={{ fontSize: '0.65rem', fontWeight: 700, color: !analysis.stayOutBetter ? 'var(--status-green)' : 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>
                        Pit Now
                    </div>
                    <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginBottom: '3px' }}>Net time cost</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                        {analysis.pitNowCost > 0 ? '+' : ''}{analysis.pitNowCost.toFixed(1)}s
                    </div>
                    <div style={{ marginTop: '6px', fontSize: '0.55rem', fontFamily: 'var(--font-mono)', padding: '2px 4px', borderRadius: '2px', display: 'inline-block', background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)' }}>
                        ~{DEFAULT_PIT_LOSS_SECONDS}s loss
                    </div>
                </div>
            </div>
        </div>
    );
};

export default StrategyComparison;
