/**
 * Competitor Predictions Component
 * 
 * Displays predicted pit laps for rival drivers based on
 * team profiles and driver behaviors from the enhanced CompetitorAI.
 * 
 * New in v3.0.1
 */

import type { FC } from 'react';
import type { DriverState } from '../types';

interface CompetitorPredictionsProps {
    /** All drivers in race order */
    drivers: DriverState[];
    /** Selected driver to show rivals for */
    selectedDriverNumber?: number;
}

interface RivalPrediction {
    driverNumber: number;
    name: string;
    team: string;
    position: number;
    predictedPitLap: number;
    confidence: number;
    compound: string;
    tyreAge: number;
}

function getTeamColor(team: string): string {
    const colors: Record<string, string> = {
        'Red Bull Racing': '#3671c6',
        'Mercedes': '#27f4d2',
        'Ferrari': '#e80020',
        'McLaren': '#ff8000',
        'Aston Martin': '#229971',
        'Alpine': '#ff87bc',
        'Williams': '#64c4ff',
        'RB': '#6692ff',
        'Haas F1 Team': '#b6babd',
        'Kick Sauber': '#52e252',
    };
    return colors[team] || '#888888';
}

/**
 * Single rival prediction row
 */
const RivalRow: FC<{ rival: RivalPrediction }> = ({ rival }) => (
    <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-xs)',
        padding: 'var(--space-xs)',
        background: 'var(--bg-tertiary)',
        borderRadius: 'var(--radius-sm)',
        borderLeft: `3px solid ${getTeamColor(rival.team)}`
    }}>
        {/* Position & Name */}
        <span style={{
            width: '24px',
            fontFamily: 'var(--font-sans)',
            fontWeight: 700,
            fontSize: '0.75rem',
            color: 'var(--text-muted)'
        }}>
            P{rival.position}
        </span>
        <span style={{
            fontFamily: 'var(--font-sans)',
            fontWeight: 600,
            fontSize: '0.8rem',
            flex: 1
        }}>
            {rival.name}
        </span>

        {/* Current tyre */}
        <div style={{
            width: '20px',
            height: '20px',
            borderRadius: '50%',
            background: rival.compound === 'SOFT' ? '#ff3333' :
                rival.compound === 'MEDIUM' ? '#ffcc00' : '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.6rem',
            fontWeight: 700,
            color: rival.compound === 'HARD' ? '#333' : '#fff'
        }}>
            {rival.tyreAge}
        </div>

        {/* Predicted pit */}
        <div style={{
            textAlign: 'right',
            minWidth: '50px'
        }}>
            <div style={{
                fontFamily: 'var(--font-sans)',
                fontWeight: 700,
                fontSize: '0.85rem',
                color: 'var(--color-info)'
            }}>
                L{rival.predictedPitLap}
            </div>
            <div style={{
                fontSize: '0.55rem',
                color: 'var(--text-muted)'
            }}>
                {(rival.confidence * 100).toFixed(0)}% conf
            </div>
        </div>
    </div>
);

/**
 * Competitor Predictions panel showing expected pit laps for rivals.
 */
const CompetitorPredictions: FC<CompetitorPredictionsProps> = ({
    drivers,
    selectedDriverNumber
}) => {
    // Get rivals (drivers within 3 positions of selected driver)
    const selectedDriver = drivers.find(d => d.driver_number === selectedDriverNumber);
    const selectedPosition = selectedDriver?.position || 1;

    // Use real strategy data from the backend (pit_window_ideal, pit_confidence)
    const rivals: RivalPrediction[] = drivers
        .filter(d =>
            d.driver_number !== selectedDriverNumber &&
            d.position &&
            Math.abs(d.position - selectedPosition) <= 3
        )
        .slice(0, 4)
        .map(d => ({
            driverNumber: d.driver_number,
            name: d.name_acronym || `#${d.driver_number}`,
            team: d.team_name || 'Unknown',
            position: d.position || 0,
            predictedPitLap: d.pit_window_ideal || d.pit_window_min || 0,
            confidence: d.pit_confidence || 0.5,
            compound: d.compound || 'MEDIUM',
            tyreAge: d.tyre_age || d.lap_in_stint || 0
        }));

    if (rivals.length === 0) {
        return null;
    }

    return (
        <div style={{ marginTop: 'var(--space-md)' }}>
            <div style={{
                fontSize: '0.75rem',
                color: 'var(--text-muted)',
                marginBottom: 'var(--space-xs)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
            }}>
                Rival Pit Predictions
            </div>

            <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-xs)'
            }}>
                {rivals.map(rival => (
                    <RivalRow key={rival.driverNumber} rival={rival} />
                ))}
            </div>
        </div>
    );
};

export default CompetitorPredictions;
