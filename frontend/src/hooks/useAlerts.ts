/**
 * useAlerts — subscribes to race state and dispatches alerts to raceStore.
 *
 * Call this hook once from LiveDashboard. It generates alerts for:
 * - Safety car / red flag / yellow flag deployment
 * - PIT_NOW recommendations
 * - Undercut threats
 *
 * Alerts are stored in raceStore.alerts and consumed by App.tsx alert strip.
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
    const timeoutsRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

    // Clear all tracked timeouts on unmount
    useEffect(() => {
        return () => {
            timeoutsRef.current.forEach(t => clearTimeout(t));
            timeoutsRef.current.clear();
        };
    }, []);

    // Helper: after an addAlert call, find the newly added alert (within last 100ms)
    // and schedule auto-dismiss after 10 seconds.
    function scheduleAutoDismiss() {
        const now = Date.now();
        const stored = useRaceStore.getState().alerts;
        const newAlert = stored[0]; // most recent is first
        if (newAlert && newAlert.ts > now - 100) {
            // Clear any existing timeout for this id (safety)
            const existing = timeoutsRef.current.get(newAlert.id);
            if (existing) clearTimeout(existing);
            const t = setTimeout(() => {
                useRaceStore.getState().dismissAlert(newAlert.id);
                timeoutsRef.current.delete(newAlert.id);
            }, 10000);
            timeoutsRef.current.set(newAlert.id, t);
        }
    }

    // Flag / SC alerts
    useEffect(() => {
        const prev = prevRef.current;
        if (redFlag && !prev.red) { addAlert('FLAG', 'RED FLAG DEPLOYED'); scheduleAutoDismiss(); }
        if (safetycar && !prev.sc) { addAlert('SC', 'SAFETY CAR DEPLOYED'); scheduleAutoDismiss(); }
        if (vsc && !prev.vsc) { addAlert('SC', 'VIRTUAL SAFETY CAR'); scheduleAutoDismiss(); }
        const hasYellow = flags.some(f => f === 'YELLOW' || f === 'DOUBLE_YELLOW');
        const prevHasYellow = prev.flags.some(f => f === 'YELLOW' || f === 'DOUBLE_YELLOW');
        if (hasYellow && !prevHasYellow) { addAlert('FLAG', 'YELLOW FLAG'); scheduleAutoDismiss(); }
        prevRef.current = { sc: safetycar, red: redFlag, vsc, flags };
    }, [redFlag, safetycar, vsc, flags, addAlert]);

    // PIT_NOW / undercut alerts
    useEffect(() => {
        sortedDrivers.forEach(d => {
            if (d.pit_recommendation === 'PIT_NOW') {
                addAlert('PIT_NOW', `${d.name_acronym} — PIT NOW (cliff: ${Math.round((d.cliff_risk || 0) * 100)}%)`);
                scheduleAutoDismiss();
            }
            if (d.undercut_threat) {
                addAlert('THREAT', `${d.name_acronym} — UNDERCUT THREAT from ${(d.position ?? 0) > 1 ? `P${(d.position ?? 0) - 1}` : 'behind'}`);
                scheduleAutoDismiss();
            }
        });
    }, [sortedDrivers, addAlert]);
}
