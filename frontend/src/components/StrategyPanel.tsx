/**
 * Strategy Panel — v2.1 Professional Strategy Console
 *
 * Right-panel console for the selected driver's strategy data.
 * Used in LiveDashboard as the full-height right column.
 * Also used in ReplayPage (compact mode).
 *
 * @module components/StrategyPanel
 */

import { useMemo, useState, type FC } from 'react';
import type { DriverState } from '../types';
import ExplainabilityPanel from './ExplainabilityPanel';
import PitRejoinVisualizer from './PitRejoinVisualizer';
import CompetitorPredictions from './CompetitorPredictions';
import PositionProbabilityChart from './PositionProbabilityChart';
import StrategyComparison from './StrategyComparison';
import { useRaceStore } from '../store/raceStore';
import styles from './StrategyPanel.module.css';
import {
    TYRE_COLORS,
    TYRE_TEXT_COLORS,
    DEG_HIGH_THRESHOLD,
    DEG_MED_THRESHOLD,
    CLIFF_RISK_CRITICAL,
    CLIFF_RISK_WARNING,
    DEFAULT_RACE_LAPS,
} from '../config/constants';

// =============================================================================
// Types
// =============================================================================

interface StrategyPanelProps {
    drivers: DriverState[];
    selectedDriver?: DriverState | number | null;
    compact?: boolean;
    currentLap?: number;
    totalLaps?: number;
}

type RecommendationType = 'PIT_NOW' | 'CONSIDER_PIT' | 'EXTEND_STINT' | string;

interface RecommendationStyle {
    bg: string;
    border: string;
    text: string;
    color: string;
}

// =============================================================================
// Helpers
// =============================================================================

function getRecStyle(rec: RecommendationType | undefined): RecommendationStyle {
    switch (rec) {
        case 'PIT_NOW':
            return { bg: 'rgba(225, 6, 0, 0.12)', border: 'var(--color-accent)', text: 'PIT NOW', color: 'var(--color-accent)' };
        case 'CONSIDER_PIT':
            return { bg: 'rgba(210, 153, 34, 0.12)', border: 'var(--status-amber)', text: 'CONSIDER PIT', color: 'var(--status-amber)' };
        case 'EXTEND_STINT':
            return { bg: 'rgba(63, 185, 80, 0.12)', border: 'var(--status-green)', text: 'EXTEND STINT', color: 'var(--status-green)' };
        default:
            return { bg: 'rgba(63, 185, 80, 0.08)', border: 'var(--status-green)', text: 'STAY OUT', color: 'var(--status-green)' };
    }
}

function getDegColor(slope: number | undefined): string {
    if (!slope) return 'var(--status-green)';
    if (slope > DEG_HIGH_THRESHOLD) return 'var(--status-red)';
    if (slope > DEG_MED_THRESHOLD) return 'var(--status-amber)';
    return 'var(--status-green)';
}

function getCliffColor(risk: number | undefined): string {
    if (!risk) return 'var(--status-green)';
    if (risk > CLIFF_RISK_CRITICAL) return 'var(--color-accent)';
    if (risk > CLIFF_RISK_WARNING) return 'var(--status-amber)';
    return 'var(--status-green)';
}

const TYRE_TEXT = TYRE_TEXT_COLORS;

// =============================================================================
// Section component
// =============================================================================

const Section: FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
    <div className={styles.strategySection}>
        <div className={styles.sectionLabel}>{label}</div>
        {children}
    </div>
);

// =============================================================================
// Compact mode
// =============================================================================

const CompactStrategy: FC<{ driver: DriverState }> = ({ driver }) => {
    const rec = getRecStyle(driver.pit_recommendation);
    return (
        <div style={{ padding: '6px 8px', fontSize: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem', textTransform: 'uppercase' }}>Strategy</span>
                <span style={{ fontWeight: 600 }}>{driver.name_acronym}</span>
            </div>
            <div style={{ padding: '4px 8px', background: rec.bg, borderLeft: `3px solid ${rec.border}`, borderRadius: '2px', marginBottom: '4px' }}>
                <span style={{ fontWeight: 700, color: rec.color, fontSize: '0.8rem' }}>{rec.text}</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2px', fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}>
                <div><span style={{ color: 'var(--text-muted)' }}>Deg </span><span style={{ color: getDegColor(driver.deg_slope ?? undefined) }}>{((driver.deg_slope || 0) * 1000).toFixed(0)}ms</span></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Cliff </span><span style={{ color: getCliffColor(driver.cliff_risk ?? undefined) }}>{Math.round((driver.cliff_risk || 0) * 100)}%</span></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Win </span><span>L{driver.pit_window_ideal || '—'}</span></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Fuel </span><span>{(driver.fuel_remaining_kg || 0).toFixed(1)}kg</span></div>
            </div>
        </div>
    );
};

// =============================================================================
// Main Component
// =============================================================================

const StrategyPanel: FC<StrategyPanelProps> = ({ drivers, selectedDriver, compact = false, currentLap = 0, totalLaps }) => {
    const sortedDrivers = useRaceStore(s => s.sortedDrivers);
    const recentPits = useRaceStore(s => s.recentPits);
    const storeCurrentLap = useRaceStore(s => s.currentLap);
    const effectiveLap = currentLap || storeCurrentLap;

    const driver = useMemo((): DriverState | null => {
        if (!drivers || drivers.length === 0) return null;
        if (selectedDriver) {
            const id = typeof selectedDriver === 'number' ? selectedDriver : selectedDriver.driver_number;
            return drivers.find(d => d.driver_number === id) || null;
        }
        return drivers[0];
    }, [drivers, selectedDriver]);

    if (!driver) {
        return (
            <div style={{ padding: '16px', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                Select a driver to view strategy data
            </div>
        );
    }

    if (compact) return <CompactStrategy driver={driver} />;

    const rec = getRecStyle(driver.pit_recommendation);
    const compound = driver.compound || 'MEDIUM';
    const tyreColor = TYRE_COLORS[compound] ?? '#fff';
    const tyreTxt = TYRE_TEXT[compound] ?? '#000';
    const fuelLaps = driver.fuel_laps_remaining || null;
    const confPct = Math.round((driver.model_confidence || 0) * 100);

    // Pit window bar positioning (% of totalLaps)
    const lapTotal = totalLaps || DEFAULT_RACE_LAPS;
    const winMin = driver.pit_window_min ?? 0;
    const winMax = driver.pit_window_max ?? null;
    const winIdeal = driver.pit_window_ideal ?? null;
    const hasPitWindow = driver.pit_window_min != null && driver.pit_window_min > 0;
    const minPct = hasPitWindow ? Math.max(0, Math.min(100, (winMin / lapTotal) * 100)) : 0;
    const maxPct = hasPitWindow && winMax != null ? Math.max(0, Math.min(100, (winMax / lapTotal) * 100)) : minPct;
    const idealPct = hasPitWindow && winIdeal != null ? Math.max(0, Math.min(100, (winIdeal / lapTotal) * 100)) : minPct;
    const currentPct = Math.max(0, Math.min(100, (effectiveLap / lapTotal) * 100));

    // 5-lap predicted pace sparkline (simple inline SVG)
    const pace = driver.predicted_pace || [];
    const sparky = pace.slice(0, 5);
    const sparkMin = sparky.length > 0 ? Math.min(...sparky) : 0;
    const sparkMax = sparky.length > 0 ? Math.max(...sparky) : 1;

    const [showExplain, setShowExplain] = useState(false);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
            {/* Driver Header */}
            <div style={{ padding: '8px 10px', background: 'var(--bg-tertiary)', borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '3px', height: '24px', background: driver.team_colour ? `#${driver.team_colour}` : '#666', borderRadius: '1px', flexShrink: 0 }} />
                    <div>
                        <div style={{ fontWeight: 700, fontSize: '0.9rem', lineHeight: 1.1 }}>{driver.name_acronym}</div>
                        <div style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', letterSpacing: '0.04em' }}>{driver.team_name}</div>
                    </div>
                    <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <div style={{ width: '22px', height: '22px', borderRadius: '50%', background: tyreColor, color: tyreTxt, fontSize: '0.65rem', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {compound[0]}
                        </div>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            {driver.tyre_age ?? driver.lap_in_stint ?? 0}L
                        </span>
                    </div>
                </div>
            </div>

            <div style={{ flex: 1, overflow: 'auto' }}>
                {/* Recommendation */}
                <Section label="Recommendation">
                    <div style={{ padding: '6px 8px', background: rec.bg, borderLeft: `3px solid ${rec.border}`, borderRadius: '2px', marginBottom: '4px' }}>
                        <div style={{
                            fontWeight: 700,
                            fontSize: driver.pit_recommendation === 'PIT_NOW' ? '0.7rem' : '0.9rem',
                            letterSpacing: driver.pit_recommendation === 'PIT_NOW' ? '0.08em' : '0.04em',
                            fontFamily: driver.pit_recommendation === 'PIT_NOW' ? "'Orbitron', sans-serif" : 'inherit',
                            textTransform: 'uppercase' as const,
                            padding: driver.pit_recommendation === 'PIT_NOW' ? '2px 6px' : undefined,
                            borderRadius: driver.pit_recommendation === 'PIT_NOW' ? 'var(--radius-sm)' : undefined,
                            backgroundColor: driver.pit_recommendation === 'PIT_NOW' ? 'var(--color-accent)' : undefined,
                            color: driver.pit_recommendation === 'PIT_NOW' ? '#fff' : rec.color,
                            display: 'inline-block',
                        }}>{rec.text}</div>
                        {driver.pit_reason && (
                            <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', marginTop: '2px' }}>{driver.pit_reason}</div>
                        )}
                    </div>
                    {(driver.pit_confidence || 0) > 0 && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Confidence</span>
                            <div style={{ flex: 1, height: '4px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                                <div style={{ height: '100%', width: `${Math.round((driver.pit_confidence || 0) * 100)}%`, background: rec.border, borderRadius: '2px' }} />
                            </div>
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.62rem', color: rec.color }}>{Math.round((driver.pit_confidence || 0) * 100)}%</span>
                        </div>
                    )}
                    <button
                        onClick={() => setShowExplain(true)}
                        style={{
                            width: '100%',
                            marginTop: '6px',
                            padding: '4px 8px',
                            background: 'rgba(88,166,255,0.08)',
                            border: '1px solid rgba(88,166,255,0.15)',
                            borderRadius: '3px',
                            color: 'var(--color-info)',
                            fontSize: '0.62rem',
                            cursor: 'pointer',
                            fontFamily: 'inherit',
                            letterSpacing: '0.06em',
                            textTransform: 'uppercase',
                            transition: 'background 0.15s',
                        }}
                    >
                        ◈ Explain This Decision
                    </button>
                </Section>

                {/* Pit Window */}
                <Section label="Pit Window">
                    {hasPitWindow ? (
                        <>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}>
                                <span style={{ color: 'var(--text-muted)' }}>L{winMin}</span>
                                <span style={{ color: 'var(--color-accent)', fontWeight: 700 }}>IDEAL L{winIdeal}</span>
                                <span style={{ color: 'var(--text-muted)' }}>L{winMax ?? winIdeal ?? '?'}</span>
                            </div>
                            <div style={{ position: 'relative', height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '4px', overflow: 'visible' }}>
                                {/* Window range */}
                                <div style={{ position: 'absolute', top: 0, left: `${minPct}%`, width: `${maxPct - minPct}%`, height: '100%', background: `linear-gradient(90deg, rgba(225,6,0,0.2) 0%, rgba(225,6,0,0.5) 50%, rgba(225,6,0,0.2) 100%)`, borderRadius: '4px' }} />
                                {/* Ideal marker */}
                                <div style={{ position: 'absolute', top: '-1px', left: `${idealPct}%`, width: '2px', height: '10px', background: 'var(--color-accent)', transform: 'translateX(-50%)', borderRadius: '1px' }} />
                                {/* Current lap */}
                                <div style={{ position: 'absolute', top: '-2px', left: `${currentPct}%`, width: '3px', height: '12px', background: 'var(--text-secondary)', transform: 'translateX(-50%)', borderRadius: '1px' }} />
                            </div>
                            <div style={{ marginTop: '4px', fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                                {winIdeal != null ? `Ideal: L${winIdeal}` : ''}
                            </div>
                        </>
                    ) : (
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>No pit window data</div>
                    )}
                </Section>

                {/* Threats — always visible */}
                <Section label="Threats">
                    {driver.undercut_threat && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 6px', background: 'rgba(255,107,0,0.1)', borderLeft: '3px solid var(--color-orange)', borderRadius: '2px', marginBottom: '4px' }}>
                            <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--color-orange)', letterSpacing: '0.06em' }}>UNDERCUT THREAT</span>
                            <span style={{ fontSize: '0.62rem', color: 'var(--text-secondary)' }}>Car ahead vulnerable</span>
                        </div>
                    )}
                    {driver.overcut_opportunity && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 6px', background: 'rgba(88,166,255,0.08)', borderLeft: '3px solid var(--color-info)', borderRadius: '2px' }}>
                            <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--color-info)', letterSpacing: '0.06em' }}>OVERCUT VIABLE</span>
                            <span style={{ fontSize: '0.62rem', color: 'var(--text-secondary)' }}>Car behind pitting</span>
                        </div>
                    )}
                    {!driver.undercut_threat && !driver.overcut_opportunity && (
                        <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>No threats detected</div>
                    )}
                </Section>

                {/* Degradation */}
                <Section label="Tyre Degradation">
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                        <div>
                            <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginBottom: '2px' }}>DEG RATE</div>
                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 700, color: getDegColor(driver.deg_slope ?? undefined) }}>
                                {((driver.deg_slope || 0) * 1000).toFixed(0)} ms/L
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginBottom: '2px' }}>CLIFF RISK</div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <div style={{ flex: 1, height: '4px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                                    <div style={{ height: '100%', width: `${Math.round((driver.cliff_risk || 0) * 100)}%`, background: `linear-gradient(90deg, #3fb950 0%, #d29922 50%, #f85149 100%)`, borderRadius: '2px' }} />
                                </div>
                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: getCliffColor(driver.cliff_risk ?? undefined) }}>
                                    {Math.round((driver.cliff_risk || 0) * 100)}%
                                </span>
                                {(driver.cliff_risk ?? 0) > 0.8 && (
                                    <span style={{
                                        fontFamily: "'Orbitron', sans-serif",
                                        fontSize: '0.65rem',
                                        fontWeight: 700,
                                        color: 'var(--color-accent)',
                                        letterSpacing: '0.1em',
                                        marginLeft: '6px',
                                    }}>
                                        CLIFF
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                </Section>

                {/* Predicted Pace */}
                {sparky.length > 0 && (
                    <Section label={`Predicted Pace — Next 5 Laps (${confPct}% conf)`}>
                        <div style={{ fontSize: '0.55rem', color: 'var(--text-muted)', marginBottom: '4px', fontStyle: 'italic' }}>
                            taller bars = slower pace (degrading)
                        </div>
                        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '3px', height: '52px' }}>
                            {sparky.map((v, i) => {
                                const BAR_MAX = 30;
                                const range = sparkMax - sparkMin;
                                const barH = range > 0.05 ? Math.max(4, ((v - sparkMin) / range) * BAR_MAX) : BAR_MAX / 2;
                                const delta = v - sparky[0];
                                const barColor = i === 0
                                    ? 'rgba(88,166,255,0.55)'
                                    : delta > 0.5 ? 'var(--status-red)'
                                    : delta > 0.2 ? 'var(--status-amber)'
                                    : 'rgba(88,166,255,0.4)';
                                return (
                                    <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end' }}>
                                        <div style={{ fontSize: '0.48rem', color: i === 0 ? 'var(--text-muted)' : barColor, fontFamily: 'var(--font-mono)', marginBottom: '2px', whiteSpace: 'nowrap' }}>
                                            {i === 0 ? 'base' : delta > 0 ? `+${delta.toFixed(1)}s` : '—'}
                                        </div>
                                        <div style={{ width: '100%', height: `${barH}px`, background: barColor, borderRadius: '2px 2px 0 0' }} />
                                        <div style={{ fontSize: '0.55rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>+{i + 1}</div>
                                    </div>
                                );
                            })}
                        </div>
                        <div style={{ marginTop: '2px', fontSize: '0.62rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                            Base: {sparky[0] ? `${sparky[0].toFixed(3)}s` : '—'}
                        </div>
                    </Section>
                )}

                {/* Fuel */}
                <Section label="Fuel Load">
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem', fontWeight: 700 }}>
                            {(driver.fuel_remaining_kg || 0).toFixed(1)} kg
                        </span>
                        {fuelLaps !== null && (
                            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>~{fuelLaps}L remaining</span>
                        )}
                    </div>
                    <div style={{ marginTop: '4px', height: '4px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${Math.min(100, ((driver.fuel_remaining_kg || 0) / 110) * 100)}%`, background: 'var(--color-info)', borderRadius: '2px' }} />
                    </div>
                </Section>

                {/* Rejoin Visualizer — visible whenever pit window data exists */}
                {(hasPitWindow || driver.in_pit === true) ? (
                    <PitRejoinVisualizer
                        driver={driver}
                        allDrivers={sortedDrivers}
                    />
                ) : (
                    <div style={{ marginTop: 'var(--space-md)', padding: 'var(--space-sm)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', minHeight: '72px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: '3px' }}>
                        <span style={{ fontSize: '0.6rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Pit Rejoin Prediction</span>
                        <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            No pit window calculated yet
                        </span>
                    </div>
                )}

                {/* Competitor Predictions — rival pit windows */}
                <CompetitorPredictions
                    drivers={sortedDrivers}
                    selectedDriverNumber={driver.driver_number}
                />

                {/* Position Probability — Monte Carlo results */}
                <PositionProbabilityChart
                    probabilities={[]}
                    currentPosition={driver.position ?? undefined}
                />

                {/* Strategy Comparison — 1-stop vs 2-stop */}
                <StrategyComparison driver={driver} totalLaps={totalLaps || DEFAULT_RACE_LAPS} />

                {/* Pit History Strip */}
                {recentPits.length > 0 && (
                    <Section label="RECENT PITS">
                        {recentPits.slice(0, 3).map((pit) => (
                            <div key={`${pit.driver_number}-${pit.lap_number}`} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', padding: '2px 0', color: 'var(--text-secondary)' }}>
                                <span style={{ color: 'var(--text-primary)', minWidth: '28px' }}>#{pit.driver_number}</span>
                                <span>L{pit.lap_number}</span>
                                {pit.compound && (
                                    <span style={{
                                        width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0,
                                        display: 'inline-block',
                                        background: pit.compound === 'SOFT' ? 'var(--tyre-soft)'
                                            : pit.compound === 'MEDIUM' ? 'var(--tyre-medium)'
                                            : pit.compound === 'HARD' ? 'var(--tyre-hard)'
                                            : pit.compound === 'INTERMEDIATE' ? 'var(--tyre-inter)'
                                            : pit.compound === 'WET' ? 'var(--tyre-wet)'
                                            : 'var(--text-muted)',
                                    }} />
                                )}
                                {pit.compound && <span style={{ fontSize: '0.7rem', textTransform: 'uppercase' as const }}>{pit.compound.slice(0, 1)}</span>}
                                {pit.pit_duration != null && (
                                    <span style={{ color: 'var(--text-muted)', marginLeft: 'auto' }}>{pit.pit_duration.toFixed(1)}s</span>
                                )}
                            </div>
                        ))}
                    </Section>
                )}
            </div>

            {/* Explainability overlay */}
            {showExplain && (
                <ExplainabilityPanel
                    driverNumber={driver.driver_number}
                    onClose={() => setShowExplain(false)}
                />
            )}
        </div>
    );
};

export default StrategyPanel;
