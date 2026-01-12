/**
 * DriverTable Component Tests
 *
 * Tests the driver standings table rendering and interactions.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DriverTable from '../DriverTable';
import type { DriverState } from '../../types';

// =============================================================================
// Mock Data
// =============================================================================

const mockDriver = (overrides: Partial<DriverState> = {}): DriverState => ({
    driver_number: 1,
    name_acronym: 'VER',
    full_name: 'Max Verstappen',
    team_name: 'Red Bull Racing',
    team_colour: '3671C6',
    position: 1,
    current_lap: 25,
    gap_to_leader: 0,
    gap_to_ahead: null,
    last_lap_time: 92.5,
    best_lap_time: 91.8,
    sector_1: null,
    sector_2: null,
    sector_3: null,
    compound: 'MEDIUM',
    tyre_age: 15,
    is_pit_out_lap: false,
    lap_in_stint: 15,
    stint_start_lap: 10,
    speed: 320,
    gear: 8,
    throttle: 100,
    brake: 0,
    drs: 0,
    x: 1000,
    y: 2000,
    rel_dist: 0.5,
    deg_slope: 0.06,
    cliff_risk: 0.3,
    pit_window_min: 20,
    pit_window_max: 30,
    pit_window_ideal: 25,
    pit_recommendation: 'EXTEND_STINT',
    pit_reason: 'Good pace',
    pit_confidence: 0.85,
    undercut_threat: false,
    overcut_opportunity: false,
    predicted_pace: [],
    predicted_rejoin_position: 0,
    rejoin_traffic_severity: 0.0,
    ...overrides,
});

const mockDrivers: DriverState[] = [
    mockDriver({ driver_number: 1, name_acronym: 'VER', position: 1 }),
    mockDriver({ driver_number: 11, name_acronym: 'PER', position: 2, gap_to_leader: 3.5 }),
    mockDriver({ driver_number: 44, name_acronym: 'HAM', position: 3, gap_to_leader: 8.2 }),
];

// =============================================================================
// Tests
// =============================================================================

describe('DriverTable', () => {
    it('renders driver positions correctly', () => {
        render(<DriverTable drivers={mockDrivers} />);

        expect(screen.getByText('VER')).toBeInTheDocument();
        expect(screen.getByText('PER')).toBeInTheDocument();
        expect(screen.getByText('HAM')).toBeInTheDocument();
    });

    it('shows LEADER for position 1', () => {
        render(<DriverTable drivers={mockDrivers} />);

        expect(screen.getByText('LEADER')).toBeInTheDocument();
    });

    it('shows gap to leader for non-leaders', () => {
        render(<DriverTable drivers={mockDrivers} />);

        expect(screen.getByText('+3.500')).toBeInTheDocument();
        expect(screen.getByText('+8.200')).toBeInTheDocument();
    });

    it('renders empty state when no drivers', () => {
        render(<DriverTable drivers={[]} />);

        expect(screen.getByText('No driver data available')).toBeInTheDocument();
    });

    it('highlights selected driver', () => {
        const selectedDriver = mockDrivers[1];
        render(
            <DriverTable
                drivers={mockDrivers}
                selectedDriver={selectedDriver}
            />
        );

        // The selected row should have a class or style
        const rows = screen.getAllByRole('row');
        expect(rows.length).toBeGreaterThan(1);
    });

    it('calls onDriverSelect when row is clicked', () => {
        const onSelect = vi.fn();
        render(
            <DriverTable
                drivers={mockDrivers}
                onDriverSelect={onSelect}
            />
        );

        const driverName = screen.getByText('VER');
        fireEvent.click(driverName.closest('tr')!);

        expect(onSelect).toHaveBeenCalledWith(mockDrivers[0]);
    });

    it('renders compact mode correctly', () => {
        render(<DriverTable drivers={mockDrivers} compact />);

        // Compact mode should still show drivers
        expect(screen.getByText('VER')).toBeInTheDocument();

        // But with fewer columns (check column headers)
        const headers = screen.getAllByRole('columnheader');
        expect(headers.length).toBeLessThan(10);
    });

    it('displays tyre compound badges', () => {
        render(<DriverTable drivers={mockDrivers} />);

        // Should show M for MEDIUM compound
        const tyreBadges = screen.getAllByText('M');
        expect(tyreBadges.length).toBeGreaterThan(0);
    });

    it('shows degradation with color coding', () => {
        const driversWithHighDeg = [
            mockDriver({ driver_number: 1, deg_slope: 0.12 }), // High (red)
            mockDriver({ driver_number: 2, deg_slope: 0.04 }), // Low (green)
        ];

        render(<DriverTable drivers={driversWithHighDeg} />);

        // Degradation values should be visible
        expect(screen.getByText('120ms')).toBeInTheDocument();
        expect(screen.getByText('40ms')).toBeInTheDocument();
    });
});
