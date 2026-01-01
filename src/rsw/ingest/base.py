"""
Base interface for data providers.

All data adapters must implement this interface to ensure
consistent data formats across different sources.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from pydantic import BaseModel


# ============================================================================
# Data Transfer Objects (DTOs) - canonical format for all data providers
# ============================================================================

class SessionInfo(BaseModel):
    """Session information from a data provider."""
    session_key: int
    meeting_key: int
    session_name: str  # "Race", "Qualifying", "Practice 1", etc.
    session_type: str  # "Race", "Qualifying", "Practice"
    circuit_short_name: str
    country_name: str
    date_start: datetime
    date_end: datetime | None = None
    year: int


class DriverInfo(BaseModel):
    """Driver information from a data provider."""
    driver_number: int
    name_acronym: str  # "VER", "HAM", etc.
    full_name: str
    team_name: str
    team_colour: str  # Hex color code (without #)
    country_code: str
    headshot_url: str | None = None


class LapData(BaseModel):
    """Single lap data from a data provider."""
    driver_number: int
    lap_number: int
    lap_duration: float | None = None
    sector_1: float | None = None
    sector_2: float | None = None
    sector_3: float | None = None
    is_pit_out_lap: bool = False
    speed_trap: int | None = None
    timestamp: datetime | None = None


class PositionData(BaseModel):
    """Position data from a data provider."""
    driver_number: int
    position: int
    timestamp: datetime


class IntervalData(BaseModel):
    """Interval/gap data from a data provider."""
    driver_number: int
    gap_to_leader: float | None = None
    interval: float | None = None  # Gap to car ahead
    timestamp: datetime


class StintData(BaseModel):
    """Stint (tyre) data from a data provider."""
    driver_number: int
    stint_number: int
    compound: str  # "SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"
    lap_start: int
    lap_end: int | None = None
    tyre_age_at_start: int = 0


class PitData(BaseModel):
    """Pit stop data from a data provider."""
    driver_number: int
    lap_number: int
    pit_duration: float  # Total in-pit time in seconds
    timestamp: datetime


class RaceControlMessage(BaseModel):
    """Race control message (flags, SC, etc.)."""
    category: str  # "Flag", "SafetyCar", etc.
    flag: str | None = None  # "GREEN", "YELLOW", "RED", "SC", "VSC"
    message: str
    lap_number: int | None = None
    driver_number: int | None = None
    timestamp: datetime


class UpdateBatch(BaseModel):
    """
    Canonical update batch - the single format all providers must output.
    
    This allows the state store to process updates uniformly regardless
    of whether they come from OpenF1, FastF1, or any other source.
    """
    session_key: int
    timestamp: datetime
    current_lap: int | None = None
    
    # Optional update payloads (only non-None fields are applied)
    drivers: list[DriverInfo] | None = None
    laps: list[LapData] | None = None
    positions: list[PositionData] | None = None
    intervals: list[IntervalData] | None = None
    stints: list[StintData] | None = None
    pits: list[PitData] | None = None
    race_control: list[RaceControlMessage] | None = None


# ============================================================================
# Abstract Base Class
# ============================================================================

class DataProvider(ABC):
    """
    Abstract base class for F1 data providers.
    
    All data adapters (OpenF1, FastF1, etc.) must implement this interface.
    This ensures that the strategy layer never needs to know about specific
    data sources - it only works with the canonical UpdateBatch format.
    """
    
    @abstractmethod
    async def get_sessions(
        self,
        year: int | None = None,
        country: str | None = None,
        session_name: str | None = None,
    ) -> list[SessionInfo]:
        """Fetch available sessions, optionally filtered."""
        pass
    
    @abstractmethod
    async def get_session(self, session_key: int) -> SessionInfo | None:
        """Fetch a specific session by key."""
        pass
    
    @abstractmethod
    async def get_drivers(self, session_key: int) -> list[DriverInfo]:
        """Fetch all drivers for a session."""
        pass
    
    @abstractmethod
    async def get_laps(
        self,
        session_key: int,
        driver_number: int | None = None,
        since_lap: int | None = None,
    ) -> list[LapData]:
        """Fetch lap data, optionally filtered by driver and/or lap number."""
        pass
    
    @abstractmethod
    async def get_positions(self, session_key: int) -> list[PositionData]:
        """Fetch position data for all drivers."""
        pass
    
    @abstractmethod
    async def get_intervals(self, session_key: int) -> list[IntervalData]:
        """Fetch interval/gap data for all drivers."""
        pass
    
    @abstractmethod
    async def get_stints(
        self,
        session_key: int,
        driver_number: int | None = None,
    ) -> list[StintData]:
        """Fetch stint (tyre) data."""
        pass
    
    @abstractmethod
    async def get_pits(self, session_key: int) -> list[PitData]:
        """Fetch pit stop data."""
        pass
    
    @abstractmethod
    async def get_race_control(self, session_key: int) -> list[RaceControlMessage]:
        """Fetch race control messages (flags, SC, etc.)."""
        pass
    
    async def fetch_update_batch(
        self,
        session_key: int,
        since_lap: int | None = None,
        include_drivers: bool = False,
    ) -> UpdateBatch:
        """
        Fetch a complete update batch with all relevant data.
        
        This is a convenience method that calls the individual fetch methods
        and combines the results into a single UpdateBatch.
        """
        from datetime import datetime
        
        batch = UpdateBatch(
            session_key=session_key,
            timestamp=datetime.now(timezone.utc),
        )
        
        if include_drivers:
            batch.drivers = await self.get_drivers(session_key)
        
        batch.laps = await self.get_laps(session_key, since_lap=since_lap)
        batch.positions = await self.get_positions(session_key)
        batch.intervals = await self.get_intervals(session_key)
        batch.stints = await self.get_stints(session_key)
        batch.pits = await self.get_pits(session_key)
        batch.race_control = await self.get_race_control(session_key)
        
        # Determine current lap from lap data
        if batch.laps:
            batch.current_lap = max(lap.lap_number for lap in batch.laps)
        
        return batch
