"""
Lap time filters for removing outliers and invalid data points.

Clean data is essential for accurate degradation modeling.
"""

import statistics

from .build import FeatureFrame


def is_valid_lap(
    lap_time: float | None,
    is_pit_in: bool = False,
    is_pit_out: bool = False,
    is_sc: bool = False,
    is_vsc: bool = False,
    min_lap_time: float = 60.0,
    max_lap_time: float = 180.0,
) -> bool:
    """
    Check if a lap time is valid for analysis.

    Invalid laps include:
    - Pit in/out laps (slow due to pit lane travel)
    - Safety car laps (artificially slow)
    - Extremely fast or slow outliers
    """
    if lap_time is None or lap_time <= 0:
        return False

    if is_pit_in or is_pit_out:
        return False

    if is_sc or is_vsc:
        return False

    if lap_time < min_lap_time or lap_time > max_lap_time:
        return False

    return True


def filter_outliers_zscore(
    lap_times: list[float],
    threshold: float = 3.0,
) -> list[tuple[int, float]]:
    """
    Filter outliers using z-score method.

    Returns list of (index, lap_time) tuples for valid laps.
    """
    if len(lap_times) < 3:
        return [(i, t) for i, t in enumerate(lap_times) if t > 0]

    valid_times = [t for t in lap_times if t and t > 0]
    if len(valid_times) < 3:
        return [(i, t) for i, t in enumerate(lap_times) if t > 0]

    mean = statistics.mean(valid_times)
    std = statistics.stdev(valid_times)

    if std == 0:
        return [(i, t) for i, t in enumerate(lap_times)]

    result = []
    for i, lap_time in enumerate(lap_times):
        if lap_time is None or lap_time <= 0:
            continue
        z_score = abs(lap_time - mean) / std
        if z_score <= threshold:
            result.append((i, lap_time))

    return result


def filter_outliers_iqr(
    lap_times: list[float],
    multiplier: float = 1.5,
) -> list[tuple[int, float]]:
    """
    Filter outliers using Interquartile Range (IQR) method.

    More robust to non-normal distributions than z-score.
    """
    valid_times = sorted([t for t in lap_times if t and t > 0])

    if len(valid_times) < 4:
        return [(i, t) for i, t in enumerate(lap_times) if t and t > 0]

    n = len(valid_times)
    q1 = valid_times[n // 4]
    q3 = valid_times[3 * n // 4]
    iqr = q3 - q1

    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr

    result = []
    for i, lap_time in enumerate(lap_times):
        if lap_time is None or lap_time <= 0:
            continue
        if lower_bound <= lap_time <= upper_bound:
            result.append((i, lap_time))

    return result


def apply_filters(
    frames: list[FeatureFrame],
    remove_pit_laps: bool = True,
    remove_sc_laps: bool = True,
    remove_traffic: bool = True,
    outlier_method: str = "zscore",
    outlier_threshold: float = 3.0,
) -> list[FeatureFrame]:
    """
    Apply filters to a list of feature frames.

    Returns only frames that pass all filter criteria.
    """
    filtered = []

    for frame in frames:
        # Skip invalid laps
        if not frame.is_valid:
            continue

        # Pit lap filter
        if remove_pit_laps and (frame.is_pit_in_lap or frame.is_pit_out_lap):
            continue

        # Safety car filter
        if remove_sc_laps and (frame.is_sc_lap or frame.is_vsc_lap):
            continue

        # Traffic filter
        if remove_traffic and frame.traffic_affected:
            continue

        filtered.append(frame)

    # Apply outlier detection on lap times
    if filtered and outlier_method:
        lap_times = [f.lap_time for f in filtered if f.lap_time]

        if outlier_method == "zscore":
            valid_indices = {idx for idx, _ in filter_outliers_zscore(lap_times, outlier_threshold)}
        elif outlier_method == "iqr":
            valid_indices = {idx for idx, _ in filter_outliers_iqr(lap_times, outlier_threshold)}
        else:
            valid_indices = set(range(len(lap_times)))

        # Map back to frames
        time_idx = 0
        final_filtered = []
        for frame in filtered:
            if frame.lap_time:
                if time_idx in valid_indices:
                    final_filtered.append(frame)
                time_idx += 1

        return final_filtered

    return filtered


def mark_pit_laps(
    laps: list[dict],
    pit_laps: set[int],
) -> None:
    """
    Mark pit in/out laps in lap data.

    Pit in lap = the lap where driver enters pits
    Pit out lap = the lap after exiting pits
    """
    for lap in laps:
        lap_num = lap.get("lap_number", 0)

        # Pit in lap
        if lap_num in pit_laps:
            lap["is_pit_in"] = True

        # Pit out lap (lap after pit)
        if lap_num - 1 in pit_laps:
            lap["is_pit_out"] = True
