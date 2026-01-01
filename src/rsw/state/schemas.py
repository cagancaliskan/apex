"""
Pydantic schemas for canonical race state.

These models represent the "single source of truth" for race state.
All data from different providers is normalized into this format.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class DriverState(BaseModel):
    """
    State for a single driver in the race.
    
    This is the canonical representation of a driver's current state,
    updated as new data arrives from the API.
    """
    # Driver identity
    driver_number: int
    name_acronym: str = ""
    full_name: str = ""
    team_name: str = ""
    team_colour: str = "FFFFFF"
    
    # Position and gaps
    position: int = 0
    gap_to_leader: float | None = None
    gap_to_ahead: float | None = None
    
    # Lap information
    current_lap: int = 0
    last_lap_time: float | None = None
    best_lap_time: float | None = None
    sector_1: float | None = None
    sector_2: float | None = None
    sector_3: float | None = None
    
    # Stint information
    stint_number: int = 1
    compound: str | None = None  # "SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"
    lap_in_stint: int = 0
    stint_start_lap: int = 1
    tyre_age: int = 0
    
    # Degradation model predictions (Phase 2)
    deg_slope: float = 0.0  # Seconds per lap of tyre degradation
    cliff_risk: float = 0.0  # 0-1 score for tyre cliff risk
    predicted_pace: list[float] = Field(default_factory=list)  # Next 5 laps predicted
    model_confidence: float = 0.0  # 0-1 model confidence score
    
    # Strategy recommendations (Phase 3)
    pit_window_min: int = 0
    pit_window_max: int = 0
    pit_window_ideal: int = 0
    pit_recommendation: str = ""  # "PIT_NOW", "STAY_OUT", "CONSIDER_PIT"
    pit_confidence: float = 0.0
    pit_reason: str = ""
    undercut_threat: bool = False
    overcut_opportunity: bool = False
    
    # Status flags
    in_pit: bool = False
    is_pit_out_lap: bool = False
    retired: bool = False
    
    # Last update timestamp
    last_update: datetime | None = None
    
    def model_copy_with_lap(
        self,
        lap_number: int,
        lap_time: float | None = None,
        **kwargs,
    ) -> "DriverState":
        """Create a copy with updated lap data."""
        updates = {
            "current_lap": lap_number,
            "lap_in_stint": lap_number - self.stint_start_lap + 1,
            "tyre_age": self.tyre_age + 1 if lap_number > self.current_lap else self.tyre_age,
            **kwargs,
        }
        
        if lap_time is not None:
            updates["last_lap_time"] = lap_time
            if self.best_lap_time is None or lap_time < self.best_lap_time:
                updates["best_lap_time"] = lap_time
        
        return self.model_copy(update=updates)


class RaceState(BaseModel):
    """
    Complete state for a race session.
    
    This is the top-level state object that contains all driver states
    and session-wide information.
    """
    # Session identification
    session_key: int
    meeting_key: int = 0
    session_name: str = ""
    session_type: str = ""
    
    # Track information  
    track_id: str = ""
    track_name: str = ""
    country: str = ""
    
    # Session progress
    current_lap: int = 0
    total_laps: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Drivers (keyed by driver number)
    drivers: dict[int, DriverState] = Field(default_factory=dict)
    
    # Current flags and status
    flags: list[str] = Field(default_factory=list)  # "GREEN", "YELLOW", "SC", "VSC", "RED"
    safety_car: bool = False
    virtual_safety_car: bool = False
    red_flag: bool = False
    
    # Recent pit events (for display)
    recent_pits: list[dict] = Field(default_factory=list)
    
    # Race control messages (recent)
    recent_messages: list[dict] = Field(default_factory=list)
    
    def get_driver(self, driver_number: int) -> DriverState | None:
        """Get driver state by number."""
        return self.drivers.get(driver_number)
    
    def get_drivers_sorted(self) -> list[DriverState]:
        """Get all drivers sorted by position."""
        return sorted(
            self.drivers.values(),
            key=lambda d: (d.position if d.position > 0 else 999, d.driver_number),
        )
    
    def get_leader(self) -> DriverState | None:
        """Get the race leader."""
        sorted_drivers = self.get_drivers_sorted()
        return sorted_drivers[0] if sorted_drivers else None
    
    def model_copy_with_drivers(self, driver_updates: dict[int, DriverState]) -> "RaceState":
        """Create a copy with updated driver states."""
        new_drivers = {**self.drivers}
        new_drivers.update(driver_updates)
        return self.model_copy(update={"drivers": new_drivers})


class StateSnapshot(BaseModel):
    """
    A serializable snapshot of race state for persistence.
    
    Includes metadata for tracking state history.
    """
    state: RaceState
    snapshot_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    config_hash: str = ""  # Hash of config used to generate this state
    version: str = "1.0"
