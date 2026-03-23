"""
Dirty Air Physics Model.

Simulates the aerodynamic disadvantage of following another car closely.
Loss of downforce reduces cornering speed and increases tyre wear (sliding).
"""

from rsw.config.constants import (
    DIRTY_AIR_EFFECT_EXPONENT,
    DIRTY_AIR_MAX_PENALTY_SECONDS,
    DIRTY_AIR_THRESHOLD_SECONDS,
)


class DirtyAirModel:
    def __init__(self):
        # Configuration for current regulations (e.g. 2026 regs might differ)
        self.dirty_air_threshold = DIRTY_AIR_THRESHOLD_SECONDS
        self.max_penalty_time = DIRTY_AIR_MAX_PENALTY_SECONDS

    def get_pace_penalty(self, gap_to_ahead: float | None) -> float:
        """
        Calculate time lost due to dirty air.

        Args:
            gap_to_ahead: Gap to car in front in seconds. None if leading or alone.

        Returns:
            Time penalty in seconds (positive = slower).
        """
        if gap_to_ahead is None or gap_to_ahead > self.dirty_air_threshold:
            return 0.0

        if gap_to_ahead <= 0:
            return 0.0  # Overtaken or glitch

        # Linear ramp up of penalty as gap closes
        # Gap 3.0s -> 0.0s penalty
        # Gap 0.5s -> Max penalty

        # Normalized proximity (0 = far/clean, 1 = bumper to bumper)
        proximity = 1.0 - (gap_to_ahead / self.dirty_air_threshold)

        # Non-linear effect: it gets much worse very close
        effect = proximity**DIRTY_AIR_EFFECT_EXPONENT

        return self.max_penalty_time * effect
