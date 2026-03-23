/**
 * Championship Simulator Page
 *
 * Multi-race Monte Carlo simulation that predicts WDC/WCC standings.
 * Users select a year and starting round, run the simulation, and
 * view probability-weighted championship predictions.
 *
 * Self-contained page with local state (same pattern as BacktestPage).
 */

import { useState, useEffect, type FC } from 'react';
import {
    DEFAULT_YEAR,
    AVAILABLE_YEARS,
    CHAMPIONSHIP_SIMULATION_COUNTS,
    API_CHAMPIONSHIP_CALENDAR,
    API_CHAMPIONSHIP_SIMULATE,
} from '../config/constants';
import type {
    RaceCalendarEntry,
    DriverChampionshipStanding,
    ConstructorChampionshipStanding,
    ChampionshipSimulationResult,
} from '../types';

// =============================================================================
// Sub-tab type
// =============================================================================

type ChampTab = 'wdc' | 'wcc';

// =============================================================================
// Component
// =============================================================================

const ChampionshipPage: FC = () => {
    // Configuration
    const [selectedYear, setSelectedYear] = useState(DEFAULT_YEAR);
    const [startRound, setStartRound] = useState(1);
    const [simCount, setSimCount] = useState(200);
    const [includeSprints, setIncludeSprints] = useState(true);

    // Calendar
    const [calendar, setCalendar] = useState<RaceCalendarEntry[]>([]);
    const [calendarLoading, setCalendarLoading] = useState(false);

    // Results
    const [result, setResult] = useState<ChampionshipSimulationResult | null>(null);
    const [isRunning, setIsRunning] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Sub-tab
    const [activeTab, setActiveTab] = useState<ChampTab>('wdc');

    // Fetch calendar on year change
    useEffect(() => {
        setCalendarLoading(true);
        fetch(API_CHAMPIONSHIP_CALENDAR(selectedYear))
            .then(r => r.json())
            .then(data => {
                const cal = data.calendar || [];
                setCalendar(cal);
                if (cal.length > 0) {
                    setStartRound(Math.max(1, Math.floor(cal.length / 2)));
                }
            })
            .catch(() => setCalendar([]))
            .finally(() => setCalendarLoading(false));
    }, [selectedYear]);

    const handleRunSimulation = async () => {
        setIsRunning(true);
        setError(null);
        setResult(null);
        try {
            const response = await fetch(API_CHAMPIONSHIP_SIMULATE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    year: selectedYear,
                    start_from_round: startRound,
                    n_simulations: simCount,
                    include_sprints: includeSprints,
                }),
            });
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `HTTP ${response.status}`);
            }
            const data: ChampionshipSimulationResult = await response.json();
            setResult(data);
        } catch (err) {
            setError(String(err instanceof Error ? err.message : err));
        } finally {
            setIsRunning(false);
        }
    };

    const completedRounds = calendar.filter(r => r.round_number < startRound).length;
    const remainingRounds = calendar.length - completedRounds;

    return (
        <div style={{ height: '100%', overflow: 'auto', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Configuration Panel */}
            <div style={{
                background: 'var(--bg-elevated)',
                borderRadius: '6px',
                padding: '12px 16px',
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                gap: '16px',
            }}>
                {/* Year */}
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    <span style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Year</span>
                    <select
                        value={selectedYear}
                        onChange={e => setSelectedYear(Number(e.target.value))}
                        style={selectStyle}
                    >
                        {AVAILABLE_YEARS.map(y => (
                            <option key={y} value={y}>{y}</option>
                        ))}
                    </select>
                </label>

                {/* Starting Round */}
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    <span style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>From Round</span>
                    <select
                        value={startRound}
                        onChange={e => setStartRound(Number(e.target.value))}
                        style={selectStyle}
                        disabled={calendarLoading || calendar.length === 0}
                    >
                        {calendar.map(r => (
                            <option key={r.round_number} value={r.round_number}>
                                R{r.round_number} — {r.event_name}
                            </option>
                        ))}
                    </select>
                </label>

                {/* Simulations */}
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    <span style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Sims</span>
                    <div style={{ display: 'flex', gap: '3px' }}>
                        {CHAMPIONSHIP_SIMULATION_COUNTS.map(n => (
                            <button
                                key={n}
                                onClick={() => setSimCount(n)}
                                style={{
                                    padding: '2px 8px',
                                    fontSize: '0.65rem',
                                    fontFamily: 'var(--font-mono)',
                                    fontWeight: simCount === n ? 700 : 400,
                                    background: simCount === n ? 'var(--color-info)' : 'rgba(255,255,255,0.06)',
                                    color: simCount === n ? '#000' : 'var(--text-secondary)',
                                    border: simCount === n ? 'none' : '1px solid rgba(255,255,255,0.1)',
                                    borderRadius: '3px',
                                    cursor: 'pointer',
                                }}
                            >
                                {n}
                            </button>
                        ))}
                    </div>
                </label>

                {/* Sprints */}
                <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                    <input
                        type="checkbox"
                        checked={includeSprints}
                        onChange={e => setIncludeSprints(e.target.checked)}
                        style={{ accentColor: 'var(--color-info)' }}
                    />
                    Sprints
                </label>

                {/* Run Button */}
                <button
                    onClick={handleRunSimulation}
                    disabled={isRunning || calendar.length === 0}
                    style={{
                        padding: '6px 20px',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        fontFamily: 'var(--font-mono)',
                        background: isRunning ? 'rgba(255,255,255,0.06)' : 'var(--color-accent)',
                        color: isRunning ? 'var(--text-muted)' : '#000',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: isRunning ? 'not-allowed' : 'pointer',
                        letterSpacing: '0.04em',
                        textTransform: 'uppercase',
                        marginLeft: 'auto',
                    }}
                >
                    {isRunning ? 'Simulating…' : 'Run Simulation'}
                </button>
            </div>

            {/* Season Timeline */}
            <div style={{
                background: 'var(--bg-elevated)',
                borderRadius: '6px',
                padding: '8px 16px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
            }}>
                <span style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', flexShrink: 0 }}>
                    Season
                </span>
                <div style={{ flex: 1, height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '4px', overflow: 'hidden', display: 'flex' }}>
                    <div style={{
                        width: calendar.length > 0 ? `${(completedRounds / calendar.length) * 100}%` : '0%',
                        background: 'var(--color-info)',
                        borderRadius: '4px 0 0 4px',
                        transition: 'width 0.3s ease',
                    }} />
                    <div style={{
                        width: calendar.length > 0 ? `${(remainingRounds / calendar.length) * 100}%` : '0%',
                        background: 'repeating-linear-gradient(45deg, rgba(255,255,255,0.08) 0px, rgba(255,255,255,0.08) 4px, transparent 4px, transparent 8px)',
                    }} />
                </div>
                <span style={{ fontSize: '0.65rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', flexShrink: 0 }}>
                    {completedRounds}/{calendar.length}
                </span>
            </div>

            {/* Error */}
            {error && (
                <div style={{
                    background: 'rgba(225, 6, 0, 0.1)',
                    border: '1px solid rgba(225, 6, 0, 0.3)',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    fontSize: '0.75rem',
                    color: 'var(--status-red)',
                }}>
                    {error}
                </div>
            )}

            {/* Results */}
            {result && (
                <>
                    {/* Tab Bar */}
                    <div style={{ display: 'flex', gap: '2px' }}>
                        <TabButton active={activeTab === 'wdc'} onClick={() => setActiveTab('wdc')} label="WDC — Drivers" />
                        <TabButton active={activeTab === 'wcc'} onClick={() => setActiveTab('wcc')} label="WCC — Constructors" />
                        <span style={{ marginLeft: 'auto', fontSize: '0.6rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', alignSelf: 'center' }}>
                            {result.n_simulations} sims · {result.elapsed_seconds}s
                        </span>
                    </div>

                    {/* Standings Table */}
                    {activeTab === 'wdc' ? (
                        <WDCTable standings={result.wdc} />
                    ) : (
                        <WCCTable standings={result.wcc} />
                    )}

                    {/* Probability Chart */}
                    {activeTab === 'wdc' && <ProbabilityChart standings={result.wdc.slice(0, 6)} />}
                    {activeTab === 'wcc' && <ProbabilityChartWCC standings={result.wcc.slice(0, 5)} />}
                </>
            )}

            {/* Empty state */}
            {!result && !isRunning && !error && (
                <div style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--text-muted)',
                    fontSize: '0.8rem',
                }}>
                    Select a year and starting round, then run the simulation.
                </div>
            )}
        </div>
    );
};

// =============================================================================
// Sub-components
// =============================================================================

const TabButton: FC<{ active: boolean; onClick: () => void; label: string }> = ({ active, onClick, label }) => (
    <button
        onClick={onClick}
        style={{
            padding: '6px 14px',
            fontSize: '0.7rem',
            fontWeight: active ? 700 : 500,
            fontFamily: 'var(--font-mono)',
            background: active ? 'var(--bg-elevated)' : 'transparent',
            color: active ? 'var(--text-primary)' : 'var(--text-muted)',
            border: 'none',
            borderBottom: active ? '2px solid var(--color-info)' : '2px solid transparent',
            cursor: 'pointer',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
        }}
    >
        {label}
    </button>
);

const WDCTable: FC<{ standings: DriverChampionshipStanding[] }> = ({ standings }) => (
    <div style={{ background: 'var(--bg-elevated)', borderRadius: '6px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.72rem', fontFamily: 'var(--font-mono)' }}>
            <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                    {['#', 'Driver', 'Team', 'Pts', 'Predicted', 'Range', 'P(Champ)', 'P(Top 3)'].map(h => (
                        <th key={h} style={thStyle}>{h}</th>
                    ))}
                </tr>
            </thead>
            <tbody>
                {standings.map((d, i) => (
                    <tr key={d.driver_number} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                        <td style={{ ...tdStyle, color: 'var(--text-muted)', width: '30px' }}>{i + 1}</td>
                        <td style={{ ...tdStyle, fontWeight: 600, color: 'var(--text-primary)' }}>
                            <span style={{ display: 'inline-block', width: '4px', height: '14px', background: `#${d.team_colour}`, borderRadius: '2px', marginRight: '6px', verticalAlign: 'middle' }} />
                            {d.name}
                        </td>
                        <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{d.team}</td>
                        <td style={{ ...tdStyle, fontWeight: 600 }}>{d.current_points}</td>
                        <td style={tdStyle}>
                            {d.total_points_mean}
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.6rem' }}> ±{d.simulated_points_std}</span>
                        </td>
                        <td style={tdStyle}>
                            <RangeBar p10={d.total_points_p10} p90={d.total_points_p90} mean={d.total_points_mean} maxPts={standings[0]?.total_points_p90 || 500} colour={d.team_colour} />
                        </td>
                        <td style={tdStyle}>
                            <ProbBar value={d.prob_champion} colour={d.team_colour} />
                        </td>
                        <td style={tdStyle}>
                            <ProbBar value={d.prob_top3} colour={d.team_colour} />
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    </div>
);

const WCCTable: FC<{ standings: ConstructorChampionshipStanding[] }> = ({ standings }) => (
    <div style={{ background: 'var(--bg-elevated)', borderRadius: '6px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.72rem', fontFamily: 'var(--font-mono)' }}>
            <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                    {['#', 'Constructor', 'Pts', 'Predicted', 'Range', 'P(Champ)'].map(h => (
                        <th key={h} style={thStyle}>{h}</th>
                    ))}
                </tr>
            </thead>
            <tbody>
                {standings.map((c, i) => (
                    <tr key={c.team} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                        <td style={{ ...tdStyle, color: 'var(--text-muted)', width: '30px' }}>{i + 1}</td>
                        <td style={{ ...tdStyle, fontWeight: 600, color: 'var(--text-primary)' }}>
                            <span style={{ display: 'inline-block', width: '4px', height: '14px', background: `#${c.team_colour}`, borderRadius: '2px', marginRight: '6px', verticalAlign: 'middle' }} />
                            {c.team}
                        </td>
                        <td style={{ ...tdStyle, fontWeight: 600 }}>{c.current_points}</td>
                        <td style={tdStyle}>
                            {c.total_points_mean}
                        </td>
                        <td style={tdStyle}>
                            <RangeBar p10={c.total_points_p10} p90={c.total_points_p90} mean={c.total_points_mean} maxPts={standings[0]?.total_points_p90 || 1000} colour={c.team_colour} />
                        </td>
                        <td style={tdStyle}>
                            <ProbBar value={c.prob_champion} colour={c.team_colour} />
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    </div>
);

const ProbabilityChart: FC<{ standings: DriverChampionshipStanding[] }> = ({ standings }) => (
    <div style={{ background: 'var(--bg-elevated)', borderRadius: '6px', padding: '12px 16px' }}>
        <div style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '10px' }}>
            Championship Probability
        </div>
        {standings.map(d => (
            <div key={d.driver_number} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span style={{ width: '35px', fontSize: '0.7rem', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', textAlign: 'right' }}>{d.name}</span>
                <div style={{ flex: 1, height: '16px', background: 'rgba(255,255,255,0.04)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{
                        width: `${Math.max(d.prob_champion * 100, 0.5)}%`,
                        height: '100%',
                        background: `#${d.team_colour}`,
                        borderRadius: '3px',
                        transition: 'width 0.5s ease',
                    }} />
                </div>
                <span style={{ width: '40px', fontSize: '0.65rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textAlign: 'right' }}>
                    {(d.prob_champion * 100).toFixed(1)}%
                </span>
            </div>
        ))}
    </div>
);

const ProbabilityChartWCC: FC<{ standings: ConstructorChampionshipStanding[] }> = ({ standings }) => (
    <div style={{ background: 'var(--bg-elevated)', borderRadius: '6px', padding: '12px 16px' }}>
        <div style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '10px' }}>
            Constructors Championship Probability
        </div>
        {standings.map(c => (
            <div key={c.team} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span style={{ width: '80px', fontSize: '0.7rem', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.team}</span>
                <div style={{ flex: 1, height: '16px', background: 'rgba(255,255,255,0.04)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{
                        width: `${Math.max(c.prob_champion * 100, 0.5)}%`,
                        height: '100%',
                        background: `#${c.team_colour}`,
                        borderRadius: '3px',
                        transition: 'width 0.5s ease',
                    }} />
                </div>
                <span style={{ width: '40px', fontSize: '0.65rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textAlign: 'right' }}>
                    {(c.prob_champion * 100).toFixed(1)}%
                </span>
            </div>
        ))}
    </div>
);

// =============================================================================
// Micro-components
// =============================================================================

const RangeBar: FC<{ p10: number; p90: number; mean: number; maxPts: number; colour: string }> = ({ p10, p90, mean, maxPts, colour }) => {
    const scale = maxPts > 0 ? 100 / maxPts : 1;
    return (
        <div style={{ position: 'relative', height: '10px', width: '100%', minWidth: '60px', background: 'rgba(255,255,255,0.04)', borderRadius: '2px' }}>
            <div style={{
                position: 'absolute',
                left: `${p10 * scale}%`,
                width: `${Math.max((p90 - p10) * scale, 1)}%`,
                height: '100%',
                background: `#${colour}33`,
                borderRadius: '2px',
            }} />
            <div style={{
                position: 'absolute',
                left: `${mean * scale}%`,
                width: '2px',
                height: '100%',
                background: `#${colour}`,
                borderRadius: '1px',
            }} />
        </div>
    );
};

const ProbBar: FC<{ value: number; colour: string }> = ({ value, colour }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
        <div style={{ width: '50px', height: '8px', background: 'rgba(255,255,255,0.04)', borderRadius: '2px', overflow: 'hidden' }}>
            <div style={{
                width: `${Math.max(value * 100, 0.5)}%`,
                height: '100%',
                background: `#${colour}`,
                borderRadius: '2px',
            }} />
        </div>
        <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', minWidth: '28px' }}>
            {(value * 100).toFixed(0)}%
        </span>
    </div>
);

// =============================================================================
// Styles
// =============================================================================

const selectStyle: React.CSSProperties = {
    padding: '3px 8px',
    fontSize: '0.7rem',
    fontFamily: 'var(--font-mono)',
    background: 'rgba(255,255,255,0.06)',
    color: 'var(--text-primary)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '3px',
    cursor: 'pointer',
};

const thStyle: React.CSSProperties = {
    padding: '8px 10px',
    textAlign: 'left',
    fontSize: '0.6rem',
    fontWeight: 600,
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
};

const tdStyle: React.CSSProperties = {
    padding: '6px 10px',
    color: 'var(--text-secondary)',
};

export default ChampionshipPage;
