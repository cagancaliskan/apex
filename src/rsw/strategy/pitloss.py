"""
Pit stop time loss calculations.

Calculates the time cost of making a pit stop, including:
- Pit lane delta (speed limit vs racing speed)
- Stationary time (tyre change)
- Position loss estimation
"""

from dataclasses import dataclass


@dataclass
class PitLossEstimate:
    """Complete pit loss breakdown."""
    pit_lane_delta: float  # Time lost driving through pit lane
    stationary_time: float  # Time for tyre change
    total_loss: float  # Total time lost
    positions_at_risk: int  # Estimated positions we could lose
    undercut_threshold: float  # Lap time delta needed for undercut


def calculate_pit_loss(
    pit_loss_seconds: float,
    pit_loss_sigma: float = 0.5,
) -> float:
    """
    Calculate expected pit stop time loss.
    
    Args:
        pit_loss_seconds: Track-specific pit loss (from config)
        pit_loss_sigma: Uncertainty in pit loss timing
    
    Returns:
        Expected total pit loss in seconds
    """
    # Pit loss from config already includes lane delta + stationary
    return pit_loss_seconds


def estimate_position_loss(
    gap_to_behind: float | None,
    pit_loss: float,
    safety_margin: float = 1.0,
) -> int:
    """
    Estimate how many positions we lose during a pit stop.
    
    Args:
        gap_to_behind: Gap to the car behind in seconds
        pit_loss: Total pit stop time loss
        safety_margin: Extra buffer for safety
    
    Returns:
        Number of positions likely to be lost
    """
    if gap_to_behind is None:
        return 1  # Assume at least 1 position if unknown
    
    # How many cars could pass during pit + margin
    effective_gap = pit_loss + safety_margin
    
    if gap_to_behind > effective_gap:
        return 0  # Safe pit, no position loss
    
    # Rough estimate: 1 position per ~2s of exposure
    positions = int((effective_gap - gap_to_behind) / 2.0) + 1
    return min(positions, 5)  # Cap at 5 positions max


def calculate_undercut_threshold(
    deg_slope_us: float,
    deg_slope_ahead: float,
    pit_loss: float,
    laps_in_window: int = 3,
) -> float:
    """
    Calculate lap time delta needed for successful undercut.
    
    The undercut works when fresh tyres give enough pace advantage
    to overcome the pit stop time loss before the car ahead pits.
    
    Args:
        deg_slope_us: Our degradation rate (s/lap)
        deg_slope_ahead: Car ahead's degradation rate
        pit_loss: Pit stop time loss
        laps_in_window: Expected laps before they pit
    
    Returns:
        Lap time improvement needed on fresh tyres
    """
    # Fresh tyre advantage needed per lap
    # Must recover pit_loss over laps_in_window
    required_delta_per_lap = pit_loss / max(laps_in_window, 1)
    
    # Factor in relative degradation
    # If they degrade faster, we need less advantage
    deg_advantage = deg_slope_ahead - deg_slope_us
    
    return required_delta_per_lap - deg_advantage


def calculate_overcut_viability(
    deg_slope_us: float,
    deg_slope_ahead: float,
    current_gap: float,
    pit_loss: float,
    laps_to_pit: int,
) -> tuple[bool, float]:
    """
    Determine if overcut strategy is viable.
    
    Overcut works when staying out longer on old tyres
    still leaves us ahead after they pit on fresh tyres.
    
    Args:
        deg_slope_us: Our degradation rate
        deg_slope_ahead: Car ahead's degradation rate
        current_gap: Current gap to car ahead (positive = behind)
        pit_loss: Pit stop time loss
        laps_to_pit: How many more laps we'll stay out
    
    Returns:
        Tuple of (is_viable, gap_after_overcut)
    """
    # They pit, we stay out
    # Their time: pit_loss + fresh_tyre_pace * laps
    # Our time: old_tyre_pace * laps
    
    # Estimate pace difference
    pace_loss_per_lap = deg_slope_us * laps_to_pit  # We lose this staying out
    
    # Gap change during overcut period
    gap_change = pit_loss - pace_loss_per_lap
    
    final_gap = current_gap + gap_change
    
    # Overcut viable if we're still ahead afterward
    is_viable = final_gap > 0
    
    return is_viable, final_gap


def get_pit_loss_estimate(
    track_pit_loss: float,
    gap_to_behind: float | None,
    our_deg: float,
    ahead_deg: float,
) -> PitLossEstimate:
    """
    Get complete pit loss estimate for strategy decisions.
    
    Args:
        track_pit_loss: Track-specific pit loss time
        gap_to_behind: Gap to car behind
        our_deg: Our degradation rate
        ahead_deg: Car ahead's degradation rate
    
    Returns:
        PitLossEstimate with full breakdown
    """
    total = calculate_pit_loss(track_pit_loss)
    positions = estimate_position_loss(gap_to_behind, total)
    undercut_thresh = calculate_undercut_threshold(our_deg, ahead_deg, total)
    
    return PitLossEstimate(
        pit_lane_delta=total * 0.6,  # ~60% is lane delta
        stationary_time=total * 0.4,  # ~40% is stationary
        total_loss=total,
        positions_at_risk=positions,
        undercut_threshold=undercut_thresh,
    )
