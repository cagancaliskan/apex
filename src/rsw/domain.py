"""
Value Objects and Domain Models.

Immutable objects that represent domain concepts.
Follows: Information Hiding, Encapsulation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ============================================================================
# Enums (Named Constants - KISS)
# ============================================================================

class TyreCompound(str, Enum):
    """Tyre compound types."""
    SOFT = "SOFT"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    INTERMEDIATE = "INTERMEDIATE"
    WET = "WET"
    
    @property
    def degradation_factor(self) -> float:
        """Base degradation factor for compound."""
        factors = {
            "SOFT": 1.2,
            "MEDIUM": 1.0,
            "HARD": 0.8,
            "INTERMEDIATE": 1.1,
            "WET": 1.0,
        }
        return factors.get(self.value, 1.0)


class SessionType(str, Enum):
    """F1 session types."""
    PRACTICE_1 = "Practice 1"
    PRACTICE_2 = "Practice 2"
    PRACTICE_3 = "Practice 3"
    QUALIFYING = "Qualifying"
    SPRINT = "Sprint"
    RACE = "Race"


class FlagStatus(str, Enum):
    """Track flag status."""
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    CHEQUERED = "CHEQUERED"


class RecommendationType(str, Enum):
    """Pit strategy recommendation types."""
    PIT_NOW = "PIT_NOW"
    CONSIDER_PIT = "CONSIDER_PIT"
    STAY_OUT = "STAY_OUT"
    EXTEND_STINT = "EXTEND_STINT"
    BOX_BOX = "BOX_BOX"  # Immediate pit call


# ============================================================================
# Value Objects (Immutable - Encapsulation)
# ============================================================================

@dataclass(frozen=True)
class LapTime:
    """
    Immutable lap time value object.
    
    Encapsulates lap time representation logic.
    """
    seconds: float
    
    def __post_init__(self) -> None:
        if self.seconds < 0:
            raise ValueError("Lap time cannot be negative")
    
    @property
    def minutes(self) -> int:
        return int(self.seconds // 60)
    
    @property
    def remainder(self) -> float:
        return self.seconds % 60
    
    def __str__(self) -> str:
        return f"{self.minutes}:{self.remainder:06.3f}"
    
    def delta(self, other: "LapTime") -> float:
        """Get time difference in seconds."""
        return self.seconds - other.seconds


@dataclass(frozen=True)
class Gap:
    """
    Immutable gap value object.
    
    Represents gap between drivers in seconds or laps.
    """
    seconds: float
    
    @property
    def is_lapped(self) -> bool:
        return self.seconds >= 60.0  # Approximate lap time
    
    @property
    def laps_behind(self) -> int:
        return int(self.seconds // 60) if self.is_lapped else 0
    
    def __str__(self) -> str:
        if self.seconds == 0:
            return "LEADER"
        if self.is_lapped:
            laps = self.laps_behind
            return f"+{laps} LAP{'S' if laps > 1 else ''}"
        return f"+{self.seconds:.3f}"


@dataclass(frozen=True)
class PitWindow:
    """
    Immutable pit window value object.
    
    Encapsulates pit window calculation results.
    """
    min_lap: int
    max_lap: int
    ideal_lap: int
    reason: str = ""
    
    def __post_init__(self) -> None:
        if self.min_lap > self.ideal_lap or self.ideal_lap > self.max_lap:
            raise ValueError("Invalid pit window: min <= ideal <= max required")
    
    def contains(self, lap: int) -> bool:
        """Check if lap is within window."""
        return self.min_lap <= lap <= self.max_lap
    
    @property
    def width(self) -> int:
        """Window width in laps."""
        return self.max_lap - self.min_lap


@dataclass(frozen=True)
class Coordinates:
    """
    Immutable track coordinates.
    
    Value object for X, Y positions.
    """
    x: float
    y: float
    
    def distance_to(self, other: "Coordinates") -> float:
        """Calculate distance to another point."""
        import math
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


# ============================================================================
# Result Objects (Encapsulation - Hide calculation details)
# ============================================================================

@dataclass(frozen=True)
class StrategyRecommendation:
    """
    Strategy recommendation result.
    
    Immutable result of strategy calculation.
    """
    recommendation: RecommendationType
    confidence: float
    reason: str
    pit_window: PitWindow | None = None
    undercut_threat: bool = False
    overcut_opportunity: bool = False
    
    @property
    def is_pit_call(self) -> bool:
        """Check if recommendation is to pit."""
        return self.recommendation in (
            RecommendationType.PIT_NOW,
            RecommendationType.BOX_BOX,
        )


@dataclass(frozen=True)
class MonteCarloResult:
    """
    Monte Carlo simulation result.
    
    Immutable simulation outcome.
    """
    expected_position: float
    position_std: float
    prob_win: float
    prob_podium: float
    prob_points: float
    simulations: int = 500
    
    @property
    def position_range(self) -> tuple[float, float]:
        """68% confidence interval for position."""
        return (
            self.expected_position - self.position_std,
            self.expected_position + self.position_std,
        )
