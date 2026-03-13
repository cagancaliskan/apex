import { describe, it, expect, beforeEach } from 'vitest';
import { useRaceStore } from './raceStore';

describe('raceStore — alert slice', () => {
    beforeEach(() => {
        useRaceStore.getState().reset();
    });

    it('starts with empty alerts', () => {
        expect(useRaceStore.getState().alerts).toEqual([]);
    });

    it('addAlert adds an alert', () => {
        useRaceStore.getState().addAlert('PIT_NOW', 'HAM — PIT NOW');
        const { alerts } = useRaceStore.getState();
        expect(alerts).toHaveLength(1);
        expect(alerts[0].type).toBe('PIT_NOW');
        expect(alerts[0].message).toBe('HAM — PIT NOW');
        expect(alerts[0].id).toBeTruthy();
        expect(alerts[0].ts).toBeGreaterThan(0);
    });

    it('does not duplicate same type within 30s', () => {
        useRaceStore.getState().addAlert('SC', 'SAFETY CAR');
        useRaceStore.getState().addAlert('SC', 'SAFETY CAR AGAIN');
        expect(useRaceStore.getState().alerts).toHaveLength(1);
    });

    it('dismissAlert removes alert by id', () => {
        useRaceStore.getState().addAlert('FLAG', 'YELLOW FLAG');
        const id = useRaceStore.getState().alerts[0].id;
        useRaceStore.getState().dismissAlert(id);
        expect(useRaceStore.getState().alerts).toHaveLength(0);
    });

    it('reset clears alerts', () => {
        useRaceStore.getState().addAlert('FLAG', 'RED FLAG');
        useRaceStore.getState().reset();
        expect(useRaceStore.getState().alerts).toHaveLength(0);
    });
});
