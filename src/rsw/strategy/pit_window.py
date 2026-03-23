"""
Pit window optimization.

Finds the optimal lap range for pit stops based on:
- Tyre degradation projections
- Remaining race laps
- Competitor strategies
- Track-specific pit loss
"""

from dataclasses import dataclass

from rsw.config.constants import (
    CLIFF_AGES,
    CLIFF_WINDOW_MARGIN,
    CONFIDENCE_CLIFF_RISK_FACTOR,
    CRITICAL_CLIFF_THRESHOLD,
    DEG_ADVANTAGE_MULTIPLIER,
    FRESH_TYRE_BASE_ADVANTAGE,
    HIGH_CLIFF_EARLY_PIT_OFFSET,
    HIGH_CLIFF_RISK_THRESHOLD,
    MODERATE_CLIFF_EARLY_PIT_OFFSET,
    MODERATE_CLIFF_RISK_THRESHOLD,
    OVERCUT_DEG_NORMALIZER,
    OVERCUT_DEG_THRESHOLD,
    PIT_WINDOW_CONFIDENCE_WEIGHT,
    PIT_WINDOW_TIMING_WEIGHT,
    SC_PIT_CONFIDENCE,
    UNDERCUT_GAP_BUFFER,
    UNDERCUT_MIN_GAP,
)
from rsw.domain import TyreCompound


@dataclass
class PitWindow:
    """Optimal pit stop window."""

    min_lap: int  # Earliest recommended pit lap
    max_lap: int  # Latest recommended pit lap
    ideal_lap: int  # Optimal pit lap
    confidence: float  # 0-1 confidence score
    reason: str  # Explanation for window


@dataclass
class CompetitorThreat:
    """Threat assessment from a competitor."""

    driver_number: int
    gap: float  # Gap to this driver
    undercut_viable: bool
    overcut_viable: bool
    threat_level: float  # 0-1 scale


def find_optimal_window(
    current_lap: int,
    total_laps: int,
    deg_slope: float,
    current_pace: float,
    pit_loss: float,
    tyre_age: int,
    compound: str,
    cliff_risk: float,
    min_stint_laps: int = 10,
    cliff_age: int | None = None,
) -> PitWindow:
    """
    Find optimal pit stop window based on degradation model.

    Args:
        current_lap: Current race lap
        total_laps: Total race laps
        deg_slope: Degradation rate (s/lap)
        current_pace: Current lap time
        pit_loss: Pit stop time loss
        tyre_age: Current tyre age in laps
        compound: Current compound
        cliff_risk: Cliff risk score (0-1)
        min_stint_laps: Minimum laps for new stint

    Returns:
        PitWindow with recommended timing
    """
    remaining_laps = total_laps - current_lap

    # Early exit if too late to pit
    if remaining_laps <= min_stint_laps:
        return PitWindow(
            min_lap=0,
            max_lap=0,
            ideal_lap=0,
            confidence=1.0,
            reason="Too late to pit - stay out to finish",
        )

    # Compound-specific cliff age (in tyre laps, not race laps)
    # Use track-learned cliff age if provided, otherwise fall back to defaults
    # Validate compound via domain enum (accepts string, normalises to upper)
    try:
        validated = TyreCompound(compound.upper())
        compound_key = validated.value
    except ValueError:
        compound_key = compound.upper()

    if cliff_age is None:
        cliff_age = CLIFF_AGES.get(compound_key, CLIFF_AGES["MEDIUM"])

    # Convert cliff_age (tyre laps) to an absolute race lap number
    stint_start_lap = current_lap - tyre_age
    cliff_race_lap = stint_start_lap + cliff_age

    # Window: pit CLIFF_WINDOW_MARGIN laps before cliff up to CLIFF_WINDOW_MARGIN past cliff
    min_lap = max(current_lap + 1, cliff_race_lap - CLIFF_WINDOW_MARGIN)
    max_lap = min(total_laps - min_stint_laps, cliff_race_lap + CLIFF_WINDOW_MARGIN)
    max_lap = max(min_lap, max_lap)

    # Ideal: the cliff race lap, pulled earlier under high risk
    if cliff_risk > HIGH_CLIFF_RISK_THRESHOLD:
        ideal_lap = max(min_lap, cliff_race_lap - HIGH_CLIFF_EARLY_PIT_OFFSET)
        reason = f"High cliff risk — pit early (L{ideal_lap})"
    elif cliff_risk > MODERATE_CLIFF_RISK_THRESHOLD:
        ideal_lap = max(min_lap, cliff_race_lap - MODERATE_CLIFF_EARLY_PIT_OFFSET)
        reason = f"Moderate degradation — pit near cliff L{cliff_race_lap}"
    else:
        ideal_lap = cliff_race_lap
        reason = f"Target pit: L{cliff_race_lap} ({compound} cliff)"

    # Clamp to valid range
    ideal_lap = max(min_lap, min(max_lap, ideal_lap))

    # Confidence based on how close we are to cliff risk threshold
    confidence = 1.0 - min(CONFIDENCE_CLIFF_RISK_FACTOR, cliff_risk * CONFIDENCE_CLIFF_RISK_FACTOR)

    return PitWindow(
        min_lap=max(1, min_lap),
        max_lap=max(min_lap, max_lap),
        ideal_lap=ideal_lap,
        confidence=confidence,
        reason=reason,
    )


def detect_undercut_threat(
    gap_to_ahead: float | None,
    our_deg: float,
    their_deg: float,
    pit_loss: float,
    laps_remaining: int,
) -> tuple[bool, float]:
    """
    Detect if we can undercut the car ahead.

    Args:
        gap_to_ahead: Gap to car in front
        our_deg: Our degradation rate
        their_deg: Their degradation rate
        pit_loss: Pit loss time
        laps_remaining: Laps left in race

    Returns:
        Tuple of (is_undercut_viable, confidence)
    """
    if gap_to_ahead is None or gap_to_ahead <= 0:
        return False, 0.0

    # Undercut effectiveness window
    if gap_to_ahead > pit_loss + UNDERCUT_GAP_BUFFER:
        # Too far behind for undercut
        return False, 0.0

    if gap_to_ahead < UNDERCUT_MIN_GAP:
        # Already close enough - normal overtake may work
        return False, 0.5

    # Calculate required pace advantage on fresh tyres
    required_delta = pit_loss - gap_to_ahead
    expected_fresh_advantage = FRESH_TYRE_BASE_ADVANTAGE + (their_deg - our_deg) * DEG_ADVANTAGE_MULTIPLIER

    is_viable = expected_fresh_advantage > required_delta
    confidence = min(1.0, expected_fresh_advantage / max(0.1, required_delta))

    return is_viable, confidence


def detect_overcut_opportunity(
    gap_to_behind: float | None,
    our_deg: float,
    their_deg: float,
    pit_loss: float,
) -> tuple[bool, float]:
    """
    Detect if overcut strategy is beneficial.

    Overcut = staying out while they pit, then pitting later.
    Works when track evolution or better tyre management helps.

    Returns:
        Tuple of (is_overcut_viable, confidence)
    """
    if gap_to_behind is None or gap_to_behind >= pit_loss:
        # Safe gap - no need for overcut
        return False, 0.0

    # If we degrade slower, overcut is viable
    deg_advantage = their_deg - our_deg

    is_viable = deg_advantage > OVERCUT_DEG_THRESHOLD
    confidence = min(1.0, deg_advantage / OVERCUT_DEG_NORMALIZER)

    return is_viable, confidence


def rank_strategies(
    windows: list[PitWindow],
    pit_loss: float,
    remaining_laps: int,
) -> list[tuple[PitWindow, float]]:
    """
    Rank multiple pit windows by expected outcome.

    Args:
        windows: List of possible pit windows
        pit_loss: Pit stop time loss
        remaining_laps: Laps remaining

    Returns:
        Sorted list of (window, score) tuples, best first
    """
    scored = []

    for window in windows:
        # Score based on confidence and timing
        timing_score = 1.0 - abs(window.ideal_lap - (window.min_lap + window.max_lap) / 2) / max(
            1, window.max_lap - window.min_lap
        )
        score = window.confidence * PIT_WINDOW_CONFIDENCE_WEIGHT + timing_score * PIT_WINDOW_TIMING_WEIGHT
        scored.append((window, score))

    return sorted(scored, key=lambda x: -x[1])


def should_pit_now(
    current_lap: int,
    window: PitWindow,
    cliff_risk: float,
    undercut_threat: bool,
    safety_car: bool = False,
    gap_to_behind: float | None = None,
    pit_loss: float = 22.0,
) -> tuple[bool, float, str]:
    """
    Determine if driver should pit this lap.

    Returns:
        Tuple of (should_pit, confidence, reason)
    """
    # Always pit under safety car if in window
    if safety_car and window.min_lap <= current_lap <= window.max_lap:
        return True, SC_PIT_CONFIDENCE, "Safety car - free pit stop"

    # Critical cliff risk
    if cliff_risk > CRITICAL_CLIFF_THRESHOLD:
        return True, 0.9, "Critical cliff risk - pit immediately"

    # Undercut threat
    if undercut_threat and current_lap >= window.min_lap:
        return True, 0.8, "Undercut threat - cover by pitting"

    # Ideal lap
    if current_lap == window.ideal_lap:
        return True, window.confidence, "Ideal pit lap reached"

    # Past max window
    if current_lap > window.max_lap:
        return True, 0.7, "Past optimal window - pit now"

    # Default - stay out
    reason = f"Stay out - window opens lap {window.min_lap}"
    if current_lap >= window.min_lap:
        reason = f"In window - ideal lap {window.ideal_lap}"

    return False, 0.5, reason
