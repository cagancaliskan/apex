/**
 * Weather Widget Component
 *
 * Displays race weather conditions including track/air temperature,
 * humidity, wind speed/direction, and rain status.
 *
 * @module components/WeatherWidget
 */

import { useMemo, type FC } from 'react';

// =============================================================================
// Types
// =============================================================================

interface WeatherData {
    track_temp?: number;
    air_temp?: number;
    humidity?: number;
    wind_speed?: number;
    wind_direction?: string | number;
    rainfall?: number;
    is_raining?: boolean;
}

interface WeatherWidgetProps {
    weather?: WeatherData | null;
    compact?: boolean;
}

type WeatherCondition = 'sunny' | 'cloudy' | 'partly_cloudy' | 'rain' | 'heavy_rain';

// =============================================================================
// Sub-Components
// =============================================================================

interface WeatherIconProps {
    condition: WeatherCondition;
    size?: number;
}

const WeatherIcon: FC<WeatherIconProps> = ({ condition, size = 24 }) => {
    const icons: Record<WeatherCondition, JSX.Element> = {
        sunny: (
            <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
            </svg>
        ),
        cloudy: (
            <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" />
            </svg>
        ),
        partly_cloudy: (
            <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 3v1M5.6 5.6l.7.7M3 12h1M5.6 18.4l.7-.7" />
                <circle cx="12" cy="10" r="4" />
                <path d="M20 16.2A5 5 0 0 0 15 10H13.2a6 6 0 0 0-10.6 4.8" />
                <path d="M15 21.1a5 5 0 0 0 5-5.1h-5" />
            </svg>
        ),
        rain: (
            <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M16 13v8M8 13v8M12 15v8" />
                <path d="M18 8h-1.26a8 8 0 1 0-9.74 0H6a4 4 0 0 0 0 8h12a4 4 0 0 0 0-8z" />
            </svg>
        ),
        heavy_rain: (
            <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M16 13v8M8 13v8M12 15v8M4 17v4M20 17v4" />
                <path d="M18 8h-1.26a8 8 0 1 0-9.74 0H6a4 4 0 0 0 0 8h12a4 4 0 0 0 0-8z" />
            </svg>
        ),
    };

    return <div style={{ color: 'var(--text-secondary)' }}>{icons[condition] || icons.cloudy}</div>;
};

interface WindArrowProps {
    direction: string | number;
    size?: number;
}

const WindArrow: FC<WindArrowProps> = ({ direction, size = 16 }) => {
    const directionMap: Record<string, number> = {
        N: 0, NNE: 22.5, NE: 45, ENE: 67.5,
        E: 90, ESE: 112.5, SE: 135, SSE: 157.5,
        S: 180, SSW: 202.5, SW: 225, WSW: 247.5,
        W: 270, WNW: 292.5, NW: 315, NNW: 337.5,
    };

    const rotation = typeof direction === 'number' ? direction : directionMap[direction] || 0;

    return (
        <svg width={size} height={size} viewBox="0 0 24 24" style={{ transform: `rotate(${rotation}deg)`, transition: 'transform 0.3s ease' }}>
            <path d="M12 2L8 10h8L12 2z" fill="var(--accent-cyan)" />
            <path d="M12 22V10" stroke="var(--text-muted)" strokeWidth="2" />
        </svg>
    );
};

interface TemperatureDisplayProps {
    value?: number;
    label: string;
    min?: number;
    max?: number;
    unit?: string;
}

const TemperatureDisplay: FC<TemperatureDisplayProps> = ({ value, label, min = 10, max = 50, unit = '°C' }) => {
    const percentage = value !== undefined ? Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100)) : 50;

    let color = 'var(--accent-cyan)';
    if (percentage > 70) color = 'var(--status-red)';
    else if (percentage > 50) color = 'var(--accent-orange)';
    else if (percentage > 30) color = 'var(--accent-yellow)';

    return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
            <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</span>
            <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', fontWeight: 600, color }}>
                {value !== undefined ? `${Math.round(value)}${unit}` : '-'}
            </span>
        </div>
    );
};

interface RainIndicatorProps {
    isRaining: boolean;
    rainfall?: number;
}

const RainIndicator: FC<RainIndicatorProps> = ({ isRaining, rainfall = 0 }) => {
    if (!isRaining && rainfall === 0) {
        return (
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: 'var(--status-green)' }} />
                DRY
            </div>
        );
    }

    const intensity = rainfall > 2 ? 'Heavy' : rainfall > 0.5 ? 'Light' : 'Drizzle';

    return (
        <div style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: 'var(--accent-cyan)', animation: 'pulse 1s ease-in-out infinite' }} />
            {intensity} Rain
        </div>
    );
};

// =============================================================================
// Main Component
// =============================================================================

const WeatherWidget: FC<WeatherWidgetProps> = ({ weather, compact = false }) => {
    const hasWeatherData = weather && (weather.track_temp !== undefined || weather.air_temp !== undefined || weather.humidity !== undefined);

    if (!hasWeatherData) {
        return (
            <div className="weather-widget card" style={{ padding: 'var(--space-md)', textAlign: 'center' }}>
                <span className="text-muted" style={{ fontSize: '0.75rem' }}>Weather data unavailable</span>
            </div>
        );
    }

    const { track_temp = 35, air_temp = 25, humidity = 50, wind_speed = 10, wind_direction = 'N', rainfall = 0, is_raining = false } = weather || {};

    const condition = useMemo((): WeatherCondition => {
        if (is_raining || rainfall > 0) {
            return rainfall > 2 ? 'heavy_rain' : 'rain';
        }
        if (humidity > 80) return 'cloudy';
        if (humidity > 50) return 'partly_cloudy';
        return 'sunny';
    }, [is_raining, rainfall, humidity]);

    if (compact) {
        return (
            <div className="weather-widget-compact" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)', padding: 'var(--space-sm) var(--space-md)', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)' }}>
                <WeatherIcon condition={condition} size={20} />
                <span style={{ fontFamily: 'var(--font-display)', fontSize: '0.85rem' }}>{air_temp !== undefined ? `${Math.round(air_temp)}°C` : '-'}</span>
                <RainIndicator isRaining={is_raining} rainfall={rainfall} />
            </div>
        );
    }

    return (
        <div className="weather-widget card card-glow">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-md)', paddingBottom: 'var(--space-sm)', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Weather</span>
                <WeatherIcon condition={condition} size={24} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-around', marginBottom: 'var(--space-md)' }}>
                <TemperatureDisplay value={track_temp} label="Track" min={15} max={60} />
                <div style={{ width: 1, backgroundColor: 'rgba(255,255,255,0.1)' }} />
                <TemperatureDisplay value={air_temp} label="Air" min={5} max={40} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-sm)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <WindArrow direction={wind_direction} size={18} />
                    <div>
                        <div style={{ fontSize: '0.8rem', fontWeight: 500 }}>{wind_speed !== undefined ? `${Math.round(wind_speed)} km/h` : '-'}</div>
                        <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>Wind {wind_direction || ''}</div>
                    </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 500 }}>{humidity !== undefined ? `${Math.round(humidity)}%` : '-'}</div>
                    <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>Humidity</div>
                </div>
            </div>

            <div style={{ paddingTop: 'var(--space-sm)', borderTop: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <RainIndicator isRaining={is_raining} rainfall={rainfall} />
            </div>
        </div>
    );
};

export default WeatherWidget;
export { WeatherIcon, WindArrow, TemperatureDisplay, RainIndicator };
