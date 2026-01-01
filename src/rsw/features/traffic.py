"""
Traffic detection heuristics for identifying laps affected by dirty air.

Dirty air behind another car causes loss of downforce and slower lap times.
"""

from dataclasses import dataclass


@dataclass
class TrafficState:
    """Tracks traffic state for a driver."""
    driver_number: int
    consecutive_close_laps: int = 0
    avg_gap_recent: float | None = None
    is_in_traffic: bool = False


def detect_traffic(
    gap_ahead: float | None,
    previous_gaps: list[float] | None = None,
    close_gap_threshold: float = 1.5,
    sustained_laps: int = 2,
) -> tuple[bool, float]:
    """
    Detect if a driver is affected by traffic.
    
    Args:
        gap_ahead: Current gap to car in front (seconds)
        previous_gaps: List of gaps from previous laps
        close_gap_threshold: Gap below which traffic is considered
        sustained_laps: Number of consecutive laps for sustained traffic
    
    Returns:
        Tuple of (is_traffic_affected, traffic_severity)
        - is_traffic_affected: Boolean flag
        - traffic_severity: 0.0 to 1.0 scale of traffic impact
    """
    if gap_ahead is None:
        return False, 0.0
    
    # Immediate traffic detection
    is_close = gap_ahead < close_gap_threshold
    
    # Calculate severity (0 = no traffic, 1 = severe traffic)
    if gap_ahead >= close_gap_threshold:
        severity = 0.0
    elif gap_ahead <= 0.5:
        severity = 1.0
    else:
        # Linear interpolation
        severity = 1.0 - (gap_ahead - 0.5) / (close_gap_threshold - 0.5)
    
    # Check for sustained traffic
    if previous_gaps:
        recent_close = sum(1 for g in previous_gaps[-sustained_laps:] if g < close_gap_threshold)
        is_sustained = recent_close >= sustained_laps
        
        if is_sustained:
            severity = min(1.0, severity * 1.2)  # Boost severity for sustained traffic
    else:
        is_sustained = False
    
    return is_close or is_sustained, severity


def estimate_traffic_delta(
    gap_ahead: float | None,
    base_delta: float = 0.3,
    max_delta: float = 1.0,
) -> float:
    """
    Estimate lap time loss due to traffic.
    
    Args:
        gap_ahead: Gap to car in front (seconds)
        base_delta: Minimum time loss in dirty air
        max_delta: Maximum time loss in very close proximity
    
    Returns:
        Estimated lap time delta in seconds
    """
    if gap_ahead is None or gap_ahead > 2.0:
        return 0.0
    
    if gap_ahead <= 0.5:
        return max_delta
    
    if gap_ahead <= 1.5:
        # DRS zone - less penalty due to speed boost
        return base_delta * 0.5
    
    # Dirty air zone (1.5 - 2.0s)
    return base_delta * (2.0 - gap_ahead) / 0.5


def detect_traffic_spike(
    current_lap_time: float,
    recent_lap_times: list[float],
    spike_threshold: float = 0.5,
) -> bool:
    """
    Detect sudden lap time spike that might indicate traffic.
    
    A sudden spike compared to rolling average often indicates
    traffic or other external factors.
    """
    if not recent_lap_times or len(recent_lap_times) < 3:
        return False
    
    if current_lap_time <= 0:
        return False
    
    # Calculate rolling mean
    mean = sum(recent_lap_times) / len(recent_lap_times)
    
    # Check for spike
    delta = current_lap_time - mean
    
    return delta > spike_threshold


class TrafficTracker:
    """
    Tracks traffic state for multiple drivers across a race.
    """
    
    def __init__(self, close_gap_threshold: float = 1.5):
        self.close_gap_threshold = close_gap_threshold
        self.driver_states: dict[int, TrafficState] = {}
        self.gap_history: dict[int, list[float]] = {}
    
    def update(
        self,
        driver_number: int,
        gap_ahead: float | None,
    ) -> tuple[bool, float]:
        """
        Update traffic state for a driver.
        
        Returns (is_in_traffic, severity).
        """
        # Initialize state if needed
        if driver_number not in self.driver_states:
            self.driver_states[driver_number] = TrafficState(driver_number)
            self.gap_history[driver_number] = []
        
        state = self.driver_states[driver_number]
        history = self.gap_history[driver_number]
        
        # Record gap
        if gap_ahead is not None:
            history.append(gap_ahead)
            # Keep last 10 gaps
            if len(history) > 10:
                history.pop(0)
        
        # Detect traffic
        is_traffic, severity = detect_traffic(
            gap_ahead,
            previous_gaps=history[:-1] if history else None,
            close_gap_threshold=self.close_gap_threshold,
        )
        
        # Update state
        state.is_in_traffic = is_traffic
        if gap_ahead is not None and gap_ahead < self.close_gap_threshold:
            state.consecutive_close_laps += 1
        else:
            state.consecutive_close_laps = 0
        
        return is_traffic, severity
    
    def get_state(self, driver_number: int) -> TrafficState | None:
        """Get current traffic state for a driver."""
        return self.driver_states.get(driver_number)
