/**
 * Strategy Panel Component
 *
 * Displays pit strategy recommendations, pit window visualization,
 * and threat indicators for the selected (or leading) driver.
 *
 * Features:
 * - Real-time pit recommendations (PIT_NOW, CONSIDER, EXTEND)
 * - Visual pit window timeline
 * - Undercut/overcut threat badges
 * - Degradation and cliff risk display
 *
 * @module components/StrategyPanel
 */

import { useMemo, type FC, type CSSProperties } from 'react';
import type { DriverState } from '../types';
import TyreLifeChart from './TyreLifeChart';
import PitRejoinVisualizer from './PitRejoinVisualizer';

// =============================================================================
// Types
// =============================================================================

interface StrategyPanelProps {
    /** Array of drivers sorted by position */
    drivers: DriverState[];
    /** Selected driver number or driver object */
    selectedDriver?: DriverState | number | null;
    /** Use compact layout for side panels */
    compact?: boolean;
}

type RecommendationType = 'PIT_NOW' | 'CONSIDER_PIT' | 'EXTEND_STINT' | string;

interface RecommendationStyle {
    bg: string;
    border: string;
    text: string;
    short: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get visual style for a pit recommendation.
 */
function getRecommendationStyle(rec: RecommendationType | undefined): RecommendationStyle {
    switch (rec) {
        case 'PIT_NOW':
            return { bg: 'rgba(255, 68, 68, 0.2)', border: 'var(--status-red)', text: '🔴 PIT NOW', short: 'PIT' };
        case 'CONSIDER_PIT':
            return { bg: 'rgba(255, 193, 7, 0.2)', border: 'var(--status-yellow)', text: '🟡 CONSIDER PIT', short: 'CONSIDER' };
        case 'EXTEND_STINT':
            return { bg: 'rgba(76, 217, 100, 0.2)', border: 'var(--status-green)', text: '🟢 EXTEND', short: 'EXTEND' };
        default:
            return { bg: 'rgba(76, 217, 100, 0.2)', border: 'var(--status-green)', text: '🟢 STAY OUT', short: 'STAY' };
    }
}

/**
 * Get color for degradation value.
 */
function getDegradationColor(slope: number | undefined): string {
    if (!slope) return 'var(--status-green)';
    if (slope > 0.08) return 'var(--status-red)';
    if (slope > 0.05) return 'var(--status-yellow)';
    return 'var(--status-green)';
}

/**
 * Get color for cliff risk value.
 */
function getCliffRiskColor(risk: number | undefined): string {
    if (!risk) return 'var(--status-green)';
    if (risk > 0.7) return 'var(--status-red)';
    if (risk > 0.4) return 'var(--status-yellow)';
    return 'var(--status-green)';
}

// =============================================================================
// Sub-Components
// =============================================================================

interface CompactStrategyProps {
    driver: DriverState;
    recStyle: RecommendationStyle;
}

/**
 * Compact strategy display for side panels.
 */
const CompactStrategy: FC<CompactStrategyProps> = ({ driver, recStyle }) => (
    <div className="card" style={{ padding: 'var(--space-sm)' }}>
        <div
            style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 'var(--space-xs)',
            }}
        >
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Strategy</span>
            <span style={{ fontSize: '0.7rem', fontWeight: 600 }}>{driver.name_acronym}</span>
        </div>

        {/* Recommendation */}
        <div
            style={{
                padding: 'var(--space-xs) var(--space-sm)',
                background: recStyle.bg,
                borderLeft: `3px solid ${recStyle.border}`,
                borderRadius: 'var(--radius-xs)',
                marginBottom: 'var(--space-xs)',
            }}
        >
            <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{recStyle.text}</div>
            {driver.pit_confidence && driver.pit_confidence > 0 && (
                <div style={{ fontSize: '0.65rem', opacity: 0.7 }}>{(driver.pit_confidence * 100).toFixed(0)}% confidence</div>
            )}
        </div>

        {/* Stats grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)', fontSize: '0.7rem' }}>
            <div>
                <span style={{ color: 'var(--text-muted)' }}>Tyre: </span>
                <span>
                    {driver.compound?.charAt(0) || '?'}
                    {driver.lap_in_stint || 0}
                </span>
            </div>
            <div>
                <span style={{ color: 'var(--text-muted)' }}>Deg: </span>
                <span style={{ color: getDegradationColor(driver.deg_slope) }}>
                    {((driver.deg_slope || 0) * 1000).toFixed(0)}ms
                </span>
            </div>
            <div>
                <span style={{ color: 'var(--text-muted)' }}>Cliff: </span>
                <span style={{ color: getCliffRiskColor(driver.cliff_risk) }}>
                    {((driver.cliff_risk || 0) * 100).toFixed(0)}%
                </span>
            </div>
            <div>
                <span style={{ color: 'var(--text-muted)' }}>Window: </span>
                <span>L{driver.pit_window_ideal || '-'}</span>
            </div>
        </div>

        {/* Threat badges */}
        <div style={{ display: 'flex', gap: 'var(--space-xs)', marginTop: 'var(--space-xs)' }}>
            {driver.undercut_threat && (
                <span style={{ fontSize: '0.6rem', color: 'var(--accent-orange)' }}>⚠️ UNDERCUT</span>
            )}
            {driver.overcut_opportunity && (
                <span style={{ fontSize: '0.6rem', color: 'var(--accent-cyan)' }}>💡 OVERCUT</span>
            )}
        </div>
    </div>
);

interface PitWindowVisualizationProps {
    driver: DriverState;
    inWindow: boolean;
    windowWidth: number;
}

/**
 * Visual pit window timeline.
 */
const PitWindowVisualization: FC<PitWindowVisualizationProps> = ({ driver, inWindow, windowWidth }) => (
    <div style={{ marginBottom: 'var(--space-md)' }}>
        <div style={{ fontSize: '0.85rem', marginBottom: 'var(--space-xs)', color: 'var(--text-secondary)' }}>
            Pit Window: Laps {driver.pit_window_min} - {driver.pit_window_max}
        </div>
        <div
            style={{
                position: 'relative',
                height: '24px',
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-sm)',
                overflow: 'hidden',
            }}
        >
            {/* Window range */}
            <div
                style={{
                    position: 'absolute',
                    left: '10%',
                    width: '80%',
                    height: '100%',
                    background: 'var(--accent-cyan)',
                    opacity: 0.3,
                }}
            />
            {/* Ideal lap marker */}
            <div
                style={{
                    position: 'absolute',
                    left: '45%',
                    width: '4px',
                    height: '100%',
                    background: 'var(--accent-cyan)',
                    boxShadow: '0 0 8px var(--accent-cyan)',
                }}
            />
            {/* Current lap indicator */}
            {inWindow && (
                <div
                    style={{
                        position: 'absolute',
                        left: `${(((driver.current_lap || 0) - (driver.pit_window_min || 0)) / Math.max(windowWidth, 1)) * 80 + 10}%`,
                        top: '50%',
                        transform: 'translate(-50%, -50%)',
                        width: '8px',
                        height: '8px',
                        background: 'white',
                        borderRadius: '50%',
                        boxShadow: '0 0 6px white',
                    }}
                />
            )}
        </div>
        <div
            style={{
                display: 'flex',
                justifyContent: 'center',
                fontSize: '0.75rem',
                marginTop: 'var(--space-xs)',
                color: 'var(--accent-cyan)',
            }}
        >
            Ideal: Lap {driver.pit_window_ideal}
        </div>
    </div>
);

// =============================================================================
// Main Component
// =============================================================================

/**
 * Strategy panel with pit recommendations and threat indicators.
 *
 * Displays strategy information for the selected driver or the leader.
 */
const StrategyPanel: FC<StrategyPanelProps> = ({ drivers, selectedDriver, compact = false }) => {
    // Select driver to display
    const driver = useMemo((): DriverState | null => {
        if (!drivers || drivers.length === 0) return null;

        if (selectedDriver) {
            const driverId = typeof selectedDriver === 'number' ? selectedDriver : selectedDriver.driver_number;
            return drivers.find((d) => d.driver_number === driverId) || null;
        }

        return drivers[0]; // Leader
    }, [drivers, selectedDriver]);

    // Empty state
    if (!driver) {
        return (
            <div className="card" style={{ padding: compact ? 'var(--space-sm)' : undefined }}>
                <h3 className="card-title" style={{ fontSize: compact ? '0.7rem' : undefined }}>
                    Strategy
                </h3>
                <p className="text-muted" style={{ fontSize: '0.75rem' }}>
                    No driver selected
                </p>
            </div>
        );
    }

    const recStyle = getRecommendationStyle(driver.pit_recommendation);
    const windowWidth = (driver.pit_window_max || 0) - (driver.pit_window_min || 0);
    const inWindow =
        (driver.current_lap || 0) >= (driver.pit_window_min || 0) &&
        (driver.current_lap || 0) <= (driver.pit_window_max || 0);

    // Compact layout
    if (compact) {
        return <CompactStrategy driver={driver} recStyle={recStyle} />;
    }

    const cardStyle: CSSProperties = {};

    return (
        <div className="card" style={cardStyle}>
            <h3 className="card-title">
                Strategy - #{driver.driver_number} {driver.name_acronym}
            </h3>

            {/* Main Recommendation */}
            <div
                style={{
                    padding: 'var(--space-md)',
                    background: recStyle.bg,
                    borderLeft: `4px solid ${recStyle.border}`,
                    borderRadius: 'var(--radius-sm)',
                    marginBottom: 'var(--space-md)',
                }}
            >
                <div
                    style={{
                        fontFamily: 'var(--font-display)',
                        fontSize: '1.2rem',
                        fontWeight: 700,
                        marginBottom: 'var(--space-xs)',
                    }}
                >
                    {recStyle.text}
                </div>
                <div style={{ fontSize: '0.85rem', opacity: 0.9 }}>{driver.pit_reason || 'Evaluating strategy...'}</div>
                {(driver.pit_confidence || 0) > 0 && (
                    <div style={{ fontSize: '0.75rem', marginTop: 'var(--space-xs)', opacity: 0.7 }}>
                        Confidence: {((driver.pit_confidence || 0) * 100).toFixed(0)}%
                    </div>
                )}
            </div>

            {/* Pit Window */}
            {driver.pit_window_ideal && driver.pit_window_ideal > 0 && (
                <PitWindowVisualization driver={driver} inWindow={inWindow} windowWidth={windowWidth} />
            )}

            {/* Threat Indicators */}
            <div style={{ display: 'flex', gap: 'var(--space-sm)', flexWrap: 'wrap' }}>
                {driver.undercut_threat && (
                    <div
                        style={{
                            padding: 'var(--space-xs) var(--space-sm)',
                            background: 'rgba(255, 149, 0, 0.2)',
                            border: '1px solid var(--accent-orange)',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                        }}
                    >
                        ⚠️ UNDERCUT THREAT
                    </div>
                )}
                {driver.overcut_opportunity && (
                    <div
                        style={{
                            padding: 'var(--space-xs) var(--space-sm)',
                            background: 'rgba(0, 210, 190, 0.2)',
                            border: '1px solid var(--accent-cyan)',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                        }}
                    >
                        💡 OVERCUT VIABLE
                    </div>
                )}
            </div>

            {/* Tyre Summary */}
            <div
                style={{
                    marginTop: 'var(--space-md)',
                    padding: 'var(--space-sm)',
                    background: 'var(--bg-tertiary)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.85rem',
                }}
            >
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Tyre Age:</span>
                    <span>{driver.tyre_age || driver.lap_in_stint || 0} laps</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Degradation:</span>
                    <span style={{ color: getDegradationColor(driver.deg_slope) }}>
                        {((driver.deg_slope || 0) * 1000).toFixed(0)} ms/lap
                    </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Cliff Risk:</span>
                    <span style={{ color: getCliffRiskColor(driver.cliff_risk) }}>
                        {((driver.cliff_risk || 0) * 100).toFixed(0)}%
                    </span>
                </div>
            </div>

            {/* Tyre Life Chart */}
            <TyreLifeChart driver={driver} />

            {/* Pit Rejoin Visualizer */}
            <PitRejoinVisualizer driver={driver} allDrivers={drivers} />
        </div>
    );
};

export default StrategyPanel;
