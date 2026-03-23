/**
 * BattlePredictor
 *
 * Compact overlay shown on the TrackMap when the selected driver is in
 * a battle (within 1.5 s of the car ahead or being chased from behind).
 *
 * Overtake probability comes from the backend neural model — not computed
 * here. This component is purely presentational.
 *
 * Does NOT repeat: tyre compound/age (leaderboard), DRS status (TelemetryHUD),
 * gap in seconds (leaderboard), undercut/overcut flags (StrategyPanel).
 */

import { type FC } from 'react';
import type { DriverState } from '../types';
import { OVERTAKE_HIGH_PROBABILITY_PCT } from '../config/constants';

interface BattlePredictorProps {
    selectedDriver: DriverState;
    allDrivers: DriverState[];
}

const BattlePredictor: FC<BattlePredictorProps> = ({ selectedDriver, allDrivers }) => {
    const selectedPos = selectedDriver.position ?? 0;

    // Attack: selected driver is within 1.5 s of car ahead
    const isAttacking = selectedDriver.overtake_probability !== null;

    // Defend: driver directly behind is attacking selected driver
    const attacker = allDrivers.find(
        d => d.position === selectedPos + 1 && d.overtake_probability !== null
    ) ?? null;
    const isDefending = !isAttacking && attacker !== null;

    if (!isAttacking && !isDefending) return null;

    const mode = isAttacking ? 'ATTACK' : 'DEFEND';
    const modeIcon = isAttacking ? '⚔' : '🛡';
    const probability = isAttacking
        ? (selectedDriver.overtake_probability ?? 0)
        : (attacker!.overtake_probability ?? 0);
    const keyFactor = isAttacking
        ? selectedDriver.battle_key_factor
        : attacker!.battle_key_factor;

    // Find the opponent driver for the label
    const opponentPosition = isAttacking
        ? selectedPos - 1
        : selectedPos;
    const opponent = allDrivers.find(d => d.position === opponentPosition) ?? null;

    const pct = Math.round(probability * 100);
    const barWidth = `${pct}%`;
    const isHighProb = pct >= OVERTAKE_HIGH_PROBABILITY_PCT;
    const barColor = isAttacking
        ? (isHighProb ? 'var(--color-accent)' : 'var(--status-yellow, #f0c040)')
        : 'var(--status-red)';

    return (
        <div style={{
            position: 'absolute',
            bottom: '8px',
            left: '8px',
            padding: '8px 12px',
            background: 'rgba(0,0,0,0.82)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            minWidth: '210px',
            maxWidth: '240px',
            pointerEvents: 'none',
            zIndex: 10,
        }}>
            {/* Header row */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                marginBottom: '6px',
            }}>
                <span style={{ fontSize: '0.7rem' }}>{modeIcon}</span>
                <span style={{
                    fontFamily: 'var(--font-sans)',
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    letterSpacing: '0.08em',
                    color: isAttacking ? 'var(--color-accent)' : 'var(--status-red)',
                }}>
                    {mode}
                </span>
                {opponent && (
                    <>
                        <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                            {isAttacking ? selectedDriver.name_acronym : attacker!.name_acronym}
                            {' → '}
                            {isAttacking ? opponent.name_acronym : selectedDriver.name_acronym}
                        </span>
                    </>
                )}
            </div>

            {/* Probability bar */}
            <div style={{ marginBottom: '5px' }}>
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '3px',
                }}>
                    <span style={{
                        fontSize: '0.6rem',
                        color: 'var(--text-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                    }}>
                        Overtake
                    </span>
                    <span style={{
                        fontFamily: 'var(--font-sans)',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        color: barColor,
                    }}>
                        {pct}%
                    </span>
                </div>
                <div style={{
                    height: '4px',
                    background: 'var(--bg-elevated)',
                    borderRadius: '2px',
                    overflow: 'hidden',
                }}>
                    <div style={{
                        height: '100%',
                        width: barWidth,
                        background: barColor,
                        borderRadius: '2px',
                        transition: 'width 0.6s ease',
                    }} />
                </div>
            </div>

            {/* Key factor */}
            {keyFactor && (
                <div style={{
                    fontSize: '0.6rem',
                    color: 'var(--text-muted)',
                    fontFamily: 'var(--font-mono)',
                }}>
                    {keyFactor}
                </div>
            )}
        </div>
    );
};

export default BattlePredictor;
