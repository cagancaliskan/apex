/**
 * Race Progress Bar Component
 *
 * Interactive timeline showing race progress with event markers.
 * Features: DNF markers, safety car periods, red flags, lap markers, clickable seek.
 *
 * @module components/RaceProgressBar
 */

import { useMemo, useState, useRef, useCallback, type FC, type MouseEvent } from 'react';

// =============================================================================
// Types
// =============================================================================

interface EventMarkerProps {
    type: 'dnf' | 'pit' | 'overtake' | 'fastest_lap';
    position: number;
    label: string;
    onClick?: () => void;
}

interface FlagPeriodData {
    startPercent: number;
    endPercent: number;
    type: 'safety_car' | 'red_flag' | 'vsc' | 'yellow';
}

interface RaceEvent {
    type: 'dnf' | 'pit' | 'overtake' | 'fastest_lap';
    position: number;
    label: string;
    lap?: number;
}

interface SeekData {
    lap?: number;
    time?: number;
    percent: number;
}

interface RaceProgressBarProps {
    currentLap?: number;
    totalLaps?: number;
    currentTime?: number;
    totalTime?: number;
    events?: RaceEvent[];
    flagPeriods?: FlagPeriodData[];
    onSeek?: (data: SeekData) => void;
    showLapMarkers?: boolean;
}

// =============================================================================
// Sub-Components
// =============================================================================

const EventMarker: FC<EventMarkerProps> = ({ type, position, label, onClick }) => {
    const markerStyles: Record<string, { color: string; symbol: string; tooltip: string }> = {
        dnf: { color: 'var(--status-red)', symbol: '×', tooltip: `DNF: ${label}` },
        pit: { color: 'var(--accent-yellow)', symbol: '●', tooltip: `Pit: ${label}` },
        overtake: { color: 'var(--accent-cyan)', symbol: '↑', tooltip: `Overtake: ${label}` },
        fastest_lap: { color: 'var(--accent-purple)', symbol: '⚡', tooltip: `Fastest Lap: ${label}` },
    };
    const style = markerStyles[type] || markerStyles.pit;

    return (
        <div className="event-marker" style={{ position: 'absolute', left: `${position}%`, top: '50%', transform: 'translate(-50%, -50%)', cursor: 'pointer', zIndex: 10 }} onClick={onClick} title={style.tooltip}>
            <div style={{ width: 14, height: 14, borderRadius: '50%', backgroundColor: style.color, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 'bold', color: 'black', boxShadow: `0 0 6px ${style.color}` }}>{style.symbol}</div>
        </div>
    );
};

const FlagPeriod: FC<FlagPeriodData> = ({ startPercent, endPercent, type }) => {
    const colors: Record<string, string> = { safety_car: 'rgba(255, 208, 0, 0.4)', red_flag: 'rgba(255, 0, 85, 0.5)', vsc: 'rgba(255, 165, 0, 0.3)', yellow: 'rgba(255, 208, 0, 0.25)' };
    const borderColors: Record<string, string> = { safety_car: 'var(--accent-yellow)', red_flag: 'var(--status-red)', vsc: 'var(--accent-orange)', yellow: 'var(--accent-yellow)' };

    return (
        <div className="flag-period" style={{ position: 'absolute', left: `${startPercent}%`, width: `${endPercent - startPercent}%`, top: 0, bottom: 0, backgroundColor: colors[type] || colors.yellow, borderLeft: `2px solid ${borderColors[type] || borderColors.yellow}`, borderRight: `2px solid ${borderColors[type] || borderColors.yellow}`, zIndex: 1 }} title={type.replace('_', ' ').toUpperCase()} />
    );
};

interface LapMarkerProps {
    position: number;
    lapNumber: number;
    totalLaps: number;
}

const LapMarker: FC<LapMarkerProps> = ({ position, lapNumber, totalLaps }) => {
    if (lapNumber % 5 !== 0 && lapNumber !== 1 && lapNumber !== totalLaps) return null;
    return (
        <div className="lap-marker" style={{ position: 'absolute', left: `${position}%`, top: 0, bottom: 0, width: 1, backgroundColor: 'rgba(255, 255, 255, 0.15)', zIndex: 0 }}>
            <span style={{ position: 'absolute', top: -16, left: '50%', transform: 'translateX(-50%)', fontSize: '0.6rem', color: 'var(--text-muted)' }}>L{lapNumber}</span>
        </div>
    );
};

// =============================================================================
// Main Component
// =============================================================================

const RaceProgressBar: FC<RaceProgressBarProps> = ({
    currentLap = 0,
    totalLaps = 0,
    currentTime = 0,
    totalTime = 0,
    events = [],
    flagPeriods = [],
    onSeek,
    showLapMarkers = true,
}) => {
    const barRef = useRef<HTMLDivElement>(null);
    const [hoveredPosition, setHoveredPosition] = useState<number | null>(null);
    const [isDragging, setIsDragging] = useState(false);

    const progress = useMemo(() => {
        if (totalLaps > 0) return Math.min(100, (currentLap / totalLaps) * 100);
        if (totalTime > 0) return Math.min(100, (currentTime / totalTime) * 100);
        return 0;
    }, [currentLap, totalLaps, currentTime, totalTime]);

    const handleSeek = useCallback((e: MouseEvent<HTMLDivElement>) => {
        if (!barRef.current || !onSeek) return;
        const rect = barRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const percent = Math.max(0, Math.min(100, (x / rect.width) * 100));
        if (totalLaps > 0) onSeek({ lap: Math.round((percent / 100) * totalLaps), percent });
        else if (totalTime > 0) onSeek({ time: (percent / 100) * totalTime, percent });
    }, [onSeek, totalLaps, totalTime]);

    const handleMouseMove = useCallback((e: MouseEvent<HTMLDivElement>) => {
        if (!barRef.current) return;
        const rect = barRef.current.getBoundingClientRect();
        const percent = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
        setHoveredPosition(percent);
        if (isDragging) handleSeek(e);
    }, [isDragging, handleSeek]);

    const lapMarkers = useMemo(() => !showLapMarkers || totalLaps === 0 ? [] : Array.from({ length: totalLaps }, (_, i) => ({ lap: i + 1, position: ((i + 1) / totalLaps) * 100 })), [showLapMarkers, totalLaps]);

    return (
        <div className="race-progress-bar-container" style={{ padding: '24px 16px 8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Race Progress</span>
                <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-display)', color: 'var(--text-secondary)' }}>
                    <span style={{ color: 'var(--accent-cyan)' }}>{currentLap}</span>
                    <span style={{ color: 'var(--text-muted)' }}>/{totalLaps}</span>
                </span>
            </div>

            <div ref={barRef} className="race-progress-bar" style={{ position: 'relative', height: 20, backgroundColor: 'var(--bg-tertiary)', borderRadius: 10, overflow: 'visible', cursor: onSeek ? 'pointer' : 'default' }} onMouseMove={handleMouseMove} onMouseDown={(e) => { setIsDragging(true); handleSeek(e); }} onMouseUp={() => setIsDragging(false)} onMouseLeave={() => { setHoveredPosition(null); setIsDragging(false); }}>
                {lapMarkers.map(({ lap, position }) => <LapMarker key={lap} position={position} lapNumber={lap} totalLaps={totalLaps} />)}
                {flagPeriods.map((period, index) => <FlagPeriod key={index} {...period} />)}
                <div className="progress-fill" style={{ position: 'absolute', top: 0, left: 0, bottom: 0, width: `${progress}%`, background: 'linear-gradient(90deg, var(--accent-cyan), var(--accent-magenta))', borderRadius: 10, transition: isDragging ? 'none' : 'width 0.3s ease', zIndex: 2 }} />
                <div className="progress-head" style={{ position: 'absolute', left: `${progress}%`, top: '50%', transform: 'translate(-50%, -50%)', width: 12, height: 12, borderRadius: '50%', backgroundColor: 'white', boxShadow: '0 0 8px var(--accent-cyan), 0 2px 4px rgba(0,0,0,0.3)', zIndex: 15, transition: isDragging ? 'none' : 'left 0.3s ease' }} />
                {events.map((event, index) => <EventMarker key={index} type={event.type} position={event.position} label={event.label} onClick={() => onSeek?.({ lap: event.lap, percent: event.position })} />)}
                {hoveredPosition !== null && onSeek && <div style={{ position: 'absolute', left: `${hoveredPosition}%`, top: 0, bottom: 0, width: 2, backgroundColor: 'rgba(255, 255, 255, 0.5)', transform: 'translateX(-50%)', zIndex: 5, pointerEvents: 'none' }} />}
            </div>

            <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}><div style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: 'var(--status-red)' }} />DNF</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}><div style={{ width: 12, height: 6, backgroundColor: 'rgba(255, 208, 0, 0.5)', borderRadius: 2 }} />SC</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}><div style={{ width: 12, height: 6, backgroundColor: 'rgba(255, 0, 85, 0.5)', borderRadius: 2 }} />Red Flag</div>
            </div>
        </div>
    );
};

export default RaceProgressBar;
export { EventMarker, FlagPeriod, LapMarker };
