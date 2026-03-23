"""
Strategy Generator.

Generates all viable pit strategies for a race:
- 1-stop strategies
- 2-stop strategies
- 3-stop strategies (sprint races)

Design: KISS - Simple generation with validation, no complex optimization.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PitStrategy:
    """
    A complete pit strategy for a race.

    Defines when to pit and which compounds to use.
    """

    n_stops: int
    stop_laps: list[int]  # Laps to pit on
    compounds: list[str]  # Compound for each stint
    stint_lengths: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Calculate stint lengths if not provided."""
        if not self.stint_lengths and self.stop_laps:
            # Will be calculated by generate_strategies
            pass

    @property
    def name(self) -> str:
        """Human-readable strategy name."""
        if self.n_stops == 0:
            return f"No-Stop ({self.compounds[0]})"
        compound_str = "-".join(self.compounds)
        stop_str = "/".join(str(lap) for lap in self.stop_laps)
        return f"{self.n_stops}-Stop: {compound_str} (L{stop_str})"

    def is_valid(self, total_laps: int, min_stint: int = 8) -> bool:
        """Check if strategy is viable."""
        # All stints must be at least min_stint laps
        if any(s < min_stint for s in self.stint_lengths):
            return False

        # Last stop must leave room for final stint
        if self.stop_laps and (total_laps - self.stop_laps[-1]) < min_stint:
            return False

        return True


# Standard compound characteristics
COMPOUND_STINTS = {
    "SOFT": {"min": 8, "optimal": 12, "max": 18},
    "MEDIUM": {"min": 12, "optimal": 20, "max": 30},
    "HARD": {"min": 15, "optimal": 30, "max": 45},
}


def generate_one_stop_strategies(
    total_laps: int,
    start_compound: str = "SOFT",
    current_lap: int = 1,
    min_stint: int = 8,
) -> list[PitStrategy]:
    """
    Generate all viable 1-stop strategies.

    Args:
        total_laps: Race length
        start_compound: Starting compound
        current_lap: Current lap (for mid-race generation)
        min_stint: Minimum stint length

    Returns:
        List of viable 1-stop strategies
    """
    strategies: list[PitStrategy] = []
    remaining = total_laps - current_lap

    # Calculate pit window
    min_pit = current_lap + min_stint
    max_pit = total_laps - min_stint

    if min_pit >= max_pit:
        return strategies  # No viable window

    # Generate strategies with different compounds
    second_compounds = ["SOFT", "MEDIUM", "HARD"]
    if start_compound in second_compounds:
        # Must use at least 2 different compounds
        second_compounds = [c for c in second_compounds if c != start_compound]

    for second in second_compounds:
        # Calculate optimal pit lap based on compound choice
        first_max = COMPOUND_STINTS.get(start_compound, COMPOUND_STINTS["MEDIUM"])["max"]
        second_min = COMPOUND_STINTS.get(second, COMPOUND_STINTS["MEDIUM"])["min"]

        # Pit lap should be when first stint is expiring OR leaves good second stint
        ideal_pit = min(
            current_lap + first_max - 3,  # Before first compound degrades
            total_laps - second_min - 5,  # Leave room for second stint
        )
        ideal_pit = max(min_pit, min(max_pit, ideal_pit))

        # Generate 3 options: early, optimal, late
        for offset in [-3, 0, 3]:
            pit_lap = ideal_pit + offset
            if min_pit <= pit_lap <= max_pit:
                first_stint = pit_lap - current_lap
                second_stint = total_laps - pit_lap

                strategy = PitStrategy(
                    n_stops=1,
                    stop_laps=[pit_lap],
                    compounds=[start_compound, second],
                    stint_lengths=[first_stint, second_stint],
                )

                if strategy.is_valid(total_laps, min_stint):
                    strategies.append(strategy)

    return strategies


def generate_two_stop_strategies(
    total_laps: int,
    start_compound: str = "SOFT",
    current_lap: int = 1,
    min_stint: int = 8,
) -> list[PitStrategy]:
    """
    Generate viable 2-stop strategies.

    Args:
        total_laps: Race length
        start_compound: Starting compound
        current_lap: Current lap
        min_stint: Minimum stint length

    Returns:
        List of viable 2-stop strategies
    """
    strategies: list[Any] = []
    remaining = total_laps - current_lap

    # Need at least 3 stints of min_stint laps
    if remaining < min_stint * 3:
        return strategies

    # Common 2-stop patterns
    patterns = [
        ["SOFT", "MEDIUM", "SOFT"],  # Aggressive
        ["SOFT", "HARD", "MEDIUM"],  # Conservative first
        ["MEDIUM", "SOFT", "HARD"],  # Medium start
        ["MEDIUM", "HARD", "SOFT"],  # Conservative, fast finish
    ]

    # Filter patterns that start with our compound
    valid_patterns = [p for p in patterns if p[0] == start_compound]
    if not valid_patterns:
        # Use any pattern that has 2+ different compounds
        valid_patterns = patterns

    for compound_pattern in valid_patterns:
        # Calculate stint lengths based on compound limits
        stint1_optimal = COMPOUND_STINTS.get(compound_pattern[0], COMPOUND_STINTS["MEDIUM"])["optimal"]
        stint2_optimal = COMPOUND_STINTS.get(compound_pattern[1], COMPOUND_STINTS["MEDIUM"])["optimal"]
        stint3_remaining = remaining - stint1_optimal - stint2_optimal

        if stint3_remaining < min_stint:
            # Adjust stint lengths
            stint1_optimal = remaining // 3
            stint2_optimal = remaining // 3
            stint3_remaining = remaining - stint1_optimal - stint2_optimal

        if stint3_remaining < min_stint:
            continue

        pit1 = current_lap + stint1_optimal
        pit2 = pit1 + stint2_optimal

        if pit2 >= total_laps - min_stint:
            continue

        strategy = PitStrategy(
            n_stops=2,
            stop_laps=[pit1, pit2],
            compounds=compound_pattern,
            stint_lengths=[stint1_optimal, stint2_optimal, stint3_remaining],
        )

        if strategy.is_valid(total_laps, min_stint):
            strategies.append(strategy)

    return strategies


def generate_all_strategies(
    total_laps: int,
    current_lap: int = 1,
    start_compound: str = "SOFT",
    compounds_used: list[str] | None = None,
    include_two_stop: bool = True,
    min_stint: int = 8,
) -> list[PitStrategy]:
    """
    Generate all viable pit strategies for current race situation.

    Args:
        total_laps: Total race laps
        current_lap: Current lap number
        start_compound: Current/starting compound
        compounds_used: Already used compounds this race
        include_two_stop: Whether to include 2-stop strategies
        min_stint: Minimum stint length

    Returns:
        List of all viable strategies, sorted by n_stops
    """
    strategies = []

    # 1-stop strategies
    one_stop = generate_one_stop_strategies(
        total_laps, start_compound, current_lap, min_stint
    )
    strategies.extend(one_stop)

    # 2-stop strategies (if race is long enough)
    if include_two_stop:
        two_stop = generate_two_stop_strategies(
            total_laps, start_compound, current_lap, min_stint
        )
        strategies.extend(two_stop)

    # Remove duplicates (same pit laps)
    seen = set()
    unique = []
    for s in strategies:
        key = (tuple(s.stop_laps), tuple(s.compounds))
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return sorted(unique, key=lambda s: (s.n_stops, s.stop_laps[0] if s.stop_laps else 0))
