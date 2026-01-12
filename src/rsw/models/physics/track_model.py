"""
Track Evolution Physics Model.

Simulates track rubbering in (grip improvement) over the race distance.
"""


class TrackModel:
    def __init__(self, evolution_factor: float = 0.015, max_evolution: float = 2.0):
        """
        args:
            evolution_factor: Time gain (s) per lap driven (grid wide average)
            max_evolution: Maximum total track improvement (s)
        """
        self.evolution_factor = evolution_factor
        self.max_evolution = max_evolution

    def get_track_improvement(self, total_grid_laps: int) -> float:
        """
        Calculate lap time GAIN (negative delta) from track evolution.
        Based on total laps driven by all cars (proxy for rubber deposition).
        """
        # Simplify: assume standard race progression
        # Linear improvement up to a cap
        improvement = total_grid_laps * 0.001  # Small gain per total lap
        return min(self.max_evolution, improvement)

    def get_lap_evolution(self, race_lap: int) -> float:
        """
        Simple lap-based evolution model.
        Returns time GAIN (s).
        """
        # Track gets ~0.03s faster per lap of the race leader
        return min(self.max_evolution, race_lap * 0.03)
