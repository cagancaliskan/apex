"""
Mock data provider — returns synthetic data for offline development and testing.

No network calls required. Useful for UI development and unit tests.
"""

from __future__ import annotations

from datetime import UTC, datetime

from rsw.ingest.base import (
    DataProvider,
    DriverInfo,
    IntervalData,
    LapData,
    PitData,
    PositionData,
    RaceControlMessage,
    SessionInfo,
    StintData,
)

_MOCK_DRIVERS = [
    ("VER", "Max Verstappen", "Red Bull Racing", "3671C6", 1),
    ("PER", "Sergio Perez", "Red Bull Racing", "3671C6", 11),
    ("HAM", "Lewis Hamilton", "Ferrari", "E8002D", 44),
    ("LEC", "Charles Leclerc", "Ferrari", "E8002D", 16),
    ("NOR", "Lando Norris", "McLaren", "FF8000", 4),
    ("PIA", "Oscar Piastri", "McLaren", "FF8000", 81),
    ("SAI", "Carlos Sainz", "Williams", "64C4FF", 55),
    ("RUS", "George Russell", "Mercedes", "27F4D2", 63),
]


class MockDataProvider(DataProvider):
    """Synthetic data provider for offline development and testing."""

    def __init__(self) -> None:
        self._session_key = 9999
        self._now = datetime.now(UTC)

    async def get_sessions(
        self, year: int | None = None, country: str | None = None, session_name: str | None = None
    ) -> list[SessionInfo]:
        return [
            SessionInfo(
                session_key=self._session_key,
                meeting_key=1000,
                session_name="Race",
                session_type="Race",
                circuit_short_name="Mock GP",
                country_name="Testland",
                date_start=self._now,
                year=year or 2024,
            )
        ]

    async def get_session(self, session_key: int) -> SessionInfo | None:
        sessions = await self.get_sessions()
        return sessions[0] if sessions else None

    async def get_drivers(self, session_key: int) -> list[DriverInfo]:
        return [
            DriverInfo(
                driver_number=num,
                name_acronym=acr,
                full_name=name,
                team_name=team,
                team_colour=colour,
                country_code="XX",
            )
            for acr, name, team, colour, num in _MOCK_DRIVERS
        ]

    async def get_laps(
        self, session_key: int, driver_number: int | None = None, since_lap: int | None = None
    ) -> list[LapData]:
        laps: list[LapData] = []
        for acr, _, _, _, num in _MOCK_DRIVERS:
            if driver_number is not None and num != driver_number:
                continue
            for lap in range(1, 11):
                if since_lap is not None and lap < since_lap:
                    continue
                base = 90.0 + (num % 10) * 0.1 + lap * 0.03
                laps.append(
                    LapData(
                        driver_number=num,
                        lap_number=lap,
                        lap_duration=base,
                        compound="MEDIUM",
                        tyre_age=lap,
                    )
                )
        return laps

    async def get_positions(self, session_key: int) -> list[PositionData]:
        return [
            PositionData(driver_number=num, position=i + 1, timestamp=self._now)
            for i, (_, _, _, _, num) in enumerate(_MOCK_DRIVERS)
        ]

    async def get_intervals(self, session_key: int) -> list[IntervalData]:
        return [
            IntervalData(
                driver_number=num,
                gap_to_leader=i * 2.5,
                interval=2.5 if i > 0 else 0.0,
                timestamp=self._now,
            )
            for i, (_, _, _, _, num) in enumerate(_MOCK_DRIVERS)
        ]

    async def get_stints(self, session_key: int, driver_number: int | None = None) -> list[StintData]:
        stints: list[StintData] = []
        for _, _, _, _, num in _MOCK_DRIVERS:
            if driver_number is not None and num != driver_number:
                continue
            stints.append(StintData(driver_number=num, stint_number=1, compound="MEDIUM", lap_start=1))
        return stints

    async def get_pits(self, session_key: int) -> list[PitData]:
        return []

    async def get_race_control(self, session_key: int) -> list[RaceControlMessage]:
        return [
            RaceControlMessage(
                category="Flag",
                flag="GREEN",
                message="GREEN FLAG - RACE START",
                lap_number=1,
                timestamp=self._now,
            )
        ]
