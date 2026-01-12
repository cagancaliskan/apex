/**
 * StrategyPanel component tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StrategyPanel from '../StrategyPanel';
import type { DriverState } from '../../types';

describe('StrategyPanel', () => {
    const mockDriver: DriverState = {
        driver_number: 1,
        name_acronym: 'VER',
        full_name: 'Max Verstappen',
        team_name: 'Red Bull Racing',
        team_colour: '3671C6',
        position: 1,
        current_lap: 25,
        last_lap_time: 90.5,
        best_lap_time: 89.5,
        gap_to_leader: 0,
        gap_to_ahead: null,
        sector_1: 25.1,
        sector_2: 30.2,
        sector_3: 35.2,
        speed: 300,
        gear: 8,
        throttle: 100,
        brake: 0,
        drs: 0,
        rel_dist: 0.5,
        x: 1000,
        y: 1000,
        compound: 'MEDIUM',
        tyre_age: 15,
        is_pit_out_lap: false,
        lap_in_stint: 15,
        stint_start_lap: 10,
        pit_recommendation: 'STAY_OUT',
        pit_confidence: 0.75,
        pit_reason: 'Low degradation - extend stint',
        pit_window_min: 20,
        pit_window_max: 35,
        pit_window_ideal: 27,
        deg_slope: 0.05,
        cliff_risk: 0.3,
        undercut_threat: false,
        overcut_opportunity: true,
        predicted_pace: [],
        predicted_rejoin_position: 0,
        rejoin_traffic_severity: 0.0,
    };

    it('renders driver info', () => {
        render(<StrategyPanel drivers={[mockDriver]} selectedDriver={mockDriver} />);
        expect(screen.getAllByText(/VER/)[0]).toBeInTheDocument();
    });
    // ...
    it('shows no driver message when empty', () => {
        render(<StrategyPanel drivers={[]} selectedDriver={null} />);
        expect(screen.getByText(/No driver selected/)).toBeInTheDocument();
    });

    it('shows PIT NOW for high risk', () => {
        const urgentDriver: DriverState = {
            ...mockDriver,
            pit_recommendation: 'PIT_NOW',
            cliff_risk: 0.9,
        };

        render(<StrategyPanel drivers={[urgentDriver]} selectedDriver={urgentDriver} />);
        expect(screen.getByText(/PIT NOW/)).toBeInTheDocument();
    });
});
