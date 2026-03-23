/**
 * Pit Rejoin Visualizer — Minimal Edition
 *
 * Shows where the driver will rejoin if they pit NOW.
 * Minimal bar with YOU→EXIT, position change badge, and traffic summary.
 */

import { useMemo, type FC } from 'react';
import type { DriverState } from '../types';

interface PitRejoinVisualizerProps {
    driver: DriverState;
    allDrivers: DriverState[];
}

const PitRejoinVisualizer: FC<PitRejoinVisualizerProps> = ({ driver, allDrivers }) => {
    const pitLoss = 22.0;

    const { carsInWindow, positionChange } = useMemo(() => {
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
                return gapToUs;
            });

        const inWindow = others.filter(g => g >= 0 && g <= pitLoss).length;
        return { carsInWindow: inWindow, positionChange: inWindow };
    }, [allDrivers, driver, pitLoss]);

    const trafficHigh = (driver.rejoin_traffic_severity ?? 0) > 0.6;
    const trafficMed = (driver.rejoin_traffic_severity ?? 0) > 0.35;
    const teamHex = driver.team_colour ? `#${driver.team_colour}` : '#888';
    const trafficColor = trafficHigh ? 'var(--status-red)' : trafficMed ? 'var(--status-amber)' : 'var(--status-green)';
    const trafficLabel = trafficHigh ? 'HIGH' : trafficMed ? 'MEDIUM' : 'CLEAR';

    return (
        <div style={{ marginTop: 'var(--space-md)', padding: 'var(--space-sm)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    Pit Rejoin Prediction
                </span>
                {positionChange > 0 ? (
                    <span style={{
                        fontSize: '0.62rem', fontFamily: 'var(--font-mono)', fontWeight: 700,
                        color: positionChange >= 2 ? 'var(--status-red)' : 'var(--status-amber)',
                        background: positionChange >= 2 ? 'rgba(248,81,73,0.12)' : 'rgba(210,153,34,0.12)',
                        padding: '1px 5px', borderRadius: '3px',
                    }}>
                        -{positionChange} POS
                    </span>
                ) : (
                    <span style={{
                        fontSize: '0.62rem', fontFamily: 'var(--font-mono)', fontWeight: 700,
                        color: 'var(--status-green)', background: 'rgba(63,185,80,0.1)',
                        padding: '1px 5px', borderRadius: '3px',
                    }}>
                        CLEAR
                    </span>
                )}
            </div>

            {/* Stats row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '8px' }}>
                <div>
                    <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Pit Loss</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)' }}>~{pitLoss}s</div>
                </div>
                <div>
                    <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Traffic</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', fontWeight: 700, color: trafficColor }}>{trafficLabel}</div>
                </div>
                <div>
                    <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Cars In Window</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', fontWeight: 700, color: carsInWindow > 0 ? 'var(--status-amber)' : 'var(--status-green)' }}>{carsInWindow}</div>
                </div>
            </div>

            {/* Minimal bar: YOU → EXIT */}
            <div style={{ position: 'relative', height: '20px', background: 'rgba(0,0,0,0.25)', borderRadius: '10px', overflow: 'hidden' }}>
                {/* Fill bar */}
                <div style={{
                    position: 'absolute', top: 0, left: 0, height: '100%', width: '100%',
                    background: `linear-gradient(90deg, ${teamHex}33 0%, ${trafficColor}22 100%)`,
                    borderRadius: '10px',
                }} />
                {/* YOU label */}
                <span style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', fontSize: '0.55rem', fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.04em' }}>
                    YOU
                </span>
                {/* Team dot */}
                <div style={{
                    position: 'absolute', left: '36px', top: '50%', transform: 'translateY(-50%)',
                    width: '8px', height: '8px', borderRadius: '50%', background: teamHex, border: '1.5px solid white',
                }} />
                {/* EXIT label */}
                <span style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', fontSize: '0.55rem', fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.04em' }}>
                    EXIT
                </span>
                {/* Dashed exit marker */}
                <div style={{
                    position: 'absolute', right: '36px', top: '50%', transform: 'translateY(-50%)',
                    width: '8px', height: '8px', borderRadius: '50%', border: `1.5px dashed ${teamHex}`, opacity: 0.6,
                }} />
            </div>
        </div>
    );
};

export default PitRejoinVisualizer;
