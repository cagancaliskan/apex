"""
Pit window optimization.

Finds the optimal lap range for pit stops based on:
- Tyre degradation projections
- Remaining race laps
- Competitor strategies
- Track-specific pit loss
"""

from dataclasses import dataclass


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

    # Calculate crossover point
    # Where staying out loses more than pit loss
    laps_until_crossover = int(pit_loss / max(deg_slope, 0.01))

    # Window boundaries
    min_lap = current_lap + max(1, min_stint_laps - tyre_age)
    max_lap = current_lap + min(remaining_laps - min_stint_laps, laps_until_crossover + 5)

    # Adjust for cliff risk
    if cliff_risk > 0.7:
        # High cliff risk - pit sooner
        ideal_lap = current_lap + max(1, int((max_lap - min_lap) * 0.3))
        reason = "High cliff risk - pit early recommended"
    elif cliff_risk > 0.4:
        # Moderate risk - pit in middle of window
        ideal_lap = current_lap + (max_lap - min_lap) // 2
        reason = "Moderate degradation - flexible window"
    else:
        # Low risk - can extend stint
        ideal_lap = max_lap
        reason = "Low degradation - extend stint if possible"

    # Clamp to valid range
    ideal_lap = max(min_lap, min(max_lap, ideal_lap))

    # Confidence based on deg slope uncertainty
    confidence = 1.0 - min(0.5, cliff_risk * 0.5)

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
    if gap_to_ahead > pit_loss + 3.0:
        # Too far behind for undercut
        return False, 0.0

    if gap_to_ahead < 1.0:
        # Already close enough - normal overtake may work
        return False, 0.5

    # Calculate required pace advantage on fresh tyres
    required_delta = pit_loss - gap_to_ahead
    expected_fresh_advantage = 1.5 + (their_deg - our_deg) * 3

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

    is_viable = deg_advantage > 0.02  # We degrade 20ms/lap slower
    confidence = min(1.0, deg_advantage / 0.05)

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
        score = window.confidence * 0.6 + timing_score * 0.4
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
        return True, 0.95, "Safety car - free pit stop"

    # Critical cliff risk
    if cliff_risk > 0.85:
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
