"""
Live Race Mode API routes.

Provides endpoints for starting/stopping live F1 session tracking,
querying live status, and listing active sessions.
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from rsw.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Module-level reference to app state, set during initialization
_app_state: Any = None


def init_live_routes(app_state: Any) -> None:
    """Initialize live routes with application state."""
    global _app_state
    _app_state = app_state


def _get_live_service() -> Any:
    """Get LiveRaceService, creating a fallback for test environments."""
    if _app_state and _app_state.live_service:
        return _app_state.live_service

    # Fallback for test environments where lifespan hasn't run
    from rsw.services.live_race_service import LiveRaceService
    from rsw.ingest.weather_client import WeatherClient
    from rsw.state import RaceStateStore

    class _MinimalState:
        def __init__(self) -> None:
            self.store = RaceStateStore()
            self.speed_multiplier = 1.0
            self.all_driver_telemetry: dict = {}

    class _NoopManager:
        async def broadcast(self, message: dict) -> None:
            pass

    from rsw.ingest import OpenF1Client
    return LiveRaceService(_MinimalState(), _NoopManager(), OpenF1Client(), WeatherClient())


class LiveStartRequest(BaseModel):
    """Request body for starting live tracking."""

    session_key: int | None = None


@router.post("/live/start")
async def start_live(request: LiveStartRequest | None = None) -> dict[str, Any]:
    """
    Start live tracking for an F1 session.

    If session_key is provided, tracks that specific session.
    If omitted, auto-detects the most recent active Race session.
    """
    live_service = _get_live_service()

    # Stop simulation if running (mutual exclusion)
    if _app_state and hasattr(_app_state, 'simulation_service') and _app_state.simulation_service and _app_state.simulation_service.is_running:
        await _app_state.simulation_service.stop()

    session_key = request.session_key if request else None

    if session_key:
        result: dict[str, Any] = cast(dict[str, Any], await live_service.start(session_key))
        if result.get("status") == "error":
            raise HTTPException(404, result.get("detail", "Session not found"))
        return result

    # Auto-detect: find most recent active Race session
    sessions = await live_service.get_active_sessions()
    if not sessions:
        raise HTTPException(404, "No active F1 sessions found")

    # Prefer Race sessions, fall back to any
    race_sessions = [s for s in sessions if s["session_type"] == "Race"]
    target = race_sessions[-1] if race_sessions else sessions[-1]

    result = cast(dict[str, Any], await live_service.start(target["session_key"]))
    if result.get("status") == "error":
        raise HTTPException(404, result.get("detail", "Session not found"))
    return result


@router.post("/live/stop")
async def stop_live() -> dict[str, str]:
    """Stop live tracking."""
    live_service = _get_live_service()
    await live_service.stop()
    return {"status": "stopped"}


@router.get("/live/status")
async def live_status() -> dict[str, Any]:
    """Get current live tracking status."""
    live_service = _get_live_service()
    return cast(dict[str, Any], live_service.get_status())


@router.get("/live/sessions")
async def list_live_sessions() -> dict[str, list[dict[str, Any]]]:
    """List currently active or recent F1 sessions."""
    live_service = _get_live_service()
    sessions = await live_service.get_active_sessions()
    return {"sessions": sessions}
