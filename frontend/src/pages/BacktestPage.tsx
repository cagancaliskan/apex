/**
 * Backtest Page
 * 
 * Allows users to run strategy backtests on historical races
 * and analyze what-if scenarios.
 * 
 * New in v3.0.1 (Medium priority feature)
 */

import { useState, type FC } from 'react';

interface BacktestResult {
    originalPosition: number;
    alternativePosition: number;
    positionGain: number;
    originalStrategy: string;
    alternativeStrategy: string;
}

interface SessionOption {
    year: number;
    round: number;
    name: string;
    circuit: string;
}

const AVAILABLE_SESSIONS: SessionOption[] = [
    { year: 2023, round: 1, name: 'Bahrain GP', circuit: 'Bahrain' },
    { year: 2023, round: 2, name: 'Saudi Arabian GP', circuit: 'Jeddah' },
    { year: 2023, round: 3, name: 'Australian GP', circuit: 'Melbourne' },
    { year: 2023, round: 4, name: 'Azerbaijan GP', circuit: 'Baku' },
    { year: 2023, round: 5, name: 'Miami GP', circuit: 'Miami' },
];

/**
 * Backtest Page Component
 */
const BacktestPage: FC = () => {
    const [selectedSession, setSelectedSession] = useState<SessionOption | null>(null);
    const [selectedDriver, setSelectedDriver] = useState<string>('');
    const [alternativeStrategy, setAlternativeStrategy] = useState<string>('1-stop');
    const [isRunning, setIsRunning] = useState(false);
    const [result, setResult] = useState<BacktestResult | null>(null);

    const handleRunBacktest = async () => {
        if (!selectedSession || !selectedDriver) return;

        setIsRunning(true);

        // Simulate backtest running
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Simulated result
        setResult({
            originalPosition: 5,
            alternativePosition: 3,
            positionGain: 2,
            originalStrategy: '2-stop (S-M-H)',
            alternativeStrategy: alternativeStrategy,
        });

        setIsRunning(false);
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
                                const session = AVAILABLE_SESSIONS.find(s => s.year === year && s.round === round);
                                setSelectedSession(session || null);
                            }}
                            style={{
                                width: '100%',
                                padding: 'var(--space-sm)',
                                background: 'var(--bg-tertiary)',
                                border: '1px solid var(--border-color)',
                                borderRadius: 'var(--radius-sm)',
                                color: 'var(--text-primary)',
                                fontSize: '0.9rem'
                            }}
                        >
                            <option value="">Select a race...</option>
                            {AVAILABLE_SESSIONS.map(s => (
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
                                background: 'var(--bg-tertiary)',
                                border: '1px solid var(--border-color)',
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
                            {['1-stop', '2-stop', '3-stop'].map(strat => (
                                <button
                                    key={strat}
                                    onClick={() => setAlternativeStrategy(strat)}
                                    style={{
                                        flex: 1,
                                        padding: 'var(--space-sm)',
                                        background: alternativeStrategy === strat ? 'var(--color-info)' : 'var(--bg-tertiary)',
                                        color: alternativeStrategy === strat ? 'black' : 'var(--text-primary)',
                                        border: '1px solid var(--border-color)',
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
                            background: isRunning ? 'var(--bg-tertiary)' : 'var(--color-info)',
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

                    {!result && !isRunning && (
                        <div style={{
                            textAlign: 'center',
                            padding: 'var(--space-xl)',
                            color: 'var(--text-muted)'
                        }}>
                            <p>Configure and run a backtest to see results</p>
                        </div>
                    )}

                    {isRunning && (
                        <div style={{
                            textAlign: 'center',
                            padding: 'var(--space-xl)'
                        }}>
                            <div style={{
                                width: '40px',
                                height: '40px',
                                border: '3px solid var(--bg-tertiary)',
                                borderTop: '3px solid var(--color-info)',
                                borderRadius: '50%',
                                animation: 'spin 1s linear infinite',
                                margin: '0 auto var(--space-md)'
                            }} />
                            <p style={{ color: 'var(--text-muted)' }}>
                                Running Monte Carlo simulation...
                            </p>
                        </div>
                    )}

                    {result && !isRunning && (
                        <div>
                            {/* Position Comparison */}
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-around',
                                marginBottom: 'var(--space-lg)',
                                padding: 'var(--space-md)',
                                background: 'var(--bg-tertiary)',
                                borderRadius: 'var(--radius-md)'
                            }}>
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 'var(--space-xs)' }}>
                                        ORIGINAL
                                    </div>
                                    <div style={{ fontFamily: 'var(--font-sans)', fontSize: '2rem', fontWeight: 700 }}>
                                        P{result.originalPosition}
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
                                        color: result.positionGain > 0 ? 'var(--status-green)' : 'var(--text-primary)'
                                    }}>
                                        P{result.alternativePosition}
                                    </div>
                                </div>
                            </div>

                            {/* Position Change */}
                            {result.positionGain !== 0 && (
                                <div style={{
                                    textAlign: 'center',
                                    padding: 'var(--space-md)',
                                    background: result.positionGain > 0 ? 'rgba(76, 217, 100, 0.1)' : 'rgba(255, 68, 68, 0.1)',
                                    border: `1px solid ${result.positionGain > 0 ? 'var(--status-green)' : 'var(--status-red)'}`,
                                    borderRadius: 'var(--radius-md)',
                                    marginBottom: 'var(--space-md)'
                                }}>
                                    <span style={{
                                        fontFamily: 'var(--font-sans)',
                                        fontSize: '1.2rem',
                                        fontWeight: 700,
                                        color: result.positionGain > 0 ? 'var(--status-green)' : 'var(--status-red)'
                                    }}>
                                        {result.positionGain > 0 ? '▲' : '▼'} {Math.abs(result.positionGain)} positions
                                    </span>
                                </div>
                            )}

                            {/* Strategy Details */}
                            <div style={{ fontSize: '0.85rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-xs)' }}>
                                    <span style={{ color: 'var(--text-muted)' }}>Original:</span>
                                    <span>{result.originalStrategy}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span style={{ color: 'var(--text-muted)' }}>Alternative:</span>
                                    <span style={{ color: 'var(--color-info)' }}>{result.alternativeStrategy}</span>
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
