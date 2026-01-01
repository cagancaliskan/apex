/**
 * StrategyPanel component tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import StrategyPanel from '../components/StrategyPanel'

describe('StrategyPanel', () => {
    const mockDriver = {
        driver_number: 1,
        name_acronym: 'VER',
        position: 1,
        current_lap: 25,
        pit_recommendation: 'STAY_OUT',
        pit_confidence: 0.75,
        pit_reason: 'Low degradation - extend stint',
        pit_window_min: 20,
        pit_window_max: 35,
        pit_window_ideal: 27,
        deg_slope: 0.05,
        cliff_risk: 0.3,
        tyre_age: 15,
        undercut_threat: false,
        overcut_opportunity: true,
    }

    it('renders driver info', () => {
        render(<StrategyPanel drivers={[mockDriver]} selectedDriver={null} />)

        expect(screen.getByText(/VER/)).toBeInTheDocument()
    })

    it('shows STAY OUT recommendation', () => {
        render(<StrategyPanel drivers={[mockDriver]} selectedDriver={null} />)

        expect(screen.getByText(/STAY OUT/)).toBeInTheDocument()
    })

    it('shows confidence percentage', () => {
        render(<StrategyPanel drivers={[mockDriver]} selectedDriver={null} />)

        expect(screen.getByText(/75%/)).toBeInTheDocument()
    })

    it('shows pit reason', () => {
        render(<StrategyPanel drivers={[mockDriver]} selectedDriver={null} />)

        expect(screen.getByText(/Low degradation/)).toBeInTheDocument()
    })

    it('shows overcut opportunity badge', () => {
        render(<StrategyPanel drivers={[mockDriver]} selectedDriver={null} />)

        expect(screen.getByText(/OVERCUT VIABLE/)).toBeInTheDocument()
    })

    it('shows no driver message when empty', () => {
        render(<StrategyPanel drivers={[]} selectedDriver={null} />)

        expect(screen.getByText(/No driver selected/)).toBeInTheDocument()
    })

    it('shows PIT NOW for high risk', () => {
        const urgentDriver = {
            ...mockDriver,
            pit_recommendation: 'PIT_NOW',
            cliff_risk: 0.9,
        }

        render(<StrategyPanel drivers={[urgentDriver]} selectedDriver={null} />)

        expect(screen.getByText(/PIT NOW/)).toBeInTheDocument()
    })
})
