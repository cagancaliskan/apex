"""
Strategy decision engine.

Evaluates current race state and generates pit stop recommendations
with confidence scores and reasoning.
"""

from dataclasses import dataclass
from enum import Enum

from .pit_window import PitWindow, find_optimal_window, should_pit_now


class RecommendationType(Enum):
    """Types of strategy recommendations."""

    PIT_NOW = "PIT_NOW"
    STAY_OUT = "STAY_OUT"
    CONSIDER_PIT = "CONSIDER_PIT"
    EXTEND_STINT = "EXTEND_STINT"


@dataclass
class PitDecision:
    """A specific pit stop decision."""

    lap: int
    compound_to: str  # Compound to switch to
    expected_positions_lost: int
    expected_time_gain: float
    confidence: float


@dataclass
class StrategyRecommendation:
    """Complete strategy recommendation."""

    driver_number: int
    recommendation: RecommendationType
    confidence: float  # 0-1
    reason: str

    # Window info
    pit_window: PitWindow | None = None

    # Pit decision if pit is recommended
    pit_decision: PitDecision | None = None

    # Threat assessment
    undercut_threat: bool = False
    overcut_opportunity: bool = False

    # Alternative strategies
    alternatives: list[str] | None = None


def evaluate_strategy(
    driver_number: int,
    current_lap: int,
    total_laps: int,
    current_position: int,
    deg_slope: float,
    cliff_risk: float,
    current_pace: float,
    tyre_age: int,
    compound: str,
    pit_loss: float,
    gap_to_ahead: float | None = None,
    gap_to_behind: float | None = None,
    ahead_deg: float = 0.05,
    behind_deg: float = 0.05,
    safety_car: bool = False,
) -> StrategyRecommendation:
    """
    Evaluate strategy and generate recommendation.

    Args:
        driver_number: Driver being evaluated
        current_lap: Current race lap
        total_laps: Total race laps
        current_position: Current position
        deg_slope: Current degradation rate
        cliff_risk: Cliff risk score
        current_pace: Current lap time
        tyre_age: Current tyre age
        compound: Current compound
        pit_loss: Pit stop time loss
        gap_to_ahead: Gap to car in front
        gap_to_behind: Gap to car behind
        ahead_deg: Car ahead's degradation
        behind_deg: Car behind's degradation
        safety_car: Is safety car out

    Returns:
        StrategyRecommendation
    """
    remaining_laps = total_laps - current_lap

    # Find optimal pit window
    window = find_optimal_window(
        current_lap=current_lap,
        total_laps=total_laps,
        deg_slope=deg_slope,
        current_pace=current_pace,
        pit_loss=pit_loss,
        tyre_age=tyre_age,
        compound=compound,
        cliff_risk=cliff_risk,
    )

    # Check if we should pit now
    should_pit, pit_confidence, pit_reason = should_pit_now(
        current_lap=current_lap,
        window=window,
        cliff_risk=cliff_risk,
        undercut_threat=False,  # Will update below
        safety_car=safety_car,
        gap_to_behind=gap_to_behind,
        pit_loss=pit_loss,
    )

    # Assess threats
    undercut_threat = False
    overcut_opportunity = False

    if gap_to_ahead and gap_to_ahead < pit_loss + 3.0:
        if ahead_deg > deg_slope + 0.02:
            undercut_threat = True

    if gap_to_behind and gap_to_behind < pit_loss:
        if deg_slope < behind_deg - 0.02:
            overcut_opportunity = True

    # Re-evaluate with threat info
    if undercut_threat and not should_pit:
        should_pit, pit_confidence, pit_reason = should_pit_now(
            current_lap=current_lap,
            window=window,
            cliff_risk=cliff_risk,
            undercut_threat=True,
            safety_car=safety_car,
            gap_to_behind=gap_to_behind,
            pit_loss=pit_loss,
        )

    # Determine recommendation type
    if safety_car and window.min_lap <= current_lap <= window.max_lap:
        rec_type = RecommendationType.PIT_NOW
        confidence = 0.95
        reason = "Safety car - free pit stop opportunity"
    elif should_pit:
        if pit_confidence > 0.7:
            rec_type = RecommendationType.PIT_NOW
        else:
            rec_type = RecommendationType.CONSIDER_PIT
        confidence = pit_confidence
        reason = pit_reason
    elif remaining_laps <= 10 and tyre_age < 15:
        rec_type = RecommendationType.EXTEND_STINT
        confidence = 0.8
        reason = f"Only {remaining_laps} laps left - no pit needed"
    else:
        rec_type = RecommendationType.STAY_OUT
        confidence = 1.0 - cliff_risk * 0.5
        reason = window.reason

    # Build pit decision if pitting
    pit_decision = None
    if rec_type in (RecommendationType.PIT_NOW, RecommendationType.CONSIDER_PIT):
        # Recommend compound based on remaining laps
        if remaining_laps > 30:
            new_compound = "MEDIUM" if compound == "SOFT" else "HARD"
        elif remaining_laps > 15:
            new_compound = "MEDIUM"
        else:
            new_compound = "SOFT"

        pit_decision = PitDecision(
            lap=current_lap,
            compound_to=new_compound,
            expected_positions_lost=1 if gap_to_behind and gap_to_behind < pit_loss else 0,
            expected_time_gain=deg_slope * 10,  # Rough estimate
            confidence=confidence,
        )

    # Build alternatives
    alternatives = []
    if rec_type == RecommendationType.STAY_OUT:
        alternatives.append(f"Pit on lap {window.ideal_lap} for optimal timing")
    elif rec_type == RecommendationType.PIT_NOW:
        alternatives.append(f"Extend stint to lap {window.max_lap} if needed")

    return StrategyRecommendation(
        driver_number=driver_number,
        recommendation=rec_type,
        confidence=confidence,
        reason=reason,
        pit_window=window,
        pit_decision=pit_decision,
        undercut_threat=undercut_threat,
        overcut_opportunity=overcut_opportunity,
        alternatives=alternatives,
    )


def get_quick_recommendation(
    cliff_risk: float,
    tyre_age: int,
    remaining_laps: int,
    in_window: bool,
) -> tuple[str, str]:
    """
    Get a quick recommendation for display.

    Returns:
        Tuple of (recommendation, color)
    """
    if cliff_risk > 0.8:
        return "PIT NOW", "red"

    if remaining_laps <= 8:
        return "STAY OUT", "green"

    if in_window:
        if cliff_risk > 0.5:
            return "CONSIDER PIT", "yellow"
        return "IN WINDOW", "cyan"

    return "STAY OUT", "green"
