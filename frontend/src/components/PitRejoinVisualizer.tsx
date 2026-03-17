/**
 * Pit Rejoin Visualizer Component
 *
 * Visualizes where the driver will rejoin the track if they pit NOW.
 * Shows a "Ghost Car" relative to other drivers on track, with:
 * - Color-coded nearby drivers (red = will be ahead, green = behind)
 * - Driver acronym labels
 * - Net position change badge
 * - Traffic severity zone at exit
 */

import { useMemo, type FC } from 'react';
import type { DriverState } from '../types';

interface PitRejoinVisualizerProps {
    driver: DriverState;
    allDrivers: DriverState[];
}

// Map timeDelta (seconds relative to current driver) to bar percentage position.
// 0s (current position) → 10%, pitLoss (rejoin position) → 80%
// Scale: pitLoss seconds spans 70% of bar width
function timeToPct(timeDelta: number, pitLoss: number): number {
    return 10 + (timeDelta / pitLoss) * 70;
}

const PitRejoinVisualizer: FC<PitRejoinVisualizerProps> = ({ driver, allDrivers }) => {
    const pitLoss = 22.0; // Seconds (TODO: Get from track config)

    // Classify each nearby driver relative to our post-pit rejoin position
    const { nearbyDrivers, positionChange } = useMemo(() => {
        const others = allDrivers
            .filter(d => d.driver_number !== driver.driver_number)
            .map(d => {
                let gapToUs = 0.0;
                if (driver.gap_to_leader !== null && d.gap_to_leader !== null) {
                    gapToUs = d.gap_to_leader - driver.gap_to_leader;
                } else if (d.position !== null && driver.position !== null) {
                    gapToUs = (d.position - driver.position) * 1.5;
                } else {
                    gapToUs = 999.0;
                }
                return { ...d, gapToUs };
            })
            // Keep window from -5s ahead of us to pitLoss + 12s
            .filter(d => d.gapToUs > -5.0 && d.gapToUs < pitLoss + 12.0);

        // Drivers between 0 and pitLoss will be AHEAD after our pit (dangerous)
        const aheadAfterPit = others.filter(d => d.gapToUs >= 0 && d.gapToUs <= pitLoss).length;
        return {
            nearbyDrivers: others,
            // Rough position change: we lose positions for every car between 0 and pitLoss
            positionChange: aheadAfterPit,
        };
    }, [allDrivers, driver, pitLoss]);

    const trafficHigh = (driver.rejoin_traffic_severity ?? 0) > 0.6;
    const trafficMed = (driver.rejoin_traffic_severity ?? 0) > 0.35;
    const teamHex = driver.team_colour ? `#${driver.team_colour}` : '#888';

    return (
        <div style={{ marginTop: 'var(--space-md)', padding: 'var(--space-sm)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    Pit Rejoin Prediction
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {trafficHigh && (
                        <span style={{ fontSize: '0.62rem', color: 'var(--status-red)', fontWeight: 700, letterSpacing: '0.06em' }}>
                            ⚠ TRAFFIC
                        </span>
                    )}
                    {positionChange > 0 && (
                        <span style={{
                            fontSize: '0.62rem',
                            fontFamily: 'var(--font-mono)',
                            color: positionChange >= 2 ? 'var(--status-red)' : 'var(--status-amber)',
                            background: positionChange >= 2 ? 'rgba(248,81,73,0.12)' : 'rgba(210,153,34,0.12)',
                            padding: '1px 5px',
                            borderRadius: '3px',
                            fontWeight: 700,
                        }}>
                            -{positionChange} POS
                        </span>
                    )}
                    {positionChange === 0 && (
                        <span style={{
                            fontSize: '0.62rem',
                            fontFamily: 'var(--font-mono)',
                            color: 'var(--status-green)',
                            background: 'rgba(63,185,80,0.1)',
                            padding: '1px 5px',
                            borderRadius: '3px',
                            fontWeight: 700,
                        }}>
                            CLEAN EXIT
                        </span>
                    )}
                </div>
            </div>

            {/* Track bar */}
            <div style={{ position: 'relative', height: '52px', background: 'rgba(0,0,0,0.3)', borderRadius: '4px', overflow: 'visible', marginBottom: '4px' }}>
                {/* Track center line */}
                <div style={{ position: 'absolute', top: '50%', width: '100%', height: '1px', background: 'rgba(255,255,255,0.15)' }} />

                {/* Pit corridor band (from YOU to EXIT) */}
                <div style={{
                    position: 'absolute',
                    left: '10%',
                    width: '70%',
                    top: '35%',
                    height: '30%',
                    background: 'rgba(255,255,255,0.03)',
                    borderTop: '1px dashed rgba(255,255,255,0.12)',
                    borderBottom: '1px dashed rgba(255,255,255,0.12)',
                }} />

                {/* Pit loss label */}
                <div style={{
                    position: 'absolute',
                    left: '50%',
                    top: '12%',
                    transform: 'translateX(-50%)',
                    fontSize: '0.55rem',
                    color: 'var(--text-muted)',
                    whiteSpace: 'nowrap',
                    letterSpacing: '0.04em',
                }}>
                    PIT LOSS (~{pitLoss}s)
                </div>

                {/* Traffic severity overlay on exit zone */}
                {(trafficMed || trafficHigh) && (
                    <div style={{
                        position: 'absolute',
                        left: '72%',
                        width: '16%',
                        top: 0,
                        height: '100%',
                        background: trafficHigh
                            ? 'rgba(248,81,73,0.18)'
                            : 'rgba(210,153,34,0.12)',
                        borderRadius: '0 4px 4px 0',
                        pointerEvents: 'none',
                    }} />
                )}

                {/* YOU — current position */}
                <div style={{
                    position: 'absolute',
                    left: '10%',
                    top: '50%',
                    transform: 'translate(-50%, -50%)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '2px',
                    zIndex: 2,
                }}>
                    <div style={{
                        width: '13px',
                        height: '13px',
                        borderRadius: '50%',
                        background: teamHex,
                        border: '2px solid white',
                        boxShadow: `0 0 6px ${teamHex}`,
                    }} />
                    <span style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', fontWeight: 700, lineHeight: 1 }}>YOU</span>
                </div>

                {/* EXIT — ghost car (rejoin position) */}
                <div style={{
                    position: 'absolute',
                    left: '80%',
                    top: '50%',
                    transform: 'translate(-50%, -50%)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '2px',
                    zIndex: 2,
                    opacity: 0.75,
                }}>
                    <div style={{
                        width: '11px',
                        height: '11px',
                        borderRadius: '50%',
                        border: `2px dashed ${teamHex}`,
                        background: trafficHigh ? 'rgba(248,81,73,0.15)' : 'transparent',
                        boxShadow: trafficHigh ? `0 0 6px rgba(248,81,73,0.4)` : 'none',
                    }} />
                    <span style={{ fontSize: '0.55rem', color: 'var(--text-muted)', lineHeight: 1 }}>EXIT</span>
                </div>

                {/* Nearby drivers */}
                {nearbyDrivers.map(d => {
                    const pct = timeToPct(d.gapToUs, pitLoss);
                    if (pct < 0 || pct > 100) return null;

                    // Will this driver be AHEAD of us after the pit?
                    const willBeAhead = d.gapToUs >= 0 && d.gapToUs <= pitLoss;
                    const dotColor = willBeAhead
                        ? (d.gapToUs < pitLoss * 0.5 ? 'var(--status-red)' : 'var(--status-amber)')
                        : 'var(--status-green)';
                    const dotHex = d.team_colour ? `#${d.team_colour}` : '#888';

                    return (
                        <div
                            key={d.driver_number}
                            style={{
                                position: 'absolute',
                                left: `${pct}%`,
                                top: '50%',
                                transform: 'translate(-50%, -50%)',
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                gap: '2px',
                                zIndex: 1,
                            }}
                            title={`#${d.driver_number} ${d.name_acronym} (${d.gapToUs > 0 ? '+' : ''}${d.gapToUs.toFixed(1)}s from you)`}
                        >
                            <div style={{
                                width: '8px',
                                height: '8px',
                                borderRadius: '50%',
                                background: dotHex,
                                border: `1.5px solid ${dotColor}`,
                                boxShadow: willBeAhead ? `0 0 4px ${dotColor}` : 'none',
                            }} />
                            <span style={{
                                fontSize: '0.5rem',
                                color: dotColor,
                                fontWeight: 600,
                                lineHeight: 1,
                                whiteSpace: 'nowrap',
                            }}>
                                {d.name_acronym ?? `#${d.driver_number}`}
                            </span>
                        </div>
                    );
                })}
            </div>

            {/* Legend */}
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <span style={{ fontSize: '0.52rem', color: 'var(--status-red)', display: 'flex', alignItems: 'center', gap: '3px' }}>
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--status-red)', display: 'inline-block' }} />
                    Ahead after pit
                </span>
                <span style={{ fontSize: '0.52rem', color: 'var(--status-green)', display: 'flex', alignItems: 'center', gap: '3px' }}>
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--status-green)', display: 'inline-block' }} />
                    Behind after pit
                </span>
            </div>
        </div>
    );
};

export default PitRejoinVisualizer;
