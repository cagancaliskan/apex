"""
FastF1 Service - Real F1 telemetry and track geometry data.

This service uses the FastF1 library to fetch actual telemetry data from
official F1 timing servers, including:
- Track geometry (X/Y coordinates)
- Driver telemetry (speed, gear, throttle, brake)
- Weather data
- DRS zones

API Documentation: https://docs.fastf1.dev/
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC
from typing import Any

import numpy as np
import pandas as pd

from rsw.state.schemas import DriverState

# FastF1 imports - will be lazy loaded
_fastf1 = None
_fastf1_cache_enabled = False


def _ensure_fastf1():
    """Lazy load and configure FastF1."""
    global _fastf1, _fastf1_cache_enabled
    if _fastf1 is None:
        import fastf1

        _fastf1 = fastf1

        # Enable cache
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".fastf1-cache")
        os.makedirs(cache_dir, exist_ok=True)
        fastf1.Cache.enable_cache(cache_dir)
        _fastf1_cache_enabled = True
        print(f"FastF1 cache enabled at: {cache_dir}")

    return _fastf1


# Thread pool for running blocking FastF1 calls
_executor = ThreadPoolExecutor(max_workers=2)


async def load_session(year: int, round_number: int | str, session_type: str = "R"):
    """
    Load a FastF1 session asynchronously.

    Args:
        year: Season year (e.g., 2023)
        round_number: Round number or circuit name
        session_type: 'R' (Race), 'Q' (Qualifying), 'S' (Sprint), etc.

    Returns:
        FastF1 Session object with telemetry loaded
    """

    def _load():
        fastf1 = _ensure_fastf1()
        session = fastf1.get_session(year, round_number, session_type)
        session.load(telemetry=True, weather=True)
        return session

    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(_executor, _load)
    except Exception as e:
        # Rethrow as RuntimeError for consistent handling
        raise RuntimeError(f"FastF1 load failed: {e}") from e


async def get_track_geometry(session) -> dict[str, Any]:
    """
    Extract track geometry from session telemetry.

    Uses the fastest lap's telemetry to get X/Y coordinates that
    define the track layout.

    Returns:
        dict with:
            - center_line: list of {x, y, rel_dist} points
            - inner_edge: list of {x, y} points
            - outer_edge: list of {x, y} points
            - drs_zones: list of {start_idx, end_idx, start_rel, end_rel}
            - bounds: {x_min, x_max, y_min, y_max}
            - rotation: circuit rotation angle
    """

    def _extract():
        try:
            # Check if laps are available/loaded
            if not hasattr(session, "laps"):
                raise ValueError("Session laps property missing")

            # Get fastest lap for track geometry
            try:
                fastest_lap = session.laps.pick_fastest()
            except Exception:
                # Handle DataNotLoadedError or other access errors
                fastest_lap = None

            if fastest_lap is None:
                # Fallback: pick first valid lap
                try:
                    valid_laps = session.laps.dropna(subset=["LapTime"])
                    if valid_laps.empty:
                        raise ValueError("No valid laps found in session")
                    fastest_lap = valid_laps.iloc[0]
                except Exception:
                    raise ValueError("Could not retrive any laps for geometry")

            telemetry = fastest_lap.get_telemetry()
            if telemetry is None or telemetry.empty:
                raise ValueError("No telemetry data available")

            # Extract coordinates
            x = telemetry["X"].to_numpy()
            y = telemetry["Y"].to_numpy()

            # Get relative distance if available, otherwise compute it
            if "RelativeDistance" in telemetry:
                rel_dist = telemetry["RelativeDistance"].to_numpy()
            else:
                # Compute from distance
                dist = telemetry["Distance"].to_numpy()
                rel_dist = dist / dist.max() if dist.max() > 0 else np.zeros_like(dist)

            # Compute track edges using normal vectors
            track_width = 15  # meters (approximate F1 track width)

            # Calculate tangent vectors
            dx = np.gradient(x)
            dy = np.gradient(y)

            # Normalize
            norm = np.sqrt(dx**2 + dy**2)
            norm[norm == 0] = 1.0
            dx = dx / norm
            dy = dy / norm

            # Normal vectors (perpendicular to tangent)
            nx = -dy
            ny = dx

            # Compute edges
            x_inner = x - nx * (track_width / 2)
            y_inner = y - ny * (track_width / 2)
            x_outer = x + nx * (track_width / 2)
            y_outer = y + ny * (track_width / 2)

            # Get DRS zones from telemetry
            drs = telemetry["DRS"].to_numpy()
            drs_zones = _extract_drs_zones(drs, x, y, rel_dist)

            # Compute bounds
            all_x = np.concatenate([x, x_inner, x_outer])
            all_y = np.concatenate([y, y_inner, y_outer])

            # Get circuit rotation angle if available
            try:
                circuit_info = session.get_circuit_info()
                rotation = float(circuit_info.rotation) if circuit_info else 0
            except Exception:
                rotation = 0

            # Downsample for transfer (every 5th point is usually enough)
            step = 5

            return {
                "center_line": [
                    {"x": float(x[i]), "y": float(y[i]), "rel_dist": float(rel_dist[i])}
                    for i in range(0, len(x), step)
                ],
                "inner_edge": [
                    {"x": float(x_inner[i]), "y": float(y_inner[i])}
                    for i in range(0, len(x_inner), step)
                ],
                "outer_edge": [
                    {"x": float(x_outer[i]), "y": float(y_outer[i])}
                    for i in range(0, len(x_outer), step)
                ],
                "drs_zones": drs_zones,
                "bounds": {
                    "x_min": float(all_x.min()),
                    "x_max": float(all_x.max()),
                    "y_min": float(all_y.min()),
                    "y_max": float(all_y.max()),
                },
                "rotation": rotation,
                "total_points": len(x),
            }
        except Exception as e:
            print(f"Warning: Failed to extract track geometry: {e}")
            # Return empty default geometry (perfect circle placeholder or empty)
            return {
                "center_line": [],
                "inner_edge": [],
                "outer_edge": [],
                "drs_zones": [],
                "bounds": {"x_min": 0, "x_max": 0, "y_min": 0, "y_max": 0},
                "rotation": 0,
                "total_points": 0,
            }

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _extract)


def _extract_drs_zones(
    drs: np.ndarray, x: np.ndarray, y: np.ndarray, rel_dist: np.ndarray
) -> list[dict]:
    """Extract DRS zones from telemetry DRS signal."""
    zones = []
    in_zone = False
    zone_start_idx = 0

    for i, val in enumerate(drs):
        # DRS is active when value is 10, 12, or 14
        is_drs_on = val in [10, 12, 14]

        if is_drs_on and not in_zone:
            # Zone started
            in_zone = True
            zone_start_idx = i
        elif not is_drs_on and in_zone:
            # Zone ended
            in_zone = False
            zones.append(
                {
                    "start_idx": int(zone_start_idx),
                    "end_idx": int(i - 1),
                    "start_x": float(x[zone_start_idx]),
                    "start_y": float(y[zone_start_idx]),
                    "end_x": float(x[i - 1]),
                    "end_y": float(y[i - 1]),
                    "start_rel": float(rel_dist[zone_start_idx]),
                    "end_rel": float(rel_dist[i - 1]),
                }
            )

    # Handle zone that extends to end of lap
    if in_zone:
        zones.append(
            {
                "start_idx": int(zone_start_idx),
                "end_idx": int(len(drs) - 1),
                "start_x": float(x[zone_start_idx]),
                "start_y": float(y[zone_start_idx]),
                "end_x": float(x[-1]),
                "end_y": float(y[-1]),
                "start_rel": float(rel_dist[zone_start_idx]),
                "end_rel": float(rel_dist[-1]),
            }
        )

    return zones


async def get_driver_positions(session, frame_index: int = 0) -> dict[str, dict]:
    """
    Get driver positions at a specific frame/time.

    For live data, this returns current positions.
    For replay, this returns positions at the given frame.
    """

    def _extract():
        drivers = {}

        for driver in session.drivers:
            try:
                driver_laps = session.laps.pick_drivers(driver)
                if driver_laps.empty:
                    continue

                # Get driver info
                driver_info = session.get_driver(driver)
                code = driver_info.get("Abbreviation", str(driver))

                # Get latest lap telemetry
                latest_lap = driver_laps.iloc[-1]
                telemetry = latest_lap.get_telemetry()

                if telemetry is None or telemetry.empty:
                    continue

                # Get position at frame (or latest if frame exceeds)
                idx = min(frame_index, len(telemetry) - 1)

                drivers[code] = {
                    "x": float(telemetry["X"].iloc[idx]),
                    "y": float(telemetry["Y"].iloc[idx]),
                    "speed": float(telemetry["Speed"].iloc[idx]),
                    "gear": int(telemetry["nGear"].iloc[idx]),
                    "throttle": float(telemetry["Throttle"].iloc[idx]),
                    "brake": float(telemetry["Brake"].iloc[idx]) * 100,  # Normalize to 0-100
                    "drs": int(telemetry["DRS"].iloc[idx]),
                    "rel_dist": float(telemetry["RelativeDistance"].iloc[idx])
                    if "RelativeDistance" in telemetry
                    else 0,
                }
            except Exception as e:
                print(f"Error getting position for driver {driver}: {e}")
                continue

        return drivers

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _extract)


async def get_weather_data(session) -> list[dict]:
    """
    Extract weather data from session.

    Returns list of weather snapshots with track_temp, air_temp, humidity, etc.
    """

    def _extract():
        weather_df = getattr(session, "weather_data", None)
        if weather_df is None or weather_df.empty:
            return []

        weather_points = []
        for _, row in weather_df.iterrows():
            point = {
                "time": row["Time"].total_seconds() if hasattr(row["Time"], "total_seconds") else 0,
                "track_temp": float(row.get("TrackTemp", 0))
                if row.get("TrackTemp") is not None
                else None,
                "air_temp": float(row.get("AirTemp", 0))
                if row.get("AirTemp") is not None
                else None,
                "humidity": float(row.get("Humidity", 0))
                if row.get("Humidity") is not None
                else None,
                "wind_speed": float(row.get("WindSpeed", 0))
                if row.get("WindSpeed") is not None
                else None,
                "wind_direction": float(row.get("WindDirection", 0))
                if row.get("WindDirection") is not None
                else None,
                "rainfall": bool(row.get("Rainfall", False))
                if row.get("Rainfall") is not None
                else False,
            }
            weather_points.append(point)

        return weather_points

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _extract)


async def get_session_info(year: int, round_number: int | str) -> dict:
    """
    Get basic session info without loading full telemetry.
    Faster than load_session when you only need metadata.
    """

    def _get_info():
        fastf1 = _ensure_fastf1()
        schedule = fastf1.get_event_schedule(year)

        if isinstance(round_number, int):
            event = schedule.iloc[round_number - 1]
        else:
            # Search by circuit name
            matches = schedule[schedule["EventName"].str.contains(round_number, case=False)]
            if matches.empty:
                return None
            event = matches.iloc[0]

        return {
            "event_name": event["EventName"],
            "country": event["Country"],
            "location": event["Location"],
            "round": int(event["RoundNumber"]),
        }

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_info)


# Cache for loaded sessions to avoid reloading
_session_cache: dict[str, Any] = {}


async def get_or_load_session(year: int, round_number: int | str, session_type: str = "R"):
    """Get cached session or load it."""
    cache_key = f"{year}_{round_number}_{session_type}"

    if cache_key not in _session_cache:
        print(f"Loading FastF1 session: {year} R{round_number} {session_type}...")
        _session_cache[cache_key] = await load_session(year, round_number, session_type)
        print("Session loaded successfully")

    return _session_cache[cache_key]


def clear_session_cache():
    """Clear the session cache to free memory."""
    _session_cache = {}


def extract_race_data(session):
    """
    Extract comprehensive race data from a loaded FastF1 session.

    Args:
        session: Loaded FastF1 session object

    Returns:
        Tuple containing:
        - drivers: List[DriverState]
        - all_laps: List[LapData] (Pydantic)
        - all_stints: List[StintData] (Pydantic)
        - all_pits: List[PitData] (Pydantic)
        - all_race_control: List[RaceControlMessage] (Pydantic)
    """
    from datetime import datetime

    from rsw.ingest.base import LapData, PitData, RaceControlMessage, StintData

    # 1. Extract Drivers
    drivers = []
    try:
        # Check if drivers are available
        if hasattr(session, "drivers"):
            for driver_id in session.drivers:
                try:
                    drv = session.get_driver(driver_id)
                    if not str(drv["DriverNumber"]).isdigit():
                        continue

                    driver_state = DriverState(
                        driver_number=int(drv["DriverNumber"]),
                        name_acronym=drv["Abbreviation"] or str(drv["DriverNumber"]),
                        full_name=drv["FullName"] or f"Driver {drv['DriverNumber']}",
                        team_name=drv["TeamName"] or "Unknown",
                        team_colour=drv["TeamColor"] or "FFFFFF",
                        position=int(drv["ClassifiedPosition"])
                        if str(drv["ClassifiedPosition"]).isdigit()
                        else 0,
                    )
                    drivers.append(driver_state)
                except Exception:
                    continue
    except Exception as e:
        print(f"Warning: Failed to extract drivers: {e}")

    # 2. Laps - Convert to LapData Pydantic models
    def _timedelta_to_seconds(val):
        """Safely convert Timedelta to float seconds, or None for NaT."""
        if val is None:
            return None
        if hasattr(val, "total_seconds"):
            return val.total_seconds()
        # Check for NaT (pandas Not-a-Time)
        try:
            if pd.isna(val):
                return None
        except Exception:
            pass
        return None

    all_laps = []
    try:
        # Verify laps attribute existence and accessibility
        if hasattr(session, "laps"):
            try:
                laps_iter = session.laps.itertuples()
                for row in laps_iter:
                    lap_time = getattr(row, "LapTime", None)
                    lap_duration = _timedelta_to_seconds(lap_time)

                    # Safely get driver number
                    driver_num = getattr(row, "DriverNumber", None)
                    if driver_num is None:
                        continue

                    # Extract tyre data
                    # Handle NaN/None in Compound
                    raw_compound = getattr(row, "Compound", None)
                    compound = (
                        str(raw_compound)
                        if pd.notna(raw_compound) and str(raw_compound).strip() != ""
                        else "UNKNOWN"
                    )

                    # Handle NaN/None in TyreLife
                    raw_life = getattr(row, "TyreLife", 0)
                    tyre_age = int(raw_life) if pd.notna(raw_life) else 0

                    all_laps.append(
                        LapData(
                            driver_number=int(driver_num),
                            lap_number=int(getattr(row, "LapNumber", 0)),
                            lap_duration=lap_duration,
                            sector_1=_timedelta_to_seconds(getattr(row, "Sector1Time", None)),
                            sector_2=_timedelta_to_seconds(getattr(row, "Sector2Time", None)),
                            sector_3=_timedelta_to_seconds(getattr(row, "Sector3Time", None)),
                            is_pit_out_lap=getattr(row, "PitOutTime", None) is not None,
                            compound=compound,
                            tyre_age=tyre_age,
                        )
                    )
            except Exception as e:
                # Catch DataNotLoadedError or AttributeError from session.laps
                print(f"Warning: Failed to iterate laps: {e}")
    except Exception as e:
        print(f"Warning: Failed to parse laps: {e}")
        all_laps = []

    # 3. Pit Stops - Convert to PitData Pydantic models
    all_pits = []
    try:
        if hasattr(session, "laps"):
            # Manually filter for pit stops if pick_pit_stops is missing or fails
            try:
                # Check for standard FastF1 columns
                laps_df = session.laps
                if "PitInTime" in laps_df.columns:
                    # Filter for rows where PitInTime is not null (not NaT)
                    pit_stops = laps_df[pd.notna(laps_df["PitInTime"])]

                    for pit_row in pit_stops.itertuples():
                        driver_num = getattr(pit_row, "DriverNumber", None)
                        if driver_num is None:
                            continue

                        pit_duration = getattr(pit_row, "PitInTime", None)
                        if pit_duration and hasattr(pit_duration, "total_seconds"):
                            pit_duration = pit_duration.total_seconds()
                        else:
                            pit_duration = 20.0  # Default

                        all_pits.append(
                            PitData(
                                driver_number=int(driver_num),
                                lap_number=int(getattr(pit_row, "LapNumber", 0)),
                                pit_duration=pit_duration,
                                timestamp=datetime.now(
                                    UTC
                                ),  # FastF1 doesn't provide timestamps
                            )
                        )
            except Exception as e:
                print(f"Warning: Failed to manual extract pits: {e}")
    except Exception as e:
        print(f"Warning: Failed to extract pits: {e}")
        all_pits = []

    # 4. Stints - Convert to StintData Pydantic models
    all_stints = []
    if all_laps:
        max_lap = max(l.lap_number for l in all_laps)
        for drv in drivers:
            all_stints.append(
                StintData(
                    driver_number=drv.driver_number,
                    stint_number=1,
                    compound="MEDIUM",  # Default; ideally parse from FastF1
                    lap_start=1,
                    lap_end=max_lap,
                    tyre_age_at_start=0,
                )
            )

    # 5. Race Control - Convert to RaceControlMessage Pydantic models
    all_race_control = []
    try:
        messages = getattr(session, "race_control_messages", None)
        if messages is not None and not messages.empty:
            for _, msg in messages.iterrows():
                all_race_control.append(
                    RaceControlMessage(
                        category=msg.get("Category", "Other"),
                        flag=msg.get("Flag", None),
                        message=msg.get("Message", ""),
                        lap_number=int(msg["Lap"])
                        if msg.get("Lap") and str(msg["Lap"]).isdigit()
                        else None,
                        driver_number=int(msg["RacingNumber"])
                        if msg.get("RacingNumber") and str(msg["RacingNumber"]).isdigit()
                        else None,
                        timestamp=datetime.now(UTC),
                    )
                )
    except Exception as e:
        print(f"Warning: Failed to extract race control: {e}")
        all_race_control = []

    return drivers, all_laps, all_stints, all_pits, all_race_control
