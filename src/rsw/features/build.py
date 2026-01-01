"""
Feature builder for extracting race analytics features from lap data.

Features are computed per driver and used as inputs to the
degradation models and strategy calculations.
"""

from dataclasses import dataclass, field
from typing import Optional
import statistics


@dataclass
class FeatureFrame:
    """
    Feature container for a single driver at a point in the race.
    
    These features are used by the degradation model and strategy engine.
    """
    driver_number: int
    lap_number: int
    
    # Stint features
    lap_in_stint: int = 0
    stint_number: int = 1
    compound: str = "UNKNOWN"
    tyre_age: int = 0
    
    # Pace features
    lap_time: float | None = None
    recent_pace_mean: float | None = None
    recent_pace_std: float | None = None
    best_lap_time: float | None = None
    
    # Track evolution proxy (normalized race progress)
    # Rubber builds up on track, making it faster as race progresses
    track_evolution: float = 0.0  # 0.0 = start, 1.0 = end
    
    # Traffic indicators
    gap_ahead: float | None = None
    traffic_affected: bool = False
    clean_air: bool = True
    
    # Flags
    is_pit_in_lap: bool = False
    is_pit_out_lap: bool = False
    is_sc_lap: bool = False
    is_vsc_lap: bool = False
    is_valid: bool = True  # Valid for model training
    
    # Fuel correction (approximate)
    fuel_corrected_time: float | None = None


def build_features(
    driver_number: int,
    lap_number: int,
    lap_times: list[float],
    lap_in_stint: int,
    stint_number: int,
    compound: str | None,
    tyre_age: int,
    gap_ahead: float | None,
    total_laps: int,
    is_pit_out: bool = False,
    is_sc: bool = False,
    is_vsc: bool = False,
    window_size: int = 5,
) -> FeatureFrame:
    """
    Build a feature frame for a driver at a specific lap.
    
    Args:
        driver_number: Driver's car number
        lap_number: Current lap in the race
        lap_times: List of this driver's lap times so far
        lap_in_stint: Laps since last pit stop
        stint_number: Current stint number (1-indexed)
        compound: Tyre compound ("SOFT", "MEDIUM", "HARD", etc.)
        tyre_age: Total age of tyres in laps
        gap_ahead: Gap to car in front in seconds
        total_laps: Total race laps
        is_pit_out: Whether this is an out-lap from pits
        is_sc: Whether safety car is deployed
        is_vsc: Whether virtual safety car is active
        window_size: Rolling window for pace statistics
    
    Returns:
        FeatureFrame with computed features
    """
    frame = FeatureFrame(
        driver_number=driver_number,
        lap_number=lap_number,
        lap_in_stint=lap_in_stint,
        stint_number=stint_number,
        compound=compound or "UNKNOWN",
        tyre_age=tyre_age,
        gap_ahead=gap_ahead,
        is_pit_out_lap=is_pit_out,
        is_sc_lap=is_sc,
        is_vsc_lap=is_vsc,
    )
    
    # Current lap time
    if lap_times and len(lap_times) >= lap_number:
        frame.lap_time = lap_times[lap_number - 1] if lap_number > 0 else None
    elif lap_times:
        frame.lap_time = lap_times[-1] if lap_times else None
    
    # Best lap time
    valid_times = [t for t in lap_times if t and t > 0]
    if valid_times:
        frame.best_lap_time = min(valid_times)
    
    # Rolling pace statistics
    recent_times = valid_times[-window_size:] if valid_times else []
    if len(recent_times) >= 2:
        frame.recent_pace_mean = statistics.mean(recent_times)
        frame.recent_pace_std = statistics.stdev(recent_times)
    elif recent_times:
        frame.recent_pace_mean = recent_times[0]
        frame.recent_pace_std = 0.0
    
    # Track evolution proxy (0 = start, 1 = end)
    frame.track_evolution = lap_number / max(total_laps, 1)
    
    # Traffic detection
    if gap_ahead is not None:
        frame.traffic_affected = gap_ahead < 1.5
        frame.clean_air = gap_ahead > 2.0
    
    # Fuel correction (approximate: 0.03s per kg, ~1.5kg per lap)
    # Early laps are slower due to fuel weight
    fuel_effect = (total_laps - lap_number) * 0.045  # ~0.045s per lap of fuel
    if frame.lap_time:
        frame.fuel_corrected_time = frame.lap_time - fuel_effect
    
    # Validity for model training
    frame.is_valid = (
        not frame.is_pit_in_lap
        and not frame.is_pit_out_lap
        and not frame.is_sc_lap
        and not frame.is_vsc_lap
        and not frame.traffic_affected
        and frame.lap_time is not None
        and frame.lap_time > 0
    )
    
    return frame


def build_stint_features(
    lap_times: list[float],
    stint_start_lap: int,
    compound: str,
    total_laps: int,
) -> list[FeatureFrame]:
    """
    Build feature frames for all laps in a stint.
    
    Useful for batch processing of historical data.
    """
    frames = []
    for i, lap_time in enumerate(lap_times):
        lap_number = stint_start_lap + i
        lap_in_stint = i + 1
        
        frame = build_features(
            driver_number=0,  # Will be set by caller
            lap_number=lap_number,
            lap_times=lap_times[:i + 1],
            lap_in_stint=lap_in_stint,
            stint_number=1,
            compound=compound,
            tyre_age=lap_in_stint,
            gap_ahead=None,
            total_laps=total_laps,
        )
        frames.append(frame)
    
    return frames
