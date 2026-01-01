/**
 * Strategy Panel component showing pit recommendations and strategy info.
 * Displays for the selected driver or current leader.
 */

import { useMemo } from 'react'

function StrategyPanel({ drivers, selectedDriver }) {
    // Select driver to display (selected or leader)
    const driver = useMemo(() => {
        if (!drivers || drivers.length === 0) return null
        if (selectedDriver) {
            const driverId = selectedDriver.driver_number || selectedDriver
            return drivers.find(d => d.driver_number === driverId)
        }
        return drivers[0] // Leader
    }, [drivers, selectedDriver])

    if (!driver) {
        return (
            <div className="card">
                <h3 className="card-title">Strategy</h3>
                <p className="text-muted">No driver selected</p>
            </div>
        )
    }

    const getRecommendationStyle = (rec) => {
        switch (rec) {
            case 'PIT_NOW':
                return { bg: 'rgba(255, 68, 68, 0.2)', border: 'var(--status-red)', text: '🔴 PIT NOW' }
            case 'CONSIDER_PIT':
                return { bg: 'rgba(255, 193, 7, 0.2)', border: 'var(--status-yellow)', text: '🟡 CONSIDER PIT' }
            case 'EXTEND_STINT':
                return { bg: 'rgba(76, 217, 100, 0.2)', border: 'var(--status-green)', text: '🟢 EXTEND STINT' }
            default:
                return { bg: 'rgba(76, 217, 100, 0.2)', border: 'var(--status-green)', text: '🟢 STAY OUT' }
        }
    }

    const recStyle = getRecommendationStyle(driver.pit_recommendation)

    const windowWidth = driver.pit_window_max - driver.pit_window_min
    const inWindow = driver.current_lap >= driver.pit_window_min &&
        driver.current_lap <= driver.pit_window_max

    return (
        <div className="card">
            <h3 className="card-title">
                Strategy - #{driver.driver_number} {driver.name_acronym}
            </h3>

            {/* Main Recommendation */}
            <div style={{
                padding: 'var(--space-md)',
                background: recStyle.bg,
                borderLeft: `4px solid ${recStyle.border}`,
                borderRadius: 'var(--radius-sm)',
                marginBottom: 'var(--space-md)',
            }}>
                <div style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: '1.2rem',
                    fontWeight: 700,
                    marginBottom: 'var(--space-xs)',
                }}>
                    {recStyle.text}
                </div>
                <div style={{ fontSize: '0.85rem', opacity: 0.9 }}>
                    {driver.pit_reason || 'Evaluating strategy...'}
                </div>
                {driver.pit_confidence > 0 && (
                    <div style={{
                        fontSize: '0.75rem',
                        marginTop: 'var(--space-xs)',
                        opacity: 0.7
                    }}>
                        Confidence: {(driver.pit_confidence * 100).toFixed(0)}%
                    </div>
                )}
            </div>

            {/* Pit Window Visualization */}
            {driver.pit_window_ideal > 0 && (
                <div style={{ marginBottom: 'var(--space-md)' }}>
                    <div style={{
                        fontSize: '0.85rem',
                        marginBottom: 'var(--space-xs)',
                        color: 'var(--text-secondary)',
                    }}>
                        Pit Window: Laps {driver.pit_window_min} - {driver.pit_window_max}
                    </div>
                    <div style={{
                        position: 'relative',
                        height: '24px',
                        background: 'var(--bg-tertiary)',
                        borderRadius: 'var(--radius-sm)',
                        overflow: 'hidden',
                    }}>
                        {/* Window range */}
                        <div style={{
                            position: 'absolute',
                            left: '10%',
                            width: '80%',
                            height: '100%',
                            background: 'var(--accent-cyan)',
                            opacity: 0.3,
                        }} />
                        {/* Ideal lap marker */}
                        <div style={{
                            position: 'absolute',
                            left: '45%',
                            width: '4px',
                            height: '100%',
                            background: 'var(--accent-cyan)',
                            boxShadow: '0 0 8px var(--accent-cyan)',
                        }} />
                        {/* Current lap indicator */}
                        {inWindow && (
                            <div style={{
                                position: 'absolute',
                                left: `${((driver.current_lap - driver.pit_window_min) / Math.max(windowWidth, 1)) * 80 + 10}%`,
                                top: '50%',
                                transform: 'translate(-50%, -50%)',
                                width: '8px',
                                height: '8px',
                                background: 'white',
                                borderRadius: '50%',
                                boxShadow: '0 0 6px white',
                            }} />
                        )}
                    </div>
                    <div style={{
                        display: 'flex',
                        justifyContent: 'center',
                        fontSize: '0.75rem',
                        marginTop: 'var(--space-xs)',
                        color: 'var(--accent-cyan)',
                    }}>
                        Ideal: Lap {driver.pit_window_ideal}
                    </div>
                </div>
            )}

            {/* Threat Indicators */}
            <div style={{ display: 'flex', gap: 'var(--space-sm)', flexWrap: 'wrap' }}>
                {driver.undercut_threat && (
                    <div style={{
                        padding: 'var(--space-xs) var(--space-sm)',
                        background: 'rgba(255, 149, 0, 0.2)',
                        border: '1px solid var(--accent-orange)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                    }}>
                        ⚠️ UNDERCUT THREAT
                    </div>
                )}
                {driver.overcut_opportunity && (
                    <div style={{
                        padding: 'var(--space-xs) var(--space-sm)',
                        background: 'rgba(0, 210, 190, 0.2)',
                        border: '1px solid var(--accent-cyan)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                    }}>
                        💡 OVERCUT VIABLE
                    </div>
                )}
            </div>

            {/* Tyre Summary */}
            <div style={{
                marginTop: 'var(--space-md)',
                padding: 'var(--space-sm)',
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.85rem',
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Tyre Age:</span>
                    <span>{driver.tyre_age || driver.lap_in_stint || 0} laps</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Degradation:</span>
                    <span style={{
                        color: driver.deg_slope > 0.08 ? 'var(--status-red)' :
                            driver.deg_slope > 0.05 ? 'var(--status-yellow)' : 'var(--status-green)'
                    }}>
                        {(driver.deg_slope * 1000).toFixed(0)} ms/lap
                    </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Cliff Risk:</span>
                    <span style={{
                        color: driver.cliff_risk > 0.7 ? 'var(--status-red)' :
                            driver.cliff_risk > 0.4 ? 'var(--status-yellow)' : 'var(--status-green)'
                    }}>
                        {(driver.cliff_risk * 100).toFixed(0)}%
                    </span>
                </div>
            </div>
        </div>
    )
}

export default StrategyPanel
