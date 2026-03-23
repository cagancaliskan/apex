/**
 * Utility functions for the F1 Dashboard.
 */

import type { TyreCompound } from '../types';
import { TYRE_COLORS } from '../config/constants';

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
    return TYRE_COLORS[compound.toUpperCase()] ?? '#888';
}

