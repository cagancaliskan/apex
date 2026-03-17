"""
Championship Simulator API routes.

Provides endpoints for multi-race Monte Carlo championship prediction:
- POST /championship/simulate — run full championship simulation
- GET  /championship/calendar/{year} — get season calendar
- GET  /championship/standings/{year}/{up_to_round} — actual standings
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from rsw.logging_config import get_logger
from rsw.services.championship_service import ChampionshipService

logger = get_logger(__name__)

router = APIRouter()

_app_state: Any = None


def init_championship_routes(app_state: Any) -> None:
    """Initialize championship routes with application state."""
    global _app_state
    _app_state = app_state


def _get_service() -> ChampionshipService:
    """Get or create ChampionshipService."""
    return ChampionshipService()


# =============================================================================
# Request/Response Models
# =============================================================================


class SimulateRequest(BaseModel):
    """Championship simulation request."""

    year: int = 2023
    start_from_round: int = 1
    n_simulations: int = Field(default=200, ge=1, le=1000)
    include_sprints: bool = True


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/championship/simulate")
async def simulate_championship(request: SimulateRequest) -> dict[str, Any]:
    """
    Run championship simulation for remaining season.

    This is a long-running endpoint (20-60s depending on params).
    Returns WDC and WCC probability distributions.
    """
    try:
        service = _get_service()
        result = await service.simulate(
            year=request.year,
            start_from_round=request.start_from_round,
            n_simulations=request.n_simulations,
            include_sprints=request.include_sprints,
        )
        return result.model_dump()
    except Exception as e:
        logger.exception("championship_simulation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/championship/calendar/{year}")
async def get_season_calendar(year: int) -> dict[str, Any]:
    """
    Get season calendar with race entries.

    Lightweight endpoint — no simulation, just fetches the schedule.
    """
    try:
        service = _get_service()
        calendar = await service.fetch_calendar(year)
        return {"calendar": [entry.model_dump() for entry in calendar]}
    except Exception as e:
        logger.exception("calendar_fetch_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/championship/standings/{year}/{up_to_round}")
async def get_actual_standings(year: int, up_to_round: int) -> dict[str, Any]:
    """
    Get actual championship standings after a specific round.

    Fetches real results from FastF1.
    """
    try:
        service = _get_service()
        standings = await service.fetch_standings(year, up_to_round)
        drivers = [
            {
                "driver_number": drv,
                "name": info["name"],
                "team": info["team"],
                "points": info["points"],
                "positions": info["positions"],
            }
            for drv, info in sorted(
                standings.items(), key=lambda x: x[1]["points"], reverse=True
            )
        ]
        return {"drivers": drivers}
    except Exception as e:
        logger.exception("standings_fetch_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
