/**
 * ExplainabilityPanel — AI Strategy Explanation Dashboard
 *
 * Shows WHY the AI recommends a particular strategy:
 * - Top 3 contributing factors (waterfall chart)
 * - Sensitivity analysis (how robust is the recommendation)
 * - What-if scenarios (alternative outcomes)
 *
 * @module components/ExplainabilityPanel
 */

import { useState, useEffect, useCallback, useRef, type FC } from 'react';

// =============================================================================
// Types
// =============================================================================

interface FactorContribution {
    name: string;
    score: number;
    direction: string;
    description: string;
}

interface SensitivityPoint {
    param_name: string;
    param_label: string;
    low_value: number;
    base_value: number;
    high_value: number;
    low_rec: string;
    base_rec: string;
    high_rec: string;
    low_conf: number;
    base_conf: number;
    high_conf: number;
    delta: number;
}

interface WhatIfScenario {
    condition: string;
    outcome: string;
    confidence_change: number;
}

interface ExplainabilityData {
    driver_number: number;
    recommendation: string;
    confidence: number;
    explanation: string;
    strategy: {
        action: string;
        confidence: number;
        reason: string;
    };
    top_factors: FactorContribution[];
    sensitivity: SensitivityPoint[];
    what_if_scenarios: WhatIfScenario[];
}

interface ExplainabilityPanelProps {
    driverNumber: number;
    onClose: () => void;
}

// =============================================================================
// Sub-components
// =============================================================================

const FactorBar: FC<{ factor: FactorContribution; maxScore: number }> = ({ factor, maxScore }) => {
    const widthPct = maxScore > 0 ? (factor.score / maxScore) * 100 : 0;
    const color = factor.direction === 'positive' ? 'var(--status-red)' : 'var(--status-green)';
    const icon = factor.direction === 'positive' ? '▲' : '▼';

    return (
        <div style={{ marginBottom: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3px' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {icon} {factor.name}
                </span>
                <span style={{ fontSize: '0.65rem', fontFamily: 'var(--font-mono)', color }}>
                    {(factor.score * 100).toFixed(0)}%
                </span>
            </div>
            <div style={{ height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{
                    height: '100%',
                    width: `${widthPct}%`,
                    background: `linear-gradient(90deg, ${color}40, ${color})`,
                    borderRadius: '3px',
                    transition: 'width 0.5s ease',
                }} />
            </div>
            <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                {factor.description}
            </div>
        </div>
    );
};

const SensitivityBar: FC<{ point: SensitivityPoint }> = ({ point }) => {
    const changed = point.low_rec !== point.base_rec || point.high_rec !== point.base_rec;
    const impactColor = point.delta > 0.15 ? 'var(--status-red)' : point.delta > 0.08 ? 'var(--status-amber)' : 'var(--status-green)';

    // Visual: show low—base—high confidence spread
    const barWidth = 100;
    const lowPos = Math.max(0, Math.min(barWidth, point.low_conf * barWidth));
    const basePos = Math.max(0, Math.min(barWidth, point.base_conf * barWidth));
    const highPos = Math.max(0, Math.min(barWidth, point.high_conf * barWidth));
    const minPos = Math.min(lowPos, basePos, highPos);
    const maxPos = Math.max(lowPos, basePos, highPos);

    return (
        <div style={{
            padding: '6px 8px',
            background: changed ? 'rgba(248,81,73,0.06)' : 'rgba(255,255,255,0.02)',
            borderLeft: `3px solid ${impactColor}`,
            borderRadius: '2px',
            marginBottom: '6px',
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 600 }}>{point.param_label}</span>
                <span style={{ fontSize: '0.6rem', fontFamily: 'var(--font-mono)', color: impactColor }}>
                    Δ {(point.delta * 100).toFixed(0)}%
                </span>
            </div>
            {/* Horizontal spread bar */}
            <div style={{ position: 'relative', height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px' }}>
                <div style={{
                    position: 'absolute',
                    left: `${minPos}%`,
                    width: `${Math.max(2, maxPos - minPos)}%`,
                    height: '100%',
                    background: `${impactColor}50`,
                    borderRadius: '3px',
                }} />
                <div style={{
                    position: 'absolute',
                    left: `${basePos}%`,
                    top: '-1px',
                    width: '2px',
                    height: '8px',
                    background: 'var(--text-secondary)',
                    transform: 'translateX(-50%)',
                    borderRadius: '1px',
                }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '3px', fontSize: '0.58rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                <span>{point.low_value.toFixed(2)}</span>
                <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>{point.base_value.toFixed(2)}</span>
                <span>{point.high_value.toFixed(2)}</span>
            </div>
            {changed && (
                <div style={{ marginTop: '3px', fontSize: '0.6rem', color: 'var(--status-amber)' }}>
                    ⚠ Recommendation changes with this parameter
                </div>
            )}
        </div>
    );
};

const WhatIfCard: FC<{ scenario: WhatIfScenario }> = ({ scenario }) => {
    const changeColor = scenario.confidence_change > 0 ? 'var(--status-green)' : 'var(--status-red)';

    return (
        <div style={{
            padding: '6px 8px',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '4px',
            marginBottom: '4px',
        }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginBottom: '2px' }}>
                {scenario.condition}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 600 }}>→ {scenario.outcome}</span>
                <span style={{ fontSize: '0.6rem', fontFamily: 'var(--font-mono)', color: changeColor }}>
                    {scenario.confidence_change > 0 ? '+' : ''}{(scenario.confidence_change * 100).toFixed(0)}%
                </span>
            </div>
        </div>
    );
};

// =============================================================================
// Section
// =============================================================================

const XSection: FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
    <div style={{ padding: '8px 10px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
        <div style={{
            fontSize: '0.58rem',
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            marginBottom: '6px',
            fontWeight: 500,
        }}>
            {label}
        </div>
        {children}
    </div>
);

// =============================================================================
// Main Component
// =============================================================================

const ExplainabilityPanel: FC<ExplainabilityPanelProps> = ({ driverNumber, onClose }) => {
    const [data, setData] = useState<ExplainabilityData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const mountedRef = useRef(true);

    // Stable fetch function — no dependency on `data`
    const doFetch = useCallback(async (showSpinner: boolean) => {
        if (showSpinner) setLoading(true);
        setError(null);
        try {
            const response = await fetch(`/api/strategy/explain/${driverNumber}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const json = await response.json();
            if (mountedRef.current) {
                setData(json);
                setLastUpdated(new Date());
            }
        } catch (err) {
            if (mountedRef.current) {
                setError(err instanceof Error ? err.message : 'Failed to load');
            }
        } finally {
            if (mountedRef.current) setLoading(false);
        }
    }, [driverNumber]);

    // Initial fetch + auto-refresh every 5 seconds
    useEffect(() => {
        mountedRef.current = true;
        doFetch(true); // initial fetch with spinner

        const interval = setInterval(() => {
            doFetch(false); // auto-refresh without spinner
        }, 5000);

        return () => {
            mountedRef.current = false;
            clearInterval(interval);
        };
    }, [doFetch]);

    const maxFactorScore = data?.top_factors?.length ? Math.max(...data.top_factors.map(f => f.score)) : 1;

    // Recommendation badge
    const getRecBadge = (rec: string) => {
        const styles: Record<string, { bg: string; color: string; label: string }> = {
            PIT_NOW: { bg: 'rgba(248,81,73,0.15)', color: 'var(--status-red)', label: 'PIT NOW' },
            CONSIDER_PIT: { bg: 'rgba(210,153,34,0.15)', color: 'var(--status-amber)', label: 'CONSIDER PIT' },
            EXTEND_STINT: { bg: 'rgba(63,185,80,0.12)', color: 'var(--status-green)', label: 'EXTEND STINT' },
            STAY_OUT: { bg: 'rgba(63,185,80,0.08)', color: 'var(--status-green)', label: 'STAY OUT' },
        };
        return styles[rec] || styles.STAY_OUT;
    };

    return (
        <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'var(--bg-primary)',
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
        }}>
            {/* Header */}
            <div style={{
                padding: '8px 10px',
                background: 'var(--bg-tertiary)',
                borderBottom: '1px solid rgba(255,255,255,0.06)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexShrink: 0,
            }}>
                <div>
                    <div style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.04em' }}>
                        AI STRATEGY EXPLANATION
                    </div>
                    <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>Driver #{driverNumber}</span>
                        {lastUpdated && (
                            <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                                <span style={{
                                    width: '5px', height: '5px', borderRadius: '50%',
                                    background: 'var(--status-green)',
                                    animation: 'pulse 2s ease-in-out infinite',
                                    display: 'inline-block',
                                }} />
                                <span style={{ fontSize: '0.55rem' }}>
                                    Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                </span>
                            </span>
                        )}
                    </div>
                </div>
                <button
                    onClick={onClose}
                    style={{
                        background: 'rgba(255,255,255,0.06)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        color: 'var(--text-secondary)',
                        borderRadius: '3px',
                        padding: '3px 8px',
                        fontSize: '0.65rem',
                        cursor: 'pointer',
                        fontFamily: 'inherit',
                    }}
                >
                    ✕ Close
                </button>
            </div>

            {/* Content */}
            <div style={{ flex: 1, overflow: 'auto' }}>
                {loading && (
                    <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                        Analyzing strategy factors...
                    </div>
                )}

                {error && (
                    <div style={{ padding: '16px', color: 'var(--status-red)', fontSize: '0.72rem' }}>
                        Error: {error}
                        <button onClick={() => doFetch(true)} style={{ marginLeft: '8px', color: 'var(--color-info)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.72rem' }}>
                            Retry
                        </button>
                    </div>
                )}

                {data && !loading && (
                    <>
                        {/* Recommendation Badge */}
                        <XSection label="Current Recommendation">
                            {(() => {
                                const badge = getRecBadge(data.recommendation);
                                return (
                                    <div style={{
                                        padding: '8px 12px',
                                        background: badge.bg,
                                        borderLeft: `3px solid ${badge.color}`,
                                        borderRadius: '2px',
                                    }}>
                                        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '2px' }}>
                                            <span style={{ fontWeight: 700, fontSize: '1rem', color: badge.color, letterSpacing: '0.05em' }}>
                                                {badge.label}
                                            </span>
                                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: badge.color }}>
                                                {(data.confidence * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
                                            {data.strategy.reason}
                                        </div>
                                    </div>
                                );
                            })()}
                        </XSection>

                        {/* Top Factors */}
                        {data.top_factors.length > 0 && (
                            <XSection label="Top Contributing Factors">
                                {data.top_factors.map((f, i) => (
                                    <FactorBar key={i} factor={f} maxScore={maxFactorScore} />
                                ))}
                            </XSection>
                        )}

                        {/* Sensitivity Analysis */}
                        {data.sensitivity.length > 0 && (
                            <XSection label="Sensitivity Analysis">
                                <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
                                    How much does each parameter affect the recommendation?
                                </div>
                                {data.sensitivity.map((s, i) => (
                                    <SensitivityBar key={i} point={s} />
                                ))}
                            </XSection>
                        )}

                        {/* What-If Scenarios */}
                        {data.what_if_scenarios.length > 0 && (
                            <XSection label="What If...">
                                {data.what_if_scenarios.map((w, i) => (
                                    <WhatIfCard key={i} scenario={w} />
                                ))}
                            </XSection>
                        )}

                        {/* Refresh */}
                        <div style={{ padding: '8px 10px', textAlign: 'center' }}>
                            <button
                                onClick={() => doFetch(true)}
                                style={{
                                    background: 'rgba(88,166,255,0.1)',
                                    border: '1px solid rgba(88,166,255,0.2)',
                                    color: 'var(--color-info)',
                                    borderRadius: '4px',
                                    padding: '5px 14px',
                                    fontSize: '0.68rem',
                                    cursor: 'pointer',
                                    fontFamily: 'inherit',
                                    transition: 'background 0.15s',
                                }}
                            >
                                ↻ Refresh Analysis
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default ExplainabilityPanel;
