"""
Tyre Degradation Physics Model.

Implements a 3-phase degradation curve:
1. Warmup (Performance gain)
2. Stable (Linear/Slight exp degradation)
3. Cliff (Exponential loss)
"""

import math
from dataclasses import dataclass


@dataclass
class TyreParams:
    base_grip: float  # Base grip level (lower lap time is better, but here grip -> +speed)
    deg_rate: float  # Linear degradation (s/lap)
    warmup_laps: int  # Laps to reach peak temperature
    cliff_lap: int  # Lap where cliff starts
    cliff_severity: float  # Exponential factor for cliff


# Compound characteristics (relative to base)
COMPOUND_PARAMS = {
    "SOFT": TyreParams(
        base_grip=1.2, deg_rate=0.08, warmup_laps=1, cliff_lap=15, cliff_severity=0.2
    ),
    "MEDIUM": TyreParams(
        base_grip=0.6, deg_rate=0.05, warmup_laps=2, cliff_lap=25, cliff_severity=0.15
    ),
    "HARD": TyreParams(
        base_grip=0.0, deg_rate=0.03, warmup_laps=3, cliff_lap=40, cliff_severity=0.1
    ),
    "INTERMEDIATE": TyreParams(
        base_grip=-2.0, deg_rate=0.05, warmup_laps=1, cliff_lap=30, cliff_severity=0.1
    ),
    "WET": TyreParams(
        base_grip=-5.0, deg_rate=0.05, warmup_laps=1, cliff_lap=30, cliff_severity=0.1
    ),
}


class TyreModel:
    def __init__(self, compound: str = "MEDIUM"):
        self.compound = compound
        self.params = COMPOUND_PARAMS.get(compound, COMPOUND_PARAMS["MEDIUM"])

    def get_tyre_penalty(self, lap_age: int) -> float:
        """
        Calculate time penalty (s) due to tyre wear for a given age.
        Positive value = Slower lap time.
        """
        # Phase 1: Warmup (Negative penalty = faster)
        if lap_age < self.params.warmup_laps:
            # Simple linear ramp up to peak
            return 0.5 * (self.params.warmup_laps - lap_age)

        # Phase 2: Stable Degradation
        stable_laps = lap_age - self.params.warmup_laps
        linear_loss = stable_laps * self.params.deg_rate

        # Phase 3: Cliff
        cliff_penalty = 0.0
        if lap_age > self.params.cliff_lap:
            cliff_laps = lap_age - self.params.cliff_lap
            # Exponential growth: e^(severity * laps) - 1
            cliff_penalty = 0.1 * (math.exp(self.params.cliff_severity * cliff_laps) - 1)

        # Base offset (Softs are faster than Hards)
        # We model this as a penalty relative to Softs.
        # But here, let's keep it simple: Return the DEGRADATION delta only.

        return linear_loss + cliff_penalty

    def get_compound_pace_delta(self) -> float:
        """Return base pace difference relative to theoretical baseline (Softs)."""
        # Softs = 1.2 grip, Hards = 0.0 grip.
        # Difference ~ 1.2s
        soft_base = COMPOUND_PARAMS["SOFT"].base_grip
        my_base = self.params.base_grip
        return soft_base - my_base  # e.g. 1.2 - 0.0 = 1.2s slower
