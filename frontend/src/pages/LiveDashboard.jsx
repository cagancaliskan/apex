/**
 * Live Dashboard page - main race monitoring view.
 */

import { useMemo, useState } from 'react'
import { Flag, Timer, Users, Gauge, Radio, AlertCircle } from 'lucide-react'
import DriverTable from '../components/DriverTable'
import MetricCard from '../components/MetricCard'
import RaceMessages from '../components/RaceMessages'
import StrategyPanel from '../components/StrategyPanel'

function LiveDashboard({ raceState, isPolling }) {
    const [selectedDriver, setSelectedDriver] = useState(null)

    // Calculate statistics
    const stats = useMemo(() => {
        if (!raceState?.drivers) return null

        const drivers = raceState.drivers
        const lapTimes = drivers
            .filter(d => d.last_lap_time && d.last_lap_time > 0)
            .map(d => d.last_lap_time)

        return {
            leader: drivers.find(d => d.position === 1),
            fastestLap: lapTimes.length > 0 ? Math.min(...lapTimes) : null,
            avgLapTime: lapTimes.length > 0
                ? lapTimes.reduce((a, b) => a + b, 0) / lapTimes.length
                : null,
            retiredCount: drivers.filter(d => d.retired).length,
            pitStops: raceState.recent_pits?.length || 0,
        }
    }, [raceState])

    const formatLapTime = (seconds) => {
        if (!seconds) return '-'
        const mins = Math.floor(seconds / 60)
        const secs = (seconds % 60).toFixed(3)
        return mins > 0 ? `${mins}:${secs.padStart(6, '0')}` : secs
    }

    const getFlagStatus = () => {
        if (raceState.red_flag) return { label: 'RED FLAG', className: 'red' }
        if (raceState.safety_car) return { label: 'SAFETY CAR', className: 'sc' }
        if (raceState.virtual_safety_car) return { label: 'VSC', className: 'vsc' }
        if (raceState.flags?.includes('YELLOW')) return { label: 'YELLOW', className: 'yellow' }
        return { label: 'GREEN', className: 'green' }
    }

    const flagStatus = getFlagStatus()

    return (
        <div className="animate-fade-in">
            {/* Header */}
            <header className="header">
                <div className="header-left">
                    <div className="session-info">
                        <div className="circuit">
                            {raceState.track_name || 'Loading...'}
                        </div>
                        <div className="session-type">
                            {raceState.session_name || 'Race'} • {raceState.country}
                        </div>
                    </div>
                </div>

                <div className="header-right">
                    <div className={`status-badge ${flagStatus.className}`}>
                        <Flag size={12} />
                        {flagStatus.label}
                    </div>

                    <div className="lap-counter">
                        <span className="current">{raceState.current_lap || 0}</span>
                        <span className="total">/{raceState.total_laps || '?'}</span>
                    </div>

                    {isPolling && (
                        <div className="status-badge green" style={{ animation: 'pulse 2s infinite' }}>
                            <Radio size={12} />
                            LIVE
                        </div>
                    )}
                </div>
            </header>

            {/* Metrics Grid */}
            <div className="metrics-grid">
                <MetricCard
                    label="Leader"
                    value={stats?.leader?.name_acronym || '-'}
                    color="cyan"
                    icon={Users}
                />
                <MetricCard
                    label="Fastest Lap"
                    value={formatLapTime(stats?.fastestLap)}
                    color="magenta"
                    icon={Timer}
                />
                <MetricCard
                    label="Current Lap"
                    value={raceState.current_lap || 0}
                    color="cyan"
                    icon={Gauge}
                />
                <MetricCard
                    label="Pit Stops"
                    value={stats?.pitStops || 0}
                    color="purple"
                    icon={AlertCircle}
                />
            </div>

            {/* Main Content Grid */}
            <div className="dashboard-grid">
                {/* Driver Table */}
                <div>
                    <h3 className="mb-md" style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-tertiary)',
                        letterSpacing: '0.1em',
                        textTransform: 'uppercase'
                    }}>
                        Race Classification
                    </h3>
                    <DriverTable
                        drivers={raceState.drivers}
                        fastestLap={stats?.fastestLap}
                        onDriverSelect={setSelectedDriver}
                        selectedDriver={selectedDriver}
                    />
                </div>

                {/* Side Panel */}
                <div className="flex flex-col gap-lg">
                    {/* Strategy Panel */}
                    <StrategyPanel
                        drivers={raceState.drivers}
                        selectedDriver={selectedDriver}
                    />

                    {/* Race Control Messages */}
                    <div className="card card-glow">
                        <h4 className="mb-md" style={{
                            fontSize: '0.75rem',
                            color: 'var(--text-tertiary)',
                            letterSpacing: '0.1em',
                            textTransform: 'uppercase'
                        }}>
                            Race Control
                        </h4>
                        <RaceMessages messages={raceState.recent_messages} />
                    </div>

                    {/* Recent Pit Stops */}
                    <div className="card card-glow">
                        <h4 className="mb-md" style={{
                            fontSize: '0.75rem',
                            color: 'var(--text-tertiary)',
                            letterSpacing: '0.1em',
                            textTransform: 'uppercase'
                        }}>
                            Recent Pit Stops
                        </h4>
                        {raceState.recent_pits?.length > 0 ? (
                            <div>
                                {raceState.recent_pits.slice(0, 5).map((pit, index) => {
                                    const driver = raceState.drivers?.find(d => d.driver_number === pit.driver_number)
                                    return (
                                        <div
                                            key={index}
                                            className="flex items-center justify-between"
                                            style={{
                                                padding: 'var(--space-sm)',
                                                borderBottom: '1px solid rgba(255, 255, 255, 0.03)'
                                            }}
                                        >
                                            <div className="flex items-center gap-sm">
                                                <div
                                                    style={{
                                                        width: '4px',
                                                        height: '20px',
                                                        borderRadius: '2px',
                                                        backgroundColor: `#${driver?.team_colour || 'FFFFFF'}`
                                                    }}
                                                />
                                                <span className="text-sm">{driver?.name_acronym || `#${pit.driver_number}`}</span>
                                            </div>
                                            <div className="text-muted text-xs">
                                                Lap {pit.lap_number} • {pit.pit_duration?.toFixed(1)}s
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>
                        ) : (
                            <div className="text-muted text-sm">No pit stops yet</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

export default LiveDashboard
