/**
 * Backtest Page
 *
 * Runs alternative pit strategy simulations against historical races
 * via POST /api/backtest/run and shows position + time deltas.
 */

import { useState, useEffect, type FC } from 'react';
import {
    API_SESSIONS,
    API_BACKTEST_RUN,
    DEFAULT_YEAR,
    AVAILABLE_YEARS,
    STRATEGY_OPTIONS,
} from '../config/constants';

interface BacktestResult {
    original_position: number;
    alternative_position: number;
    position_delta: number;
    time_delta: number;
    original_strategy: string;
    alternative_strategy: string;
    driver_name: string;
    session_name: string;
    total_laps: number;
}

interface SessionOption {
    year: number;
    round: number;
    name: string;
    circuit: string;
}

const BacktestPage: FC = () => {
    const [selectedYear, setSelectedYear] = useState(DEFAULT_YEAR);
    const [availableSessions, setAvailableSessions] = useState<SessionOption[]>([]);
    const [selectedSession, setSelectedSession] = useState<SessionOption | null>(null);
    const [selectedDriver, setSelectedDriver] = useState<string>('');
    const [alternativeStrategy, setAlternativeStrategy] = useState<string>(STRATEGY_OPTIONS[0]);
    const [isRunning, setIsRunning] = useState(false);
    const [result, setResult] = useState<BacktestResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setSelectedSession(null);
        fetch(`${API_SESSIONS}?year=${selectedYear}`)
            .then(r => r.json())
            .then((data: Array<{ year: number; round_number: number; session_name: string; circuit: string }>) => {
                setAvailableSessions(data.map(s => ({
                    year: s.year,
                    round: s.round_number,
                    name: s.session_name,
                    circuit: s.circuit,
                })));
            })
            .catch(() => setAvailableSessions([]));
    }, [selectedYear]);

    const handleRunBacktest = async () => {
        if (!selectedSession || !selectedDriver) return;

        setIsRunning(true);
        setResult(null);
        setError(null);

        try {
            const resp = await fetch(API_BACKTEST_RUN, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    year: selectedSession.year,
                    round: selectedSession.round,
                    driver_acronym: selectedDriver,
                    strategy: alternativeStrategy,
                }),
            });

            if (!resp.ok) {
                const body = await resp.json().catch(() => ({ detail: resp.statusText }));
                throw new Error(body.detail ?? resp.statusText);
            }

            const data: BacktestResult = await resp.json();
            setResult(data);
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
        } finally {
            setIsRunning(false);
        }
    };

    const timeDeltaLabel = (delta: number) => {
        const abs = Math.abs(delta).toFixed(1);
        return delta < 0 ? `−${abs}s faster` : `+${abs}s slower`;
    };

    return (
        <div style={{
            padding: 'var(--space-lg)',
            maxWidth: '1200px',
            margin: '0 auto'
        }}>
            <h1 style={{
                fontFamily: 'var(--font-sans)',
                fontSize: '1.8rem',
                marginBottom: 'var(--space-lg)',
                color: 'var(--text-primary)'
            }}>
                Strategy Backtest
            </h1>

            <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 'var(--space-lg)'
            }}>
                {/* Configuration Panel */}
                <div className="card">
                    <h3 className="card-title">Configuration</h3>

                    {/* Year Selection */}
                    <div style={{ marginBottom: 'var(--space-md)' }}>
                        <label style={{
                            display: 'block',
                            fontSize: '0.75rem',
                            color: 'var(--text-muted)',
                            marginBottom: 'var(--space-xs)',
                            textTransform: 'uppercase'
                        }}>
                            Season
                        </label>
                        <select
                            value={selectedYear}
                            onChange={(e) => setSelectedYear(Number(e.target.value))}
                            style={{
                                width: '100%',
                                padding: 'var(--space-sm)',
                                background: 'var(--bg-elevated)',
                                border: '1px solid var(--border-subtle)',
                                borderRadius: 'var(--radius-sm)',
                                color: 'var(--text-primary)',
                                fontSize: '0.9rem'
                            }}
                        >
                            {AVAILABLE_YEARS.map(y => (
                                <option key={y} value={y}>{y}</option>
                            ))}
                        </select>
                    </div>

                    {/* Session Selection */}
                    <div style={{ marginBottom: 'var(--space-md)' }}>
                        <label style={{
                            display: 'block',
                            fontSize: '0.75rem',
                            color: 'var(--text-muted)',
                            marginBottom: 'var(--space-xs)',
                            textTransform: 'uppercase'
                        }}>
                            Select Race
                        </label>
                        <select
                            value={selectedSession ? `${selectedSession.year}-${selectedSession.round}` : ''}
                            onChange={(e) => {
                                const [year, round] = e.target.value.split('-').map(Number);
                                const session = availableSessions.find(s => s.year === year && s.round === round);
                                setSelectedSession(session || null);
                            }}
                            style={{
                                width: '100%',
                                padding: 'var(--space-sm)',
                                background: 'var(--bg-elevated)',
                                border: '1px solid var(--border-subtle)',
                                borderRadius: 'var(--radius-sm)',
                                color: 'var(--text-primary)',
                                fontSize: '0.9rem'
                            }}
                        >
                            <option value="">Select a race...</option>
                            {availableSessions.map(s => (
                                <option key={`${s.year}-${s.round}`} value={`${s.year}-${s.round}`}>
                                    {s.year} {s.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Driver Selection */}
                    <div style={{ marginBottom: 'var(--space-md)' }}>
                        <label style={{
                            display: 'block',
                            fontSize: '0.75rem',
                            color: 'var(--text-muted)',
                            marginBottom: 'var(--space-xs)',
                            textTransform: 'uppercase'
                        }}>
                            Select Driver
                        </label>
                        <select
                            value={selectedDriver}
                            onChange={(e) => setSelectedDriver(e.target.value)}
                            style={{
                                width: '100%',
                                padding: 'var(--space-sm)',
                                background: 'var(--bg-elevated)',
                                border: '1px solid var(--border-subtle)',
                                borderRadius: 'var(--radius-sm)',
                                color: 'var(--text-primary)',
                                fontSize: '0.9rem'
                            }}
                        >
                            <option value="">Select a driver...</option>
                            <option value="VER">Max Verstappen</option>
                            <option value="PER">Sergio Perez</option>
                            <option value="HAM">Lewis Hamilton</option>
                            <option value="RUS">George Russell</option>
                            <option value="LEC">Charles Leclerc</option>
                            <option value="SAI">Carlos Sainz</option>
                            <option value="NOR">Lando Norris</option>
                            <option value="PIA">Oscar Piastri</option>
                        </select>
                    </div>

                    {/* Alternative Strategy */}
                    <div style={{ marginBottom: 'var(--space-md)' }}>
                        <label style={{
                            display: 'block',
                            fontSize: '0.75rem',
                            color: 'var(--text-muted)',
                            marginBottom: 'var(--space-xs)',
                            textTransform: 'uppercase'
                        }}>
                            Alternative Strategy
                        </label>
                        <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                            {STRATEGY_OPTIONS.map(strat => (
                                <button
                                    key={strat}
                                    onClick={() => setAlternativeStrategy(strat)}
                                    style={{
                                        flex: 1,
                                        padding: 'var(--space-sm)',
                                        background: alternativeStrategy === strat ? 'var(--color-accent)' : 'var(--bg-elevated)',
                                        color: alternativeStrategy === strat ? 'black' : 'var(--text-primary)',
                                        border: '1px solid var(--border-subtle)',
                                        borderRadius: 'var(--radius-sm)',
                                        cursor: 'pointer',
                                        fontWeight: alternativeStrategy === strat ? 600 : 400,
                                        transition: 'all 0.2s ease'
                                    }}
                                >
                                    {strat}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Run Button */}
                    <button
                        onClick={handleRunBacktest}
                        disabled={!selectedSession || !selectedDriver || isRunning}
                        style={{
                            width: '100%',
                            padding: 'var(--space-md)',
                            background: isRunning ? 'var(--bg-elevated)' : 'var(--color-accent)',
                            color: isRunning ? 'var(--text-muted)' : 'black',
                            border: 'none',
                            borderRadius: 'var(--radius-md)',
                            cursor: isRunning ? 'wait' : 'pointer',
                            fontFamily: 'var(--font-sans)',
                            fontSize: '1rem',
                            fontWeight: 700,
                            transition: 'all 0.2s ease'
                        }}
                    >
                        {isRunning ? 'Running Simulation...' : 'Run Backtest'}
                    </button>
                </div>

                {/* Results Panel */}
                <div className="card">
                    <h3 className="card-title">Results</h3>

                    {!result && !isRunning && !error && (
                        <div style={{
                            textAlign: 'center',
                            padding: 'var(--space-xl)',
                            color: 'var(--text-muted)'
                        }}>
                            <p>Configure and run a backtest to see results</p>
                        </div>
                    )}

                    {isRunning && (
                        <div style={{ textAlign: 'center', padding: 'var(--space-xl)' }}>
                            <div style={{
                                width: '40px',
                                height: '40px',
                                border: '3px solid var(--bg-elevated)',
                                borderTop: '3px solid var(--color-accent)',
                                borderRadius: '50%',
                                animation: 'spin 1s linear infinite',
                                margin: '0 auto var(--space-md)'
                            }} />
                            <p style={{ color: 'var(--text-muted)' }}>
                                Loading race data and running simulation...
                            </p>
                        </div>
                    )}

                    {error && !isRunning && (
                        <div style={{
                            padding: 'var(--space-md)',
                            background: 'rgba(248,81,73,0.08)',
                            border: '1px solid var(--status-red)',
                            borderRadius: 'var(--radius-md)',
                            color: 'var(--status-red)',
                            fontSize: '0.85rem'
                        }}>
                            {error}
                        </div>
                    )}

                    {result && !isRunning && (
                        <div>
                            {/* Session / Driver */}
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 'var(--space-md)' }}>
                                {result.session_name} · {result.driver_name} · {result.total_laps} laps
                            </div>

                            {/* Position Comparison */}
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-around',
                                marginBottom: 'var(--space-md)',
                                padding: 'var(--space-md)',
                                background: 'var(--bg-elevated)',
                                borderRadius: 'var(--radius-md)'
                            }}>
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 'var(--space-xs)' }}>
                                        ORIGINAL
                                    </div>
                                    <div style={{ fontFamily: 'var(--font-sans)', fontSize: '2rem', fontWeight: 700 }}>
                                        P{result.original_position}
                                    </div>
                                </div>
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    fontSize: '1.5rem',
                                    color: 'var(--text-muted)'
                                }}>
                                    →
                                </div>
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 'var(--space-xs)' }}>
                                        ALTERNATIVE
                                    </div>
                                    <div style={{
                                        fontFamily: 'var(--font-sans)',
                                        fontSize: '2rem',
                                        fontWeight: 700,
                                        color: result.position_delta > 0
                                            ? 'var(--status-green)'
                                            : result.position_delta < 0
                                                ? 'var(--status-red)'
                                                : 'var(--text-primary)'
                                    }}>
                                        P{result.alternative_position}
                                    </div>
                                </div>
                            </div>

                            {/* Position change badge */}
                            {result.position_delta !== 0 && (
                                <div style={{
                                    textAlign: 'center',
                                    padding: 'var(--space-sm)',
                                    background: result.position_delta > 0
                                        ? 'rgba(76,217,100,0.1)'
                                        : 'rgba(255,68,68,0.1)',
                                    border: `1px solid ${result.position_delta > 0 ? 'var(--status-green)' : 'var(--status-red)'}`,
                                    borderRadius: 'var(--radius-md)',
                                    marginBottom: 'var(--space-sm)'
                                }}>
                                    <span style={{
                                        fontFamily: 'var(--font-sans)',
                                        fontSize: '1.2rem',
                                        fontWeight: 700,
                                        color: result.position_delta > 0 ? 'var(--status-green)' : 'var(--status-red)'
                                    }}>
                                        {result.position_delta > 0 ? '▲' : '▼'} {Math.abs(result.position_delta)} position{Math.abs(result.position_delta) !== 1 ? 's' : ''}
                                    </span>
                                </div>
                            )}

                            {/* Time delta */}
                            <div style={{
                                textAlign: 'center',
                                padding: 'var(--space-sm)',
                                background: 'var(--bg-elevated)',
                                borderRadius: 'var(--radius-md)',
                                marginBottom: 'var(--space-md)',
                                fontFamily: 'var(--font-mono)',
                                fontSize: '0.9rem',
                                color: result.time_delta < 0 ? 'var(--status-green)' : 'var(--text-secondary)'
                            }}>
                                {timeDeltaLabel(result.time_delta)}
                            </div>

                            {/* Strategy Details */}
                            <div style={{ fontSize: '0.85rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-xs)' }}>
                                    <span style={{ color: 'var(--text-muted)' }}>Original:</span>
                                    <span>{result.original_strategy}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span style={{ color: 'var(--text-muted)' }}>Alternative:</span>
                                    <span style={{ color: 'var(--color-accent)' }}>{result.alternative_strategy}</span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default BacktestPage;
