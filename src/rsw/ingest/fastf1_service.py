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
import atexit
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC
from typing import Any

import numpy as np
import pandas as pd

from rsw.logging_config import get_logger
from rsw.state.schemas import DriverState

logger = get_logger(__name__)

# FastF1 imports - will be lazy loaded
_fastf1 = None
_fastf1_cache_enabled = False


def _ensure_fastf1() -> Any:
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
        logger.info("fastf1_cache_enabled", cache_dir=cache_dir)

    return _fastf1


# Thread pool for running blocking FastF1 calls
_FASTF1_WORKERS = int(os.getenv("RSW_FASTF1_WORKERS", "4"))
_executor = ThreadPoolExecutor(max_workers=_FASTF1_WORKERS)
atexit.register(lambda: _executor.shutdown(wait=False))


async def load_session(year: int, round_number: int | str, session_type: str = "R") -> Any:
    """
    Load a FastF1 session asynchronously.

    Args:
        year: Season year (e.g., 2023)
        round_number: Round number or circuit name
        session_type: 'R' (Race), 'Q' (Qualifying), 'S' (Sprint), etc.

    Returns:
        FastF1 Session object with telemetry loaded
    """

    def _load() -> Any:
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


async def get_track_geometry(session: Any) -> dict[str, Any]:
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

    def _extract() -> dict[str, Any]:
        try:
            # Check if laps are available/loaded
            if not hasattr(session, "laps"):
                raise ValueError("Session laps property missing")

            # Get fastest lap for track geometry
            try:
                fastest_lap = session.laps.pick_fastest()
            except Exception as e:
                logger.debug("pick_fastest_failed", error=str(e))
                fastest_lap = None

            if fastest_lap is None:
                # Fallback: pick first valid lap
                try:
                    valid_laps = session.laps.dropna(subset=["LapTime"])
                    if valid_laps.empty:
                        raise ValueError("No valid laps found in session")
                    fastest_lap = valid_laps.iloc[0]
                except Exception as e:
                    raise ValueError(f"Could not retrieve any laps for geometry: {e}") from e

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
            except Exception as e:
                logger.debug("circuit_info_unavailable", error=str(e))
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
            logger.warning("track_geometry_extraction_failed", error=str(e))
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


async def get_driver_positions(session: Any, frame_index: int = 0) -> dict[str, dict]:
    """
    Get driver positions at a specific frame/time.

    For live data, this returns current positions.
    For replay, this returns positions at the given frame.
    """

    def _extract() -> dict[str, dict]:
        drivers: dict[str, dict] = {}

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
                logger.debug("driver_position_error", driver=driver, error=str(e))
                continue

        return drivers

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _extract)


async def get_weather_data(session: Any) -> list[dict]:
    """
    Extract weather data from session.

    Returns list of weather snapshots with track_temp, air_temp, humidity, etc.
    """

    def _extract() -> list[dict]:
        weather_df = getattr(session, "weather_data", None)
        if weather_df is None or weather_df.empty:
            return []

        # Vectorized extraction using to_dict
        result = pd.DataFrame()
        result["time"] = weather_df["Time"].apply(
            lambda t: t.total_seconds() if hasattr(t, "total_seconds") else 0
        )

        col_map = {
            "TrackTemp": "track_temp",
            "AirTemp": "air_temp",
            "Humidity": "humidity",
            "WindSpeed": "wind_speed",
            "WindDirection": "wind_direction",
        }
        for src, dst in col_map.items():
            if src in weather_df.columns:
                col = weather_df[src]
                result[dst] = col.where(col.notna(), None).astype(float, errors="ignore")
            else:
                result[dst] = None

        if "Rainfall" in weather_df.columns:
            result["rainfall"] = weather_df["Rainfall"].fillna(False).astype(bool)
        else:
            result["rainfall"] = False

        return result.to_dict(orient="records")  # type: ignore[no-any-return]

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _extract)


async def get_session_info(year: int, round_number: int | str) -> dict:
    """
    Get basic session info without loading full telemetry.
    Faster than load_session when you only need metadata.
    """

    def _get_info() -> dict[str, Any] | None:
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
    return await loop.run_in_executor(_executor, _get_info)  # type: ignore[arg-type]


# Cache for loaded sessions to avoid reloading
_session_cache: dict[str, Any] = {}


async def get_or_load_session(year: int, round_number: int | str, session_type: str = "R") -> Any:
    """Get cached session or load it."""
    cache_key = f"{year}_{round_number}_{session_type}"

    if cache_key not in _session_cache:
        logger.info("loading_fastf1_session", year=year, round=round_number, type=session_type)
        _session_cache[cache_key] = await load_session(year, round_number, session_type)
        logger.info("fastf1_session_loaded")

    return _session_cache[cache_key]


def clear_session_cache() -> None:
    """Clear the session cache to free memory."""
    _session_cache.clear()


def extract_race_data(session: Any) -> Any:
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
                except Exception as e:
                    logger.debug("driver_parse_skip", driver_id=driver_id, error=str(e))
                    continue
    except Exception as e:
        logger.warning("driver_extraction_failed", error=str(e))

    # 2. Laps - Convert to LapData Pydantic models
    def _timedelta_to_seconds(val: Any) -> float | None:
        """Safely convert Timedelta to float seconds, or None for NaT."""
        if val is None:
            return None
        if hasattr(val, "total_seconds"):
            return float(val.total_seconds())
        # Check for NaT (pandas Not-a-Time)
        try:
            if pd.isna(val):
                return None
        except (TypeError, ValueError):
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
                logger.warning("lap_iteration_failed", error=str(e))
    except Exception as e:
        logger.warning("lap_parsing_failed", error=str(e))
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
                logger.warning("pit_extraction_failed", error=str(e))
    except Exception as e:
        logger.warning("pit_data_extraction_failed", error=str(e))
        all_pits = []

    # 4. Stints - Parse real stints from FastF1 lap data (Stint + Compound columns)
    all_stints = []
    _compound_aliases = {
        "SOFT": "SOFT", "MEDIUM": "MEDIUM", "HARD": "HARD",
        "INTERMEDIATE": "INTERMEDIATE", "WET": "WET",
        "SUPERSOFT": "SOFT", "ULTRASOFT": "SOFT", "HYPERSOFT": "SOFT",
        "C1": "HARD", "C2": "HARD", "C3": "MEDIUM",
        "C4": "MEDIUM", "C5": "SOFT",
    }
    try:
        if hasattr(session, "laps"):
            laps_df = session.laps
            required_cols = {"DriverNumber", "Stint", "Compound", "LapNumber"}
            if required_cols.issubset(laps_df.columns):
                for (drv_num, stint_num), grp in laps_df.groupby(["DriverNumber", "Stint"]):
                    try:
                        drv_int = int(drv_num)
                        stint_int = int(stint_num)

                        # Use most common non-null compound value in this stint group
                        raw_compounds = [
                            str(c).strip().upper()
                            for c in grp["Compound"].dropna().tolist()
                            if str(c).strip() not in ("", "NAN", "NONE", "UNKNOWN")
                        ]
                        if raw_compounds:
                            raw_compound = max(set(raw_compounds), key=raw_compounds.count)
                            compound = _compound_aliases.get(raw_compound, "UNKNOWN")
                        else:
                            compound = "UNKNOWN"

                        lap_start = int(grp["LapNumber"].min())
                        lap_end = int(grp["LapNumber"].max())

                        # TyreLife on lap 1 of stint = 1 (new tyre) or higher (used tyre)
                        tyre_age_at_start = 0
                        if "TyreLife" in grp.columns:
                            first_life = grp["TyreLife"].iloc[0]
                            if pd.notna(first_life):
                                tyre_age_at_start = max(0, int(first_life) - 1)

                        all_stints.append(
                            StintData(
                                driver_number=drv_int,
                                stint_number=stint_int,
                                compound=compound,
                                lap_start=lap_start,
                                lap_end=lap_end,
                                tyre_age_at_start=tyre_age_at_start,
                            )
                        )
                    except Exception as e:
                        logger.debug("stint_parse_skip", driver=drv_num, stint=stint_num, error=str(e))
                        continue
    except Exception as e:
        logger.warning("stint_extraction_failed", error=str(e))

    # Fallback: if no stints were extracted, create a single dummy stint per driver
    if not all_stints and all_laps:
        max_lap = max(l.lap_number for l in all_laps)
        for drv in drivers:
            all_stints.append(
                StintData(
                    driver_number=drv.driver_number,
                    stint_number=1,
                    compound="UNKNOWN",
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
            now = datetime.now(UTC)
            for row in messages.itertuples():
                category = getattr(row, "Category", "Other") or "Other"
                flag = getattr(row, "Flag", None)
                message = getattr(row, "Message", "") or ""
                raw_lap = getattr(row, "Lap", None)
                lap_number = int(raw_lap) if raw_lap is not None and str(raw_lap).isdigit() else None
                raw_num = getattr(row, "RacingNumber", None)
                driver_number = int(raw_num) if raw_num is not None and str(raw_num).isdigit() else None

                all_race_control.append(
                    RaceControlMessage(
                        category=category,
                        flag=flag,
                        message=message,
                        lap_number=lap_number,
                        driver_number=driver_number,
                        timestamp=now,
                    )
                )
    except Exception as e:
        logger.warning("race_control_extraction_failed", error=str(e))
        all_race_control = []

    return drivers, all_laps, all_stints, all_pits, all_race_control
