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
            return { bg: 'rgba(248, 81, 73, 0.12)', border: 'var(--status-red)', text: 'PIT NOW', color: 'var(--status-red)' };
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
    if (slope > 0.08) return 'var(--status-red)';
    if (slope > 0.05) return 'var(--status-amber)';
    return 'var(--status-green)';
}

function getCliffColor(risk: number | undefined): string {
    if (!risk) return 'var(--status-green)';
    if (risk > 0.7) return 'var(--status-red)';
    if (risk > 0.4) return 'var(--status-amber)';
    return 'var(--status-green)';
}

const TYRE_COLORS: Record<string, string> = {
    SOFT: '#ff0000', MEDIUM: '#ffd700', HARD: '#e8e8e8',
    INTERMEDIATE: '#39d353', WET: '#0080ff',
};
const TYRE_TEXT: Record<string, string> = {
    SOFT: '#fff', MEDIUM: '#000', HARD: '#000', INTERMEDIATE: '#000', WET: '#fff',
};

// =============================================================================
// Section component
// =============================================================================

const Section: FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
    <div className="strategy-section">
        <div className="strategy-section-label">{label}</div>
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
                <div><span style={{ color: 'var(--text-muted)' }}>Deg </span><span style={{ color: getDegColor(driver.deg_slope) }}>{((driver.deg_slope || 0) * 1000).toFixed(0)}ms</span></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Cliff </span><span style={{ color: getCliffColor(driver.cliff_risk) }}>{Math.round((driver.cliff_risk || 0) * 100)}%</span></div>
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
    const lapTotal = totalLaps || 60;
    const winMin = driver.pit_window_min || 0;
    const winMax = driver.pit_window_max || 0;
    const winIdeal = driver.pit_window_ideal || 0;
    const hasPitWindow = winMin > 0 && winMax > 0;
    const minPct = hasPitWindow ? Math.max(0, Math.min(100, (winMin / lapTotal) * 100)) : 0;
    const maxPct = hasPitWindow ? Math.max(0, Math.min(100, (winMax / lapTotal) * 100)) : 0;
    const idealPct = hasPitWindow ? Math.max(0, Math.min(100, (winIdeal / lapTotal) * 100)) : 0;
    const currentPct = Math.max(0, Math.min(100, (currentLap / lapTotal) * 100));

    // 5-lap predicted pace sparkline (simple inline SVG)
    const pace = driver.predicted_pace || [];
    const sparky = pace.slice(0, 5);
    const sparkMin = sparky.length > 0 ? Math.min(...sparky) : 0;
    const sparkMax = sparky.length > 0 ? Math.max(...sparky) : 1;
    const sparkRange = sparkMax - sparkMin || 1;

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
                        <div style={{ fontWeight: 700, fontSize: '0.9rem', color: rec.color, letterSpacing: '0.04em' }}>{rec.text}</div>
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
                                <span style={{ color: 'var(--text-muted)' }}>MIN L{winMin}</span>
                                <span style={{ color: 'var(--color-info)', fontWeight: 700 }}>IDEAL L{winIdeal}</span>
                                <span style={{ color: 'var(--text-muted)' }}>MAX L{winMax}</span>
                            </div>
                            <div style={{ position: 'relative', height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '4px', overflow: 'visible' }}>
                                {/* Window range */}
                                <div style={{ position: 'absolute', top: 0, left: `${minPct}%`, width: `${maxPct - minPct}%`, height: '100%', background: 'rgba(88,166,255,0.2)', borderRadius: '4px' }} />
                                {/* Ideal marker */}
                                <div style={{ position: 'absolute', top: '-1px', left: `${idealPct}%`, width: '2px', height: '10px', background: 'var(--color-info)', transform: 'translateX(-50%)', borderRadius: '1px' }} />
                                {/* Current lap */}
                                <div style={{ position: 'absolute', top: '-2px', left: `${currentPct}%`, width: '3px', height: '12px', background: 'var(--text-secondary)', transform: 'translateX(-50%)', borderRadius: '1px' }} />
                            </div>
                            <div style={{ marginTop: '4px', fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                                L{currentLap} of {lapTotal} — {currentLap < winMin ? `Opens in ${winMin - currentLap}L` : currentLap <= winMax ? 'WINDOW OPEN' : 'Window closed'}
                            </div>
                        </>
                    ) : (
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>No pit window data</div>
                    )}
                </Section>

                {/* Threats */}
                {(driver.undercut_threat || driver.overcut_opportunity) && (
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
                    </Section>
                )}

                {/* Degradation */}
                <Section label="Tyre Degradation">
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                        <div>
                            <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginBottom: '2px' }}>DEG RATE</div>
                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 700, color: getDegColor(driver.deg_slope) }}>
                                {((driver.deg_slope || 0) * 1000).toFixed(0)} ms/L
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginBottom: '2px' }}>CLIFF RISK</div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <div style={{ flex: 1, height: '4px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                                    <div style={{ height: '100%', width: `${Math.round((driver.cliff_risk || 0) * 100)}%`, background: getCliffColor(driver.cliff_risk), borderRadius: '2px' }} />
                                </div>
                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: getCliffColor(driver.cliff_risk) }}>
                                    {Math.round((driver.cliff_risk || 0) * 100)}%
                                </span>
                            </div>
                        </div>
                    </div>
                </Section>

                {/* Predicted Pace */}
                {sparky.length > 0 && (
                    <Section label={`Predicted Pace (${confPct}% model conf)`}>
                        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '3px', height: '44px' }}>
                            {sparky.map((v, i) => {
                                const BAR_MAX = 30; // px — avoids % height in flex child
                                const barH = sparkRange > 0 ? Math.max(4, ((sparkMax - v) / sparkRange) * BAR_MAX) : BAR_MAX / 2;
                                const isFastest = v === sparkMin;
                                return (
                                    <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '3px', justifyContent: 'flex-end' }}>
                                        <div style={{ width: '100%', height: `${barH}px`, background: isFastest ? 'var(--status-green)' : 'rgba(88,166,255,0.4)', borderRadius: '2px 2px 0 0' }} />
                                        <div style={{ fontSize: '0.55rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>+{i + 1}</div>
                                    </div>
                                );
                            })}
                        </div>
                        <div style={{ marginTop: '2px', fontSize: '0.62rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                            Next: {sparky[0] ? `${sparky[0].toFixed(3)}s` : '—'}
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

                {/* Rejoin */}
                {(driver.predicted_rejoin_position || 0) > 0 && (
                    <Section label="Predicted Rejoin">
                        <div style={{ display: 'flex', gap: '16px', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
                            <div>
                                <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginBottom: '2px' }}>POSITION</div>
                                <div style={{ fontWeight: 700 }}>P{driver.predicted_rejoin_position}</div>
                            </div>
                            <div>
                                <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginBottom: '2px' }}>TRAFFIC</div>
                                <div style={{ color: (driver.rejoin_traffic_severity || 0) > 0.6 ? 'var(--status-red)' : (driver.rejoin_traffic_severity || 0) > 0.3 ? 'var(--status-amber)' : 'var(--status-green)' }}>
                                    {(driver.rejoin_traffic_severity || 0) > 0.6 ? 'HIGH' : (driver.rejoin_traffic_severity || 0) > 0.3 ? 'MED' : 'LOW'}
                                </div>
                            </div>
                        </div>
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
