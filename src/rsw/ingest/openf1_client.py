"""
OpenF1 API client for fetching F1 timing data.

This client uses the public OpenF1 API for historical data.
Real-time data requires a paid subscription.

API Documentation: https://openf1.org
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx

from ..config import load_app_config
from .base import (
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


class OpenF1Client(DataProvider):
    """
    HTTP client for the OpenF1 API.

    This implements the DataProvider interface, translating OpenF1 responses
    into the canonical data format used by the rest of the application.
    """

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        """Initialize the client with optional custom settings."""
        config = load_app_config()
        self.base_url = base_url or config.openf1.base_url
        self.timeout = timeout or config.openf1.timeout_seconds
        self._client: httpx.AsyncClient | None = None
        self._cache: dict[str, tuple[datetime, Any]] = {}
        self._cache_ttl = config.polling.cache_ttl_seconds

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _fetch(self, endpoint: str, params: dict | None = None) -> list[dict[str, Any]]:
        """Fetch data from OpenF1 API with caching and retries."""
        # Check cache
        cache_key = f"{endpoint}:{str(sorted(params.items())) if params else ''}"
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            from typing import cast

            if (datetime.now(UTC) - cached_time).total_seconds() < self._cache_ttl:
                return cast(list[dict[str, Any]], cached_data)

        # Make request with retries
        client = await self._get_client()
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                response = await client.get(endpoint, params=params, timeout=10.0)

                # Handle 429 Rate Limit explicitly
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    print(f"Rate limited on {endpoint}. Retrying after {retry_after}s...")
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                data = response.json()

                # Update cache
                self._cache[cache_key] = (datetime.now(UTC), data)

                return data if isinstance(data, list) else []

            except httpx.HTTPStatusError as e:
                print(f"HTTP error fetching {endpoint} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return []
            except httpx.RequestError as e:
                print(
                    f"Request error fetching {endpoint} (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt == max_retries - 1:
                    return []
            except Exception as e:
                print(f"Unexpected error fetching {endpoint}: {e}")
                return []

            # Exponential backoff for retries
            await asyncio.sleep(base_delay * (2**attempt))

        return []

    def _parse_datetime(self, dt_str: str | None) -> datetime | None:
        """Parse ISO datetime string from API."""
        if not dt_str:
            return None
        try:
            # Handle various ISO formats
            dt_str = dt_str.replace("Z", "+00:00")
            return datetime.fromisoformat(dt_str)
        except ValueError:
            return None

    # ========================================================================
    # DataProvider interface implementation
    # ========================================================================

    async def get_sessions(
        self,
        year: int | None = None,
        country: str | None = None,
        session_name: str | None = None,
    ) -> list[SessionInfo]:
        """Fetch available sessions."""
        params: dict[str, Any] = {}
        if year:
            params["year"] = year
        if country:
            params["country_name"] = country
        if session_name:
            params["session_name"] = session_name

        data = await self._fetch("/sessions", params)

        sessions = []
        for item in data:
            try:
                session = SessionInfo(
                    session_key=item["session_key"],
                    meeting_key=item["meeting_key"],
                    session_name=item["session_name"],
                    session_type=item.get("session_type", item["session_name"]),
                    circuit_short_name=item["circuit_short_name"],
                    country_name=item["country_name"],
                    date_start=self._parse_datetime(item["date_start"])
                    or datetime.now(UTC),
                    date_end=self._parse_datetime(item.get("date_end")),
                    year=item["year"],
                )
                sessions.append(session)
            except (KeyError, ValueError) as e:
                print(f"Error parsing session: {e}")
                continue

        return sessions

    async def get_session(self, session_key: int) -> SessionInfo | None:
        """Fetch a specific session by key."""
        params = {"session_key": session_key}
        data = await self._fetch("/sessions", params)

        if not data:
            return None

        item = data[0]
        try:
            return SessionInfo(
                session_key=item["session_key"],
                meeting_key=item["meeting_key"],
                session_name=item["session_name"],
                session_type=item.get("session_type", item["session_name"]),
                circuit_short_name=item["circuit_short_name"],
                country_name=item["country_name"],
                date_start=self._parse_datetime(item["date_start"]) or datetime.now(UTC),
                date_end=self._parse_datetime(item.get("date_end")),
                year=item["year"],
            )
        except (KeyError, ValueError):
            return None

    async def get_drivers(self, session_key: int) -> list[DriverInfo]:
        """Fetch all drivers for a session."""
        params = {"session_key": session_key}
        data = await self._fetch("/drivers", params)

        drivers = []
        for item in data:
            try:
                driver = DriverInfo(
                    driver_number=item["driver_number"],
                    name_acronym=item["name_acronym"],
                    full_name=item["full_name"],
                    team_name=item["team_name"],
                    team_colour=item.get("team_colour", "FFFFFF"),
                    country_code=item.get("country_code", ""),
                    headshot_url=item.get("headshot_url"),
                )
                drivers.append(driver)
            except (KeyError, ValueError) as e:
                print(f"Error parsing driver: {e}")
                continue

        return drivers

    async def get_laps(
        self,
        session_key: int,
        driver_number: int | None = None,
        since_lap: int | None = None,
    ) -> list[LapData]:
        """Fetch lap data."""
        params: dict[str, Any] = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        if since_lap:
            params["lap_number>"] = since_lap

        data = await self._fetch("/laps", params)

        laps = []
        for item in data:
            try:
                lap = LapData(
                    driver_number=item["driver_number"],
                    lap_number=item["lap_number"],
                    lap_duration=item.get("lap_duration"),
                    sector_1=item.get("duration_sector_1"),
                    sector_2=item.get("duration_sector_2"),
                    sector_3=item.get("duration_sector_3"),
                    is_pit_out_lap=item.get("is_pit_out_lap", False),
                    speed_trap=item.get("st_speed"),
                    timestamp=self._parse_datetime(item.get("date_start")),
                )
                laps.append(lap)
            except (KeyError, ValueError) as e:
                print(f"Error parsing lap: {e}")
                continue

        return laps

    async def get_positions(self, session_key: int) -> list[PositionData]:
        """Fetch position data."""
        params = {"session_key": session_key}
        data = await self._fetch("/position", params)

        # OpenF1 returns multiple position entries per driver (one per change)
        # We want the most recent position for each driver
        latest_positions: dict[int, PositionData] = {}

        for item in data:
            try:
                driver_num = item["driver_number"]
                timestamp = self._parse_datetime(item["date"])

                if timestamp is None:
                    continue

                position = PositionData(
                    driver_number=driver_num,
                    position=item["position"],
                    timestamp=timestamp,
                )

                # Keep only the latest position for each driver
                if (
                    driver_num not in latest_positions
                    or timestamp > latest_positions[driver_num].timestamp
                ):
                    latest_positions[driver_num] = position

            except (KeyError, ValueError) as e:
                print(f"Error parsing position: {e}")
                continue

        return list(latest_positions.values())

    async def get_intervals(self, session_key: int) -> list[IntervalData]:
        """Fetch interval/gap data."""
        params = {"session_key": session_key}
        data = await self._fetch("/intervals", params)

        # Get most recent interval for each driver
        latest_intervals: dict[int, IntervalData] = {}

        for item in data:
            try:
                driver_num = item["driver_number"]
                timestamp = self._parse_datetime(item["date"])

                if timestamp is None:
                    continue

                interval = IntervalData(
                    driver_number=driver_num,
                    gap_to_leader=item.get("gap_to_leader"),
                    interval=item.get("interval"),
                    timestamp=timestamp,
                )

                if (
                    driver_num not in latest_intervals
                    or timestamp > latest_intervals[driver_num].timestamp
                ):
                    latest_intervals[driver_num] = interval

            except (KeyError, ValueError) as e:
                print(f"Error parsing interval: {e}")
                continue

        return list(latest_intervals.values())

    async def get_stints(
        self,
        session_key: int,
        driver_number: int | None = None,
    ) -> list[StintData]:
        """Fetch stint (tyre) data."""
        params: dict[str, Any] = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number

        data = await self._fetch("/stints", params)

        stints = []
        for item in data:
            try:
                stint = StintData(
                    driver_number=item["driver_number"],
                    stint_number=item["stint_number"],
                    compound=item["compound"],
                    lap_start=item["lap_start"],
                    lap_end=item.get("lap_end"),
                    tyre_age_at_start=item.get("tyre_age_at_start", 0),
                )
                stints.append(stint)
            except (KeyError, ValueError) as e:
                print(f"Error parsing stint: {e}")
                continue

        return stints

    async def get_pits(self, session_key: int) -> list[PitData]:
        """Fetch pit stop data."""
        params = {"session_key": session_key}
        data = await self._fetch("/pit", params)

        pits = []
        for item in data:
            try:
                pit = PitData(
                    driver_number=item["driver_number"],
                    lap_number=item["lap_number"],
                    pit_duration=item["pit_duration"],
                    timestamp=self._parse_datetime(item["date"]) or datetime.now(UTC),
                )
                pits.append(pit)
            except (KeyError, ValueError) as e:
                print(f"Error parsing pit: {e}")
                continue

        return pits

    async def get_race_control(self, session_key: int) -> list[RaceControlMessage]:
        """Fetch race control messages."""
        params = {"session_key": session_key}
        data = await self._fetch("/race_control", params)

        messages = []
        for item in data:
            try:
                msg = RaceControlMessage(
                    category=item["category"],
                    flag=item.get("flag"),
                    message=item["message"],
                    lap_number=item.get("lap_number"),
                    driver_number=item.get("driver_number"),
                    timestamp=self._parse_datetime(item["date"]) or datetime.now(UTC),
                )
                messages.append(msg)
            except (KeyError, ValueError) as e:
                print(f"Error parsing race control: {e}")
                continue

        return messages


# Convenience function for quick testing
async def test_client() -> None:
    """Test the OpenF1 client with a sample session."""
    client = OpenF1Client()

    try:
        # Get 2023 sessions
        print("Fetching 2023 sessions...")
        sessions = await client.get_sessions(year=2023)
        print(f"Found {len(sessions)} sessions")

        if sessions:
            # Get details for the first race session
            race_sessions = [s for s in sessions if s.session_name == "Race"]
            if race_sessions:
                session = race_sessions[0]
                print(f"\nSession: {session.country_name} {session.session_name}")

                # Get drivers
                drivers = await client.get_drivers(session.session_key)
                print(f"Drivers: {len(drivers)}")

                # Get some laps
                laps = await client.get_laps(session.session_key)
                print(f"Laps: {len(laps)}")

                # Get stints
                stints = await client.get_stints(session.session_key)
                print(f"Stints: {len(stints)}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_client())
