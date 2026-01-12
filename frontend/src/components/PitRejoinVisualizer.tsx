/**
 * Pit Rejoin Visualizer Component
 * 
 * Visualizes where the driver will rejoin the track if they pit NOW.
 * Shows a "Ghost Car" relative to other drivers on track.
 */

import { useMemo, type FC } from 'react';
import type { DriverState } from '../types';

interface PitRejoinVisualizerProps {
    driver: DriverState;
    allDrivers: DriverState[];
}

const PitRejoinVisualizer: FC<PitRejoinVisualizerProps> = ({ driver, allDrivers }) => {
    // We need relative positions. 
    // Ideally we use track progress (0-1).
    // If we don't have track progress, we can use gaps, but that's harder to visualize linearly without a referece.

    // For this visualizer, let's create a "Window" around the driver.
    // +10s ahead, -30s behind (covering the pit loss).

    const pitLoss = 22.0; // Seconds (TODO: Get from track config)

    // Calculate relative deltas to our driver
    const nearbyDrivers = useMemo(() => {
        return allDrivers
            .filter(d => d.driver_number !== driver.driver_number)
            .map(d => {
                // Approximate time gap based on lap time and position
                // This is tricky without precise gap data for everyone matrix style.
                // We will rely on 'gap_to_leader' diffs if available.
                let gapToUs = 0.0;

                if (driver.gap_to_leader !== null && d.gap_to_leader !== null) {
                    gapToUs = d.gap_to_leader - driver.gap_to_leader;
                } else if (d.position !== null && driver.position !== null) {
                    // Fallback to simple position delta * 1.5s
                    gapToUs = (d.position - driver.position) * 1.5;
                } else {
                    gapToUs = 999.0;
                }

                return { ...d, gapToUs };
            })
            .filter(d => d.gapToUs > -5.0 && d.gapToUs < (pitLoss + 10.0)); // Filter relevant window
    }, [allDrivers, driver]);



    // Our position is at 0 (left-ish)
    // Pit Rejoin is at +pitLoss (right-ish)

    // Actually, if we pit, we lose time. So we fall BEHIND.
    // Time increases as we fall back?
    // Gap to leader increases.
    // So if we are at Gap=10.
    // After pit we are at Gap=32.
    // Drivers with Gap=20 are AHEAD of us on track (physically ahead, but we are chasing).
    // Wait. Gap=0 is Leader. Gap=10 is +10s behind.
    // If I pit, I go from +10s to +32s.
    // A driver at +20s is currently BEHIND me. 
    // After I pit (to +32), the driver at +20s is AHEAD of me.

    // So "Rejoin Spot" is +pitLoss seconds "Behind" my current spot.

    return (
        <div style={{ marginTop: 'var(--space-md)', padding: 'var(--space-sm)', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-secondary)' }}>PIT REJOIN PREDICTION</span>
                {driver.rejoin_traffic_severity > 0.6 && (
                    <span style={{ fontSize: '0.7rem', color: 'var(--status-red)', fontWeight: 'bold' }}>TRAFFIC WARNING</span>
                )}
            </div>

            <div style={{ position: 'relative', height: '40px', background: 'rgba(0,0,0,0.3)', borderRadius: '4px', overflow: 'hidden' }}>
                {/* Track Line */}
                <div style={{ position: 'absolute', top: '50%', width: '100%', height: '2px', background: 'var(--text-muted)', opacity: 0.3 }} />

                {/* Me (Current) */}
                <div
                    style={{
                        position: 'absolute',
                        left: '10%',
                        top: '50%',
                        transform: 'translate(-50%, -50%)',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center'
                    }}
                >
                    <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: `#${driver.team_colour}`, border: '2px solid white', boxShadow: '0 0 4px white' }} />
                    <span style={{ fontSize: '0.6rem', marginTop: '2px' }}>YOU</span>
                </div>

                {/* Ghost Car (Rejoin) */}
                <div
                    style={{
                        position: 'absolute',
                        left: '80%', // Assume ~22s loss fits here
                        top: '50%',
                        transform: 'translate(-50%, -50%)',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        opacity: 0.7
                    }}
                >
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', border: `2px dashed #${driver.team_colour}`, background: 'transparent' }} />
                    <span style={{ fontSize: '0.6rem', marginTop: '2px' }}>EXIT</span>
                </div>

                {/* Traffic Arrow */}
                <div style={{ position: 'absolute', left: '10%', right: '20%', top: '50%', height: '1px', borderTop: '1px dashed rgba(255,255,255,0.2)' }} />
                <div style={{ position: 'absolute', left: '45%', top: '30%', fontSize: '0.6rem', color: 'var(--text-muted)' }}>PIT LOSS (~22s)</div>

                {/* Other Drivers */}
                {nearbyDrivers.map(d => {
                    // d.gapToUs is relative to me NOW.
                    // If d.gapToUs = +10s (they are 10s behind me).
                    // My Rejoin is at +22s.
                    // So they will be AHEAD of my rejoin.
                    // Position on bar:
                    // Me = 0s
                    // Rejoin = 22s
                    // Bar Range = -5s to 30s?

                    const timeDelta = d.gapToUs; // Positive = Behind us

                    // Map timeDelta to %
                    // 0s -> 10% (Me)
                    // 22s -> 80% (Exit)
                    // Scale: 22s = 70% width -> 1s = 3.18%
                    const percent = 10 + (timeDelta * 3.18);

                    if (percent < 0 || percent > 100) return null;

                    return (
                        <div
                            key={d.driver_number}
                            style={{
                                position: 'absolute',
                                left: `${percent}%`,
                                top: '50%',
                                transform: 'translate(-50%, -50%)',
                                zIndex: 1
                            }}
                            title={`#${d.driver_number} ${d.name_acronym} (+${timeDelta.toFixed(1)}s)`}
                        >
                            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: `#${d.team_colour}` }} />
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default PitRejoinVisualizer;
