/**
 * Driver table component with live data.
 * Displays position, driver info, gaps, lap times, tyre info, and ML predictions.
 */

import { useMemo } from 'react'

function DriverTable({ drivers, fastestLap }) {
    // Find fastest lap time
    const fastestLapTime = useMemo(() => {
        if (!drivers || drivers.length === 0) return null
        const times = drivers
            .map(d => d.last_lap_time)
            .filter(t => t && t > 0)
        return times.length > 0 ? Math.min(...times) : null
    }, [drivers])

    const formatTime = (seconds) => {
        if (!seconds || seconds <= 0) return '-'
        const mins = Math.floor(seconds / 60)
        const secs = (seconds % 60).toFixed(3)
        return mins > 0 ? `${mins}:${secs.padStart(6, '0')}` : secs
    }

    const formatGap = (gap) => {
        if (gap === null || gap === undefined) return '-'
        if (gap === 0) return 'LEADER'
        return `+${gap.toFixed(3)}`
    }

    const formatInterval = (interval) => {
        if (interval === null || interval === undefined) return '-'
        return `+${interval.toFixed(3)}`
    }

    const getTyreClass = (compound) => {
        if (!compound) return ''
        return compound.toLowerCase()
    }

    const getTyreLabel = (compound) => {
        if (!compound) return '?'
        return compound.charAt(0)
    }

    // Format degradation slope with color coding
    const formatDegSlope = (slope) => {
        if (!slope || slope === 0) return { text: '-', color: 'var(--text-muted)' }
        const text = `${(slope * 1000).toFixed(0)}ms`
        // Color based on severity: green (low) -> yellow -> red (high)
        let color = 'var(--status-green)'
        if (slope > 0.05) color = 'var(--status-yellow)'
        if (slope > 0.08) color = 'var(--accent-orange)'
        if (slope > 0.10) color = 'var(--status-red)'
        return { text, color }
    }

    // Format cliff risk as visual indicator
    const formatCliffRisk = (risk) => {
        if (!risk || risk === 0) return null
        const width = Math.min(100, Math.round(risk * 100))
        let color = 'var(--status-green)'
        if (risk > 0.5) color = 'var(--status-yellow)'
        if (risk > 0.8) color = 'var(--status-red)'
        return { width, color }
    }

    if (!drivers || drivers.length === 0) {
        return (
            <div className="card" style={{ textAlign: 'center', padding: 'var(--space-2xl)' }}>
                <p className="text-muted">No driver data available</p>
            </div>
        )
    }

    return (
        <div className="card" style={{ overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto' }}>
                <table className="driver-table">
                    <thead>
                        <tr>
                            <th style={{ width: '50px' }}>Pos</th>
                            <th>Driver</th>
                            <th style={{ width: '90px' }}>Gap</th>
                            <th style={{ width: '100px' }}>Last Lap</th>
                            <th style={{ width: '80px' }}>Tyre</th>
                            <th style={{ width: '70px' }}>Deg</th>
                            <th style={{ width: '100px' }}>Pred +5</th>
                            <th style={{ width: '60px' }}>Risk</th>
                        </tr>
                    </thead>
                    <tbody>
                        {drivers.map((driver, index) => {
                            const isPersonalBest = driver.last_lap_time &&
                                driver.best_lap_time &&
                                driver.last_lap_time === driver.best_lap_time
                            const isFastestLap = driver.last_lap_time === fastestLapTime
                            const deg = formatDegSlope(driver.deg_slope)
                            const cliff = formatCliffRisk(driver.cliff_risk)
                            const pred5 = driver.predicted_pace && driver.predicted_pace.length >= 5
                                ? driver.predicted_pace[4]
                                : null

                            return (
                                <tr key={driver.driver_number} style={{ animationDelay: `${index * 30}ms` }}>
                                    <td className="position-cell">{driver.position}</td>
                                    <td>
                                        <div className="driver-cell">
                                            <div
                                                className="team-color"
                                                style={{ backgroundColor: `#${driver.team_colour || 'FFFFFF'}` }}
                                            />
                                            <div>
                                                <div className="driver-name">{driver.name_acronym || `#${driver.driver_number}`}</div>
                                                <div className="driver-team">{driver.team_name || 'Unknown'}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="gap-cell">
                                        {driver.position === 1 ? (
                                            <span style={{ color: 'var(--accent-cyan)' }}>LEADER</span>
                                        ) : (
                                            formatGap(driver.gap_to_leader)
                                        )}
                                    </td>
                                    <td className={`lap-time-cell ${isFastestLap ? 'best' : isPersonalBest ? 'personal-best' : ''}`}>
                                        {formatTime(driver.last_lap_time)}
                                    </td>
                                    <td>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
                                            <span className={`tyre-badge ${getTyreClass(driver.compound)}`}>
                                                {getTyreLabel(driver.compound)}
                                            </span>
                                            <span className="tyre-age">L{driver.lap_in_stint || driver.tyre_age || 0}</span>
                                        </div>
                                    </td>
                                    {/* Degradation slope column */}
                                    <td style={{
                                        fontFamily: 'var(--font-display)',
                                        fontSize: '0.8rem',
                                        color: deg.color
                                    }}>
                                        {deg.text}
                                    </td>
                                    {/* Predicted pace in 5 laps */}
                                    <td className="lap-time-cell" style={{ opacity: 0.8 }}>
                                        {pred5 ? formatTime(pred5) : '-'}
                                    </td>
                                    {/* Cliff risk indicator */}
                                    <td>
                                        {cliff ? (
                                            <div style={{
                                                width: '40px',
                                                height: '6px',
                                                background: 'var(--bg-tertiary)',
                                                borderRadius: '3px',
                                                overflow: 'hidden'
                                            }}>
                                                <div style={{
                                                    width: `${cliff.width}%`,
                                                    height: '100%',
                                                    background: cliff.color,
                                                    transition: 'width 0.3s ease'
                                                }} />
                                            </div>
                                        ) : (
                                            <span className="text-muted">-</span>
                                        )}
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

export default DriverTable

