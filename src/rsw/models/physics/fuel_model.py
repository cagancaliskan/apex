"""
Fuel Load Physics Model.

Simulates lap time gain as fuel is burned.
"""


class FuelModel:
    STARTING_FUEL_KG = 110.0
    BURN_RATE_KG_PER_LAP = 1.7
    TIME_COST_PER_KG = 0.035  # seconds per kg

    def __init__(self, start_fuel: float = STARTING_FUEL_KG):
        self.starting_fuel = start_fuel

    def get_fuel_mass(self, current_lap: int) -> float:
        """Calculate current fuel mass."""
        consumed = current_lap * self.BURN_RATE_KG_PER_LAP
        return max(0.0, self.starting_fuel - consumed)

    def get_fuel_penalty(self, current_lap: int) -> float:
        """
        Calculate time penalty due to fuel load.
        Relative to empty tank (0kg).
        """
        mass = self.get_fuel_mass(current_lap)
        return mass * self.TIME_COST_PER_KG
