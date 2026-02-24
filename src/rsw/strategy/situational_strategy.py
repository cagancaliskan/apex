"""
Situational Strategy Adjustments.

Modifies strategy recommendations based on race context:
- Championship situation
- Team position battles
- Track-specific factors

Design: Single responsibility - only context adjustments, delegates to other modules.
"""

from dataclasses import dataclass
from enum import Enum


class ChampionshipPhase(Enum):
    """Current phase of the championship."""

    EARLY = "early"  # First 1/3 of season
    MIDDLE = "middle"  # Middle 1/3
    LATE = "late"  # Final 1/3
    DECISIVE = "decisive"  # Last 2-3 races, title on the line


@dataclass
class ChampionshipContext:
    """
    Championship situation affecting strategy decisions.

    Teams/drivers fighting for the title behave differently than
    those with nothing to lose.
    """

    driver_number: int
    championship_position: int  # 1 = leader
    points_gap_to_leader: int  # 0 if leader, positive if behind
    points_gap_to_behind: int  # Gap to next position behind
    races_remaining: int
    phase: ChampionshipPhase

    @property
    def is_title_contender(self) -> bool:
        """Driver is realistically fighting for championship."""
        max_points_available = self.races_remaining * 26  # Win + fastest lap
        return self.points_gap_to_leader <= max_points_available

    @property
    def needs_win(self) -> bool:
        """Driver needs race wins to have championship chance."""
        if self.championship_position == 1:
            return False
        # At decisive phase, check if points gap requires wins
        if self.phase == ChampionshipPhase.DECISIVE:
            return self.points_gap_to_leader > self.races_remaining * 15
        return False

    @property
    def can_cruise(self) -> bool:
        """Title leader with comfortable gap."""
        if self.championship_position != 1:
            return False
        return self.points_gap_to_behind > self.races_remaining * 10


@dataclass
class RaceContext:
    """
    Current race situation affecting decisions.

    Combines championship and immediate race factors.
    """

    current_lap: int
    total_laps: int
    driver_position: int
    gap_to_ahead: float | None
    gap_to_behind: float | None
    safety_car_active: bool
    is_wet: bool

    # Team situation
    teammate_position: int | None = None
    fighting_for_wcc_points: bool = False  # World Constructors

    @property
    def race_phase(self) -> str:
        """Current phase of the race."""
        progress = self.current_lap / self.total_laps
        if progress < 0.25:
            return "opening"
        elif progress < 0.5:
            return "middle"
        elif progress < 0.75:
            return "closing"
        else:
            return "final"

    @property
    def laps_remaining(self) -> int:
        return self.total_laps - self.current_lap


def calculate_risk_modifier(
    championship: ChampionshipContext | None, race: RaceContext
) -> float:
    """
    Calculate risk modifier for strategy decisions.

    Returns:
        Risk modifier where:
        - < 1.0 = more conservative (protect position)
        - 1.0 = neutral
        - > 1.0 = more aggressive (take risks for gains)
    """
    modifier = 1.0

    # Championship context
    if championship:
        if championship.can_cruise:
            modifier *= 0.7  # Very conservative
        elif championship.needs_win:
            modifier *= 1.4  # Very aggressive
        elif championship.is_title_contender and championship.championship_position > 1:
            # Title chaser who can still win - be aggressive
            if championship.phase == ChampionshipPhase.DECISIVE:
                modifier *= 1.25  # Aggressive in decisive phase
            else:
                modifier *= 1.1  # Slightly aggressive
        elif championship.is_title_contender and championship.phase == ChampionshipPhase.DECISIVE:
            modifier *= 0.85  # Leader in decisive - slightly conservative

    # Race position context
    if race.driver_position == 1:
        modifier *= 0.9  # Leaders protect
    elif race.driver_position >= 15:
        modifier *= 1.2  # Back of grid takes risks

    # Race phase
    if race.race_phase == "final" and race.driver_position <= 3:
        modifier *= 0.8  # Protect podium late in race

    # Safety car is opportunity
    if race.safety_car_active:
        modifier *= 1.1

    return round(modifier, 2)


def adjust_pit_window(
    min_lap: int,
    max_lap: int,
    ideal_lap: int,
    risk_modifier: float,
) -> tuple[int, int, int]:
    """
    Adjust pit window based on risk modifier.

    Conservative (low risk) = pit earlier in window
    Aggressive (high risk) = pit later, extend stint

    Returns:
        Tuple of (adjusted_min, adjusted_max, adjusted_ideal)
    """
    window_size = max_lap - min_lap

    if risk_modifier < 1.0:
        # Conservative - shift window earlier
        shift = int((1.0 - risk_modifier) * window_size * 0.3)
        return (min_lap, max_lap - shift, min(ideal_lap, max_lap - shift))
    elif risk_modifier > 1.0:
        # Aggressive - shift window later
        shift = int((risk_modifier - 1.0) * window_size * 0.3)
        return (min_lap + shift, max_lap, max(ideal_lap, min_lap + shift))

    return (min_lap, max_lap, ideal_lap)


def should_cover_position(
    race: RaceContext,
    championship: ChampionshipContext | None,
    car_ahead_pitting: bool,
    car_behind_pitting: bool,
) -> tuple[bool, str]:
    """
    Determine if we should react to competitor pit stops.

    Returns:
        Tuple of (should_react, reason)
    """
    # Always cover direct rivals in championship
    if championship and championship.phase == ChampionshipPhase.DECISIVE:
        if car_ahead_pitting and race.gap_to_ahead and race.gap_to_ahead < 5.0:
            return True, "Cover championship rival"

    # Don't react if position is secure
    if race.gap_to_behind and race.gap_to_behind > 25.0:
        return False, "Gap is secure, no need to react"

    # Cover undercut threat
    if car_behind_pitting and race.gap_to_behind and race.gap_to_behind < 3.0:
        return True, "Cover undercut threat"

    # React to car ahead in closing stages
    if race.race_phase in ("closing", "final") and car_ahead_pitting:
        if race.gap_to_ahead and race.gap_to_ahead < 10.0:
            return True, "Track car ahead in closing stages"

    return False, "No reaction needed"


def get_compound_preference(
    race: RaceContext,
    risk_modifier: float,
    used_compounds: list[str],
) -> str:
    """
    Recommend tyre compound based on context.

    Must use at least 2 different compounds per race.
    """
    laps_remaining = race.laps_remaining

    # Final stint compound selection
    if laps_remaining <= 15:
        # Short stint - prefer SOFT if not used
        if "SOFT" not in used_compounds:
            return "SOFT"
        return "MEDIUM"

    if laps_remaining <= 30:
        # Medium stint
        if risk_modifier > 1.1:
            return "SOFT" if "SOFT" not in used_compounds else "MEDIUM"
        return "MEDIUM"

    # Long stint remaining
    if risk_modifier < 0.9:
        return "HARD"

    return "MEDIUM"
