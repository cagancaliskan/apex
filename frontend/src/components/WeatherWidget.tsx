/**
 * Weather Widget Component
 *
 * Displays race weather conditions including track/air temperature,
 * humidity, wind speed/direction, and rain status.
 *
 * @module components/WeatherWidget
 */

import { useMemo, type FC } from 'react';
import { Thermometer, Droplets, Wind } from 'lucide-react';
import styles from './WeatherWidget.module.css';
import { WEATHER_HEAVY_RAIN_MM, WEATHER_HIGH_HUMIDITY_PCT, WEATHER_MED_HUMIDITY_PCT } from '../config/constants';
// WeatherWidget uses the global 'card' class from index.css for base card appearance

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

// =============================================================================
// Main Component
// =============================================================================

const WeatherWidget: FC<WeatherWidgetProps> = ({ weather, compact = false }) => {
    const hasWeatherData = weather && (weather.track_temp !== undefined || weather.air_temp !== undefined || weather.humidity !== undefined);

    if (!hasWeatherData) {
        return (
            <div className={`${styles.weatherWidget} card`} style={{ padding: 'var(--space-md)', textAlign: 'center' }}>
                <span className="text-muted" style={{ fontSize: '0.75rem' }}>Weather data unavailable</span>
            </div>
        );
    }

    const { track_temp = 35, air_temp = 25, humidity = 50, wind_speed = 10, wind_direction = 'N', rainfall = 0, is_raining = false } = weather || {};

    const isRaining = is_raining || rainfall > 0;

    const conditionLabel = useMemo((): string => {
        if (isRaining) {
            return rainfall > WEATHER_HEAVY_RAIN_MM ? 'Heavy Rain' : 'Light Rain';
        }
        if (humidity > WEATHER_HIGH_HUMIDITY_PCT) return 'Cloudy';
        if (humidity > WEATHER_MED_HUMIDITY_PCT) return 'Partly Cloudy';
        return 'Sunny';
    }, [isRaining, rainfall, humidity]);

    if (compact) {
        return (
            <div className={styles.weatherWidgetCompact} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)', padding: 'var(--space-sm) var(--space-md)', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)' }}>
                <Thermometer size={14} />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>{air_temp !== undefined ? `${Math.round(air_temp)}°C` : '-'}</span>
                <Droplets size={14} />
                <span style={{ fontSize: '0.7rem', color: isRaining ? 'var(--color-info)' : 'var(--text-muted)' }}>{isRaining ? conditionLabel : 'DRY'}</span>
            </div>
        );
    }

    return (
        <div className={`${styles.weatherWidget} card`}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-md)', paddingBottom: 'var(--space-sm)', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Weather</span>
                <Thermometer size={14} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-around', marginBottom: 'var(--space-md)' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                    <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Track</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem', fontWeight: 600, color: 'var(--color-orange)' }}>
                        {track_temp !== undefined ? `${Math.round(track_temp)}°C` : '-'}
                    </span>
                </div>
                <div style={{ width: 1, backgroundColor: 'rgba(255,255,255,0.1)' }} />
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                    <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Air</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem', fontWeight: 600, color: 'var(--status-amber)' }}>
                        {air_temp !== undefined ? `${Math.round(air_temp)}°C` : '-'}
                    </span>
                </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-sm)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Wind size={14} />
                    <div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 500 }}>{wind_speed !== undefined ? `${Math.round(wind_speed)} km/h` : '-'}</div>
                        <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>Wind {wind_direction || ''}</div>
                    </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 500 }}>{humidity !== undefined ? `${Math.round(humidity)}%` : '-'}</div>
                    <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>Humidity</div>
                </div>
            </div>

            <div style={{ paddingTop: 'var(--space-sm)', borderTop: '1px solid rgba(255, 255, 255, 0.05)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Droplets size={14} />
                <span style={{ fontSize: '0.7rem', color: isRaining ? 'var(--color-info)' : 'var(--text-muted)' }}>
                    {isRaining ? conditionLabel : 'DRY'}
                </span>
            </div>
        </div>
    );
};

export default WeatherWidget;
