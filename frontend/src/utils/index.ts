/**
 * Utility functions for the F1 Dashboard.
 */

import type { TyreCompound } from '../types';

// =============================================================================
// Formatting Utilities
// =============================================================================

/**
 * Format lap time from seconds to standard F1 format (M:SS.mmm)
 */
export function formatLapTime(seconds: number | null | undefined): string {
    if (seconds === null || seconds === undefined) return '-';

    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(3);

    return mins > 0 ? `${mins}:${secs.padStart(6, '0')}` : secs;
}

/**
 * Format gap to leader/ahead
 */
export function formatGap(gap: number | null | undefined): string {
    if (gap === null || gap === undefined) return '-';
    if (gap === 0) return 'LEADER';

    return `+${gap.toFixed(3)}`;
}

/**
 * Format interval to car ahead
 */
export function formatInterval(interval: number | null | undefined): string {
    if (interval === null || interval === undefined) return '-';

    return `+${interval.toFixed(3)}`;
}

// =============================================================================
// Tyre Utilities
// =============================================================================

/**
 * Get tyre compound display letter
 */
export function getTyreLabel(compound: string | null | undefined): string {
    if (!compound) return '?';

    const labels: Record<string, string> = {
        SOFT: 'S',
        MEDIUM: 'M',
        HARD: 'H',
        INTERMEDIATE: 'I',
        WET: 'W',
        UNKNOWN: '?',
    };

    return labels[compound.toUpperCase()] ?? '?';
}

/**
 * Get tyre compound CSS class
 */
export function getTyreClass(compound: string | null | undefined): string {
    if (!compound) return '';
    return compound.toLowerCase();
}

/**
 * Get tyre compound color
 */
export function getTyreColor(compound: TyreCompound | string | null): string {
    if (!compound) return '#888';

    const colors: Record<string, string> = {
        SOFT: '#ff2222',
        MEDIUM: '#ffcc00',
        HARD: '#ffffff',
        INTERMEDIATE: '#44dd44',
        WET: '#4488ff',
    };

    return colors[compound.toUpperCase()] ?? '#888';
}

// =============================================================================
// Number Utilities
// =============================================================================

/**
 * Clamp a value between min and max
 */
export function clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value));
}

/**
 * Linear interpolation
 */
export function lerp(start: number, end: number, t: number): number {
    return start + (end - start) * clamp(t, 0, 1);
}

// =============================================================================
// Team Colors
// =============================================================================

export const TEAM_COLORS: Record<string, string> = {
    'Red Bull Racing': '#3671C6',
    'Ferrari': '#E8002D',
    'Mercedes': '#27F4D2',
    'McLaren': '#FF8000',
    'Aston Martin': '#229971',
    'Alpine': '#FF87BC',
    'Williams': '#64C4FF',
    'RB': '#6692BC',
    'Kick Sauber': '#52E252',
    'Haas F1 Team': '#B6BABD',
};

/**
 * Get team color by name
 */
export function getTeamColor(teamName: string | null | undefined): string {
    if (!teamName) return '#888';
    return TEAM_COLORS[teamName] ?? '#888';
}
