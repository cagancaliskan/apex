"""
Pure reducer functions for applying updates to race state.

These functions are pure (no side effects) and take the current state
plus an update payload, returning a new state. This makes testing
and debugging much easier.
"""

from datetime import datetime, timezone

from ..ingest.base import (
    DriverInfo,
    IntervalData,
    LapData,
    PitData,
    PositionData,
    RaceControlMessage,
    StintData,
    UpdateBatch,
)
from .schemas import DriverState, RaceState


def apply_drivers(state: RaceState, drivers: list[DriverInfo]) -> RaceState:
    """
    Apply driver information to state.
    
    This initializes or updates driver identity information (name, team, etc.).
    """
    new_drivers = {**state.drivers}
    
    for driver_info in drivers:
        existing = new_drivers.get(driver_info.driver_number)
        
        if existing:
            # Update existing driver's identity info
            new_drivers[driver_info.driver_number] = existing.model_copy(
                update={
                    "name_acronym": driver_info.name_acronym,
                    "full_name": driver_info.full_name,
                    "team_name": driver_info.team_name,
                    "team_colour": driver_info.team_colour,
                    "last_update": datetime.now(timezone.utc),
                }
            )
        else:
            # Create new driver state
            new_drivers[driver_info.driver_number] = DriverState(
                driver_number=driver_info.driver_number,
                name_acronym=driver_info.name_acronym,
                full_name=driver_info.full_name,
                team_name=driver_info.team_name,
                team_colour=driver_info.team_colour,
                last_update=datetime.now(timezone.utc),
            )
    
    return state.model_copy(update={"drivers": new_drivers})


def apply_laps(state: RaceState, laps: list[LapData]) -> RaceState:
    """
    Apply lap data to state.
    
    Updates driver lap times, sectors, and current lap information.
    """
    new_drivers = {**state.drivers}
    max_lap = state.current_lap
    
    for lap in laps:
        driver = new_drivers.get(lap.driver_number)
        if not driver:
            # Create new driver if not exists
            driver = DriverState(driver_number=lap.driver_number)
        
        # Only update if this is a newer lap
        if lap.lap_number >= driver.current_lap:
            new_drivers[lap.driver_number] = driver.model_copy(
                update={
                    "current_lap": lap.lap_number,
                    "last_lap_time": lap.lap_duration,
                    "best_lap_time": (
                        min(driver.best_lap_time, lap.lap_duration)
                        if driver.best_lap_time and lap.lap_duration
                        else lap.lap_duration or driver.best_lap_time
                    ),
                    "sector_1": lap.sector_1,
                    "sector_2": lap.sector_2,
                    "sector_3": lap.sector_3,
                    "is_pit_out_lap": lap.is_pit_out_lap,
                    "lap_in_stint": lap.lap_number - driver.stint_start_lap + 1,
                    "tyre_age": driver.tyre_age + (1 if lap.lap_number > driver.current_lap else 0),
                    "last_update": lap.timestamp or datetime.now(timezone.utc),
                }
            )
            max_lap = max(max_lap, lap.lap_number)
    
    return state.model_copy(
        update={
            "drivers": new_drivers,
            "current_lap": max_lap,
            "timestamp": datetime.now(timezone.utc),
        }
    )


def apply_positions(state: RaceState, positions: list[PositionData]) -> RaceState:
    """
    Apply position data to state.
    
    Updates driver positions in the race.
    """
    new_drivers = {**state.drivers}
    
    for pos in positions:
        driver = new_drivers.get(pos.driver_number)
        if driver:
            new_drivers[pos.driver_number] = driver.model_copy(
                update={
                    "position": pos.position,
                    "last_update": pos.timestamp,
                }
            )
        else:
            new_drivers[pos.driver_number] = DriverState(
                driver_number=pos.driver_number,
                position=pos.position,
                last_update=pos.timestamp,
            )
    
    return state.model_copy(update={"drivers": new_drivers})


def apply_intervals(state: RaceState, intervals: list[IntervalData]) -> RaceState:
    """
    Apply interval/gap data to state.
    
    Updates gap to leader and gap to car ahead.
    """
    new_drivers = {**state.drivers}
    
    for interval in intervals:
        driver = new_drivers.get(interval.driver_number)
        if driver:
            new_drivers[interval.driver_number] = driver.model_copy(
                update={
                    "gap_to_leader": interval.gap_to_leader,
                    "gap_to_ahead": interval.interval,
                    "last_update": interval.timestamp,
                }
            )
    
    return state.model_copy(update={"drivers": new_drivers})


def apply_stints(state: RaceState, stints: list[StintData]) -> RaceState:
    """
    Apply stint (tyre) data to state.
    
    Updates tyre compound and stint information for each driver.
    """
    new_drivers = {**state.drivers}
    
    # Group stints by driver and get the latest stint for each
    driver_stints: dict[int, StintData] = {}
    for stint in stints:
        existing = driver_stints.get(stint.driver_number)
        if not existing or stint.stint_number > existing.stint_number:
            driver_stints[stint.driver_number] = stint
    
    for driver_num, stint in driver_stints.items():
        driver = new_drivers.get(driver_num)
        if driver:
            new_drivers[driver_num] = driver.model_copy(
                update={
                    "stint_number": stint.stint_number,
                    "compound": stint.compound,
                    "stint_start_lap": stint.lap_start,
                    "tyre_age": stint.tyre_age_at_start + max(0, driver.current_lap - stint.lap_start),
                    "lap_in_stint": max(1, driver.current_lap - stint.lap_start + 1),
                }
            )
    
    return state.model_copy(update={"drivers": new_drivers})


def apply_pits(state: RaceState, pits: list[PitData]) -> RaceState:
    """
    Apply pit stop data to state.
    
    Records recent pit stops for display.
    """
    # Add new pits to recent list (keep last 10)
    recent_pits = list(state.recent_pits)
    
    for pit in pits:
        pit_record = {
            "driver_number": pit.driver_number,
            "lap_number": pit.lap_number,
            "pit_duration": pit.pit_duration,
            "timestamp": pit.timestamp.isoformat(),
        }
        # Check if this pit is already recorded
        if not any(
            p["driver_number"] == pit.driver_number and p["lap_number"] == pit.lap_number
            for p in recent_pits
        ):
            recent_pits.append(pit_record)
    
    # Keep only the 10 most recent
    recent_pits = sorted(recent_pits, key=lambda p: p["timestamp"], reverse=True)[:10]
    
    return state.model_copy(update={"recent_pits": recent_pits})


def apply_race_control(state: RaceState, messages: list[RaceControlMessage]) -> RaceState:
    """
    Apply race control messages to state.
    
    Updates flags, safety car status, and recent messages.
    """
    new_flags = list(state.flags)
    safety_car = state.safety_car
    virtual_safety_car = state.virtual_safety_car
    red_flag = state.red_flag
    
    recent_messages = list(state.recent_messages)
    
    for msg in messages:
        # Update flags based on message
        if msg.flag:
            if msg.flag in ["GREEN", "CLEAR"]:
                new_flags = ["GREEN"]
                safety_car = False
                virtual_safety_car = False
                red_flag = False
            elif msg.flag == "RED":
                new_flags = ["RED"]
                red_flag = True
            elif msg.flag in ["YELLOW", "DOUBLE YELLOW"]:
                if "YELLOW" not in new_flags:
                    new_flags.append("YELLOW")
        
        if msg.category == "SafetyCar":
            if "DEPLOYED" in msg.message.upper():
                safety_car = True
                if "SAFETY CAR" not in new_flags:
                    new_flags.append("SAFETY CAR")
            elif "ENDING" in msg.message.upper() or "IN" in msg.message.upper():
                safety_car = False
                new_flags = [f for f in new_flags if f != "SAFETY CAR"]
        
        if "VSC" in msg.message.upper() or "VIRTUAL SAFETY CAR" in msg.message.upper():
            if "DEPLOYED" in msg.message.upper():
                virtual_safety_car = True
                if "VSC" not in new_flags:
                    new_flags.append("VSC")
            elif "ENDING" in msg.message.upper():
                virtual_safety_car = False
                new_flags = [f for f in new_flags if f != "VSC"]
        
        # Add to recent messages
        msg_record = {
            "category": msg.category,
            "flag": msg.flag,
            "message": msg.message,
            "lap_number": msg.lap_number,
            "timestamp": msg.timestamp.isoformat(),
        }
        recent_messages.append(msg_record)
    
    # Keep only the 20 most recent messages
    recent_messages = sorted(recent_messages, key=lambda m: m["timestamp"], reverse=True)[:20]
    
    return state.model_copy(
        update={
            "flags": new_flags,
            "safety_car": safety_car,
            "virtual_safety_car": virtual_safety_car,
            "red_flag": red_flag,
            "recent_messages": recent_messages,
        }
    )


def apply_update_batch(state: RaceState, batch: UpdateBatch) -> RaceState:
    """
    Apply a complete update batch to state.
    
    This is the main entry point for updating state. It applies all
    non-None fields from the batch in the correct order.
    """
    new_state = state
    
    # Apply updates in order of dependency
    if batch.drivers:
        new_state = apply_drivers(new_state, batch.drivers)
    
    if batch.positions:
        new_state = apply_positions(new_state, batch.positions)
    
    if batch.intervals:
        new_state = apply_intervals(new_state, batch.intervals)
    
    if batch.stints:
        new_state = apply_stints(new_state, batch.stints)
    
    if batch.laps:
        new_state = apply_laps(new_state, batch.laps)
    
    if batch.pits:
        new_state = apply_pits(new_state, batch.pits)
    
    if batch.race_control:
        new_state = apply_race_control(new_state, batch.race_control)
    
    # Update current lap if provided
    if batch.current_lap:
        new_state = new_state.model_copy(
            update={
                "current_lap": max(new_state.current_lap, batch.current_lap),
                "timestamp": batch.timestamp,
            }
        )
    
    return new_state
