"""
Simulation API Routes.

Endpoints for controlling race simulation playback and data loading.

Endpoints:
    POST /simulation/load/{year}/{round} - Load and start simulation
    POST /simulation/stop - Stop current simulation
    POST /simulation/speed/{speed} - Set playback speed
    GET /simulation/status - Get simulation status
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException

from rsw.logging_config import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

router = APIRouter(prefix="/simulation", tags=["simulation"])


# Module-level reference to app state (set during app initialization)
_app_state: Any = None


def init_simulation_routes(app_state: Any) -> None:
    """
    Initialize simulation routes with application state.

    Must be called during application startup.

    Args:
        app_state: Application state container with simulation_service
    """
    global _app_state
    _app_state = app_state


@router.post("/load/{year}/{round_num}")
async def load_race(year: int, round_num: int) -> dict[str, Any]:
    """
    Load and start simulation for a race session.

    Args:
        year: Season year (2018-2024)
        round_num: Championship round number (1-24)

    Returns:
        Status message with session details

    Raises:
        HTTPException: 400 if invalid parameters
        HTTPException: 500 if simulation service unavailable
    """
    if _app_state is None or _app_state.simulation_service is None:
        raise HTTPException(status_code=500, detail="Simulation service not initialized")

    if year < 2018 or year > 2030:
        raise HTTPException(
            status_code=400, detail=f"Invalid year: {year}. Must be between 2018 and 2030"
        )

    if round_num < 1 or round_num > 24:
        raise HTTPException(
            status_code=400, detail=f"Invalid round: {round_num}. Must be between 1 and 24"
        )

    logger.info("simulation_load_requested", year=year, round=round_num)

    await _app_state.simulation_service.start(year, round_num)

    return {
        "status": "ok",
        "message": f"Started simulation for {year} Round {round_num}",
        "year": year,
        "round": round_num,
    }


@router.post("/stop")
async def stop_simulation() -> dict[str, str]:
    """
    Stop the current simulation.

    Returns:
        Status confirmation
    """
    if _app_state is None or _app_state.simulation_service is None:
        raise HTTPException(status_code=500, detail="Simulation service not initialized")

    await _app_state.simulation_service.stop()
    logger.info("simulation_stopped_via_api")

    return {"status": "ok", "message": "Simulation stopped"}


@router.post("/speed/{speed}")
async def set_speed(speed: float) -> dict[str, Any]:
    """
    Set simulation playback speed.

    Args:
        speed: Playback multiplier (0.1 to 100)

    Returns:
        Confirmation with new speed value

    Raises:
        HTTPException: 400 if speed out of valid range
    """
    if speed < 0.1 or speed > 100:
        raise HTTPException(status_code=400, detail="Speed must be between 0.1 and 100")

    if _app_state is not None:
        _app_state.speed_multiplier = speed

    return {"status": "ok", "speed": speed}


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """
    Get current simulation status.

    Returns:
        Current simulation state including running status and progress
    """
    if _app_state is None:
        return {
            "status": "not_initialized",
            "running": False,
        }

    state = _app_state.store.get()

    return {
        "status": "ok",
        "running": _app_state.simulation_service.is_running
        if _app_state.simulation_service
        else False,
        "current_lap": state.current_lap,
        "total_laps": state.total_laps,
        "session_name": state.session_name,
        "speed": _app_state.speed_multiplier,
    }
