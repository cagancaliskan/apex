/**
 * useAlerts — subscribes to race state and dispatches alerts to raceStore.
 *
 * Call this hook once from LiveDashboard. It generates alerts for:
 * - Safety car / red flag / yellow flag deployment
 * - PIT_NOW recommendations
 * - Undercut threats
 */
import { useEffect, useRef } from 'react';
import { useRaceStore } from '../store/raceStore';

export function useAlerts() {
    const addAlert = useRaceStore(s => s.addAlert);
    const safetycar = useRaceStore(s => s.safetycar);
    const redFlag = useRaceStore(s => s.redFlag);
    const vsc = useRaceStore(s => s.virtualSafetyCar);
    const flags = useRaceStore(s => s.flags);
    const sortedDrivers = useRaceStore(s => s.sortedDrivers);

    const prevRef = useRef({ sc: false, red: false, vsc: false, flags: [] as string[] });

    // Flag / SC alerts
    useEffect(() => {
        const prev = prevRef.current;
        if (redFlag && !prev.red) addAlert('FLAG', 'RED FLAG DEPLOYED');
        if (safetycar && !prev.sc) addAlert('SC', 'SAFETY CAR DEPLOYED');
        if (vsc && !prev.vsc) addAlert('SC', 'VIRTUAL SAFETY CAR');
        const hasYellow = flags.some(f => f === 'YELLOW' || f === 'DOUBLE_YELLOW');
        const prevHasYellow = prev.flags.some(f => f === 'YELLOW' || f === 'DOUBLE_YELLOW');
        if (hasYellow && !prevHasYellow) addAlert('FLAG', 'YELLOW FLAG');
        prevRef.current = { sc: safetycar, red: redFlag, vsc, flags };
    }, [redFlag, safetycar, vsc, flags, addAlert]);

    // PIT_NOW / undercut alerts
    useEffect(() => {
        sortedDrivers.forEach(d => {
            if (d.pit_recommendation === 'PIT_NOW') {
                addAlert('PIT_NOW', `${d.name_acronym} — PIT NOW (cliff: ${Math.round((d.cliff_risk || 0) * 100)}%)`);
            }
            if (d.undercut_threat) {
                addAlert('THREAT', `${d.name_acronym} — UNDERCUT THREAT from ${(d.position ?? 0) > 1 ? `P${(d.position ?? 0) - 1}` : 'behind'}`);
            }
        });
    }, [sortedDrivers, addAlert]);
}
