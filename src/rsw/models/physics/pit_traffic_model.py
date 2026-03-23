"""
Pit Traffic Model.

Estimates the "cost" of rejoining the track in a specific location
relative to other cars (traffic density).
"""

from typing import Any

from rsw.config.constants import (
    DEFAULT_PIT_LOSS_SECONDS,
    PIT_TRAFFIC_MAX_CAR_THRESHOLD,
    PIT_TRAFFIC_WINDOW_SECONDS,
)


class PitTrafficModel:
    """Estimates traffic severity when rejoining after a pit stop."""

    def __init__(self, pit_loss: float = DEFAULT_PIT_LOSS_SECONDS, traffic_window: float = PIT_TRAFFIC_WINDOW_SECONDS) -> None:
        self._pit_loss = pit_loss
        self._traffic_window = traffic_window

    def check_rejoin_traffic(
        self,
        exit_lap_time_prediction: float,
        current_lap: int,
        race_state_drivers: dict[int, Any],
    ) -> float:
        """
        Estimate traffic severity at predicted rejoin time.

        Uses current gaps to approximate where the pitting driver
        will rejoin relative to the field.

        Args:
            exit_lap_time_prediction: Predicted gap to leader at pit exit (seconds).
            current_lap: Current race lap.
            race_state_drivers: Dict of driver_number -> DriverState with gap_to_leader.

        Returns:
            Traffic severity score (0.0 = clean air, 1.0 = stuck in DRS train).
        """
        rejoin_gap = exit_lap_time_prediction + self._pit_loss

        nearby_count = 0
        for driver in race_state_drivers.values():
            gap = getattr(driver, "gap_to_leader", None)
            if gap is None:
                continue
            if getattr(driver, "in_pit", False):
                continue
            if getattr(driver, "retired", False):
                continue
            if abs(gap - rejoin_gap) < self._traffic_window:
                nearby_count += 1

        # PIT_TRAFFIC_MAX_CAR_THRESHOLD+ cars in the window = maximum traffic
        return min(nearby_count / PIT_TRAFFIC_MAX_CAR_THRESHOLD, 1.0)
