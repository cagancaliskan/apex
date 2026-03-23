"""
Cached data provider — wraps OpenF1Client with in-memory LRU caching.

Reduces redundant API calls during replay and development sessions.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

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
from rsw.ingest.openf1_client import OpenF1Client


class CachedDataProvider(DataProvider):
    """Data provider that caches OpenF1 responses in memory."""

    def __init__(self, sessions_dir: str | None = None, max_cache: int = 128) -> None:
        self._client = OpenF1Client()
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._max_cache = max_cache

    def _cache_key(self, method: str, **kwargs: Any) -> str:
        parts = [method] + [f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None]
        return "|".join(parts)

    def _get(self, key: str) -> Any | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def _put(self, key: str, value: Any) -> None:
        self._cache[key] = value
        self._cache.move_to_end(key)
        while len(self._cache) > self._max_cache:
            self._cache.popitem(last=False)

    async def get_sessions(
        self, year: int | None = None, country: str | None = None, session_name: str | None = None
    ) -> list[SessionInfo]:
        key = self._cache_key("sessions", year=year, country=country, session_name=session_name)
        cached = self._get(key)
        if cached is not None:
            return cached
        result = await self._client.get_sessions(year=year, country=country, session_name=session_name)
        self._put(key, result)
        return result

    async def get_session(self, session_key: int) -> SessionInfo | None:
        key = self._cache_key("session", session_key=session_key)
        cached = self._get(key)
        if cached is not None:
            return cached
        result = await self._client.get_session(session_key)
        self._put(key, result)
        return result

    async def get_drivers(self, session_key: int) -> list[DriverInfo]:
        key = self._cache_key("drivers", session_key=session_key)
        cached = self._get(key)
        if cached is not None:
            return cached
        result = await self._client.get_drivers(session_key)
        self._put(key, result)
        return result

    async def get_laps(
        self, session_key: int, driver_number: int | None = None, since_lap: int | None = None
    ) -> list[LapData]:
        key = self._cache_key("laps", session_key=session_key, driver_number=driver_number, since_lap=since_lap)
        cached = self._get(key)
        if cached is not None:
            return cached
        result = await self._client.get_laps(session_key, driver_number=driver_number, since_lap=since_lap)
        self._put(key, result)
        return result

    async def get_positions(self, session_key: int) -> list[PositionData]:
        key = self._cache_key("positions", session_key=session_key)
        cached = self._get(key)
        if cached is not None:
            return cached
        result = await self._client.get_positions(session_key)
        self._put(key, result)
        return result

    async def get_intervals(self, session_key: int) -> list[IntervalData]:
        key = self._cache_key("intervals", session_key=session_key)
        cached = self._get(key)
        if cached is not None:
            return cached
        result = await self._client.get_intervals(session_key)
        self._put(key, result)
        return result

    async def get_stints(self, session_key: int, driver_number: int | None = None) -> list[StintData]:
        key = self._cache_key("stints", session_key=session_key, driver_number=driver_number)
        cached = self._get(key)
        if cached is not None:
            return cached
        result = await self._client.get_stints(session_key, driver_number=driver_number)
        self._put(key, result)
        return result

    async def get_pits(self, session_key: int) -> list[PitData]:
        key = self._cache_key("pits", session_key=session_key)
        cached = self._get(key)
        if cached is not None:
            return cached
        result = await self._client.get_pits(session_key)
        self._put(key, result)
        return result

    async def get_race_control(self, session_key: int) -> list[RaceControlMessage]:
        key = self._cache_key("race_control", session_key=session_key)
        cached = self._get(key)
        if cached is not None:
            return cached
        result = await self._client.get_race_control(session_key)
        self._put(key, result)
        return result
