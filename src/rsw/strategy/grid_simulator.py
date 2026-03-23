"""
Grid-Wide Physics Simulator.

Simulates the entire race state forward in time, accounting for:
- Physics (Fuel, Tyres, Track)
- Traffic (Dirty Air, Overtaking difficulty)
- Strategy (Competitor AI)
"""

import copy
import random
from typing import Any

from rsw.config.constants import (
    DEFAULT_BASE_PACE_SECONDS,
    DEFAULT_SC_BASE_PROBABILITY,
    GRID_SIM_DEFAULT_CLIFF_LAP,
    GRID_SIM_GAP_MAX,
    GRID_SIM_GAP_MIN,
    GRID_SIM_NORMAL_PIT_LOSS,
    GRID_SIM_SC_PIT_LOSS,
)
from rsw.models.physics.fuel_model import FuelModel
from rsw.models.physics.track_model import TrackModel
from rsw.models.physics.traffic_model import DirtyAirModel

# Import our physics & AI models
from rsw.models.physics.tyre_model import TyreModel
from rsw.strategy.competitor_ai import CompetitorAI


class GridSimulator:
    def __init__(self) -> None:
        self.tyre_model_factory = TyreModel
        self.fuel_model = FuelModel()
        self.track_model = TrackModel()
        self.dirty_air_model = DirtyAirModel()
        self.ai = CompetitorAI()

    def run_simulation(
        self,
        initial_state: dict[int, Any],  # Dict of DriverState
        remaining_laps: int,
        sc_probability: float = DEFAULT_SC_BASE_PROBABILITY,
    ) -> dict[int, int]:
        """
        Run a full grid simulation to the end of the race.
        Returns final positions {driver_number: position}.
        """
        # Deep copy state so we don't mutate the live race
        # In a real app we'd use a lightweight simulation state object
        sim_drivers = copy.deepcopy(initial_state)

        # Sort by position
        sorted_drivers = sorted(
            sim_drivers.values(), key=lambda d: d.position if d.position else 99
        )

        # Track cumulative time per driver in a separate dict (DriverState is a
        # Pydantic model and doesn't allow arbitrary attribute assignment).
        sim_times: dict[int, float] = {d.driver_number: 0.0 for d in sorted_drivers}

        # Simulation Loop
        for lap_offset in range(remaining_laps):
            current_race_lap = sorted_drivers[0].current_lap + lap_offset

            # 1. Check for Safety Car (Random event)
            is_sc = random.random() < (
                sc_probability / remaining_laps
            )  # Rough probability distribution

            # 2. Process each driver
            # We process in track order to handle traffic correctly

            for i, driver in enumerate(sorted_drivers):
                # --- A. Strategy Decision ---
                decision = self.ai.decide_strategy(
                    driver_number=driver.driver_number,
                    current_lap=current_race_lap,
                    tyre_age=driver.tyre_age + lap_offset,  # Estimate age
                    compound=driver.compound or "MEDIUM",
                    position=i + 1,
                    gap_to_behind=None,  # Simplified for now
                    tyre_cliff_lap=GRID_SIM_DEFAULT_CLIFF_LAP,
                    is_safety_car=is_sc,
                )

                # --- B. Physics Calculation ---
                # 1. Base Physics
                tyre_instance = self.tyre_model_factory(driver.compound or "MEDIUM")
                tyre_pen = tyre_instance.get_tyre_penalty(driver.tyre_age + lap_offset)
                fuel_pen = self.fuel_model.get_fuel_penalty(current_race_lap)
                track_gain = self.track_model.get_lap_evolution(current_race_lap)

                # 2. Traffic (Dirty Air)
                gap_to_ahead = None
                if i > 0:
                    gap_to_ahead = random.uniform(GRID_SIM_GAP_MIN, GRID_SIM_GAP_MAX)

                traffic_pen = self.dirty_air_model.get_pace_penalty(gap_to_ahead)

                predicted_pace = (getattr(driver, 'last_lap_time', None) or DEFAULT_BASE_PACE_SECONDS) + fuel_pen + tyre_pen - track_gain + traffic_pen

                # --- C. Pit Stops ---
                pit_loss = 0.0
                if decision.should_pit:
                    pit_loss = GRID_SIM_NORMAL_PIT_LOSS
                    if is_sc:
                        pit_loss = GRID_SIM_SC_PIT_LOSS
                    driver.tyre_age = 0  # Reset age (in sim state)
                    driver.compound = decision.compound

                # Update driver cumulative time
                sim_times[driver.driver_number] += predicted_pace + pit_loss

            # 3. Re-Sort Grid (Overtaking)
            sorted_drivers.sort(key=lambda d: sim_times[d.driver_number])

        # Return final positions
        return {d.driver_number: idx + 1 for idx, d in enumerate(sorted_drivers)}
