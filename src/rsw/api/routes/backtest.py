"""
Backtest API routes.

Provides the POST /api/backtest/run endpoint that runs an alternative strategy
simulation against a historical race session.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from rsw.logging_config import get_logger
from rsw.services.backtest_service import BacktestResponse, run_backtest

logger = get_logger(__name__)

router = APIRouter()


class BacktestRequest(BaseModel):
    year: int = Field(..., ge=2018, le=2030, description="Season year")
    round: int = Field(..., ge=1, le=24, description="Round number within the season")
    driver_acronym: str = Field(..., min_length=2, max_length=4, description="3-letter driver code")
    strategy: str = Field(..., description="Alternative strategy: '1-stop', '2-stop', or '3-stop'")
    compounds: list[str] | None = Field(None, description="Optional compound sequence (e.g. ['SOFT', 'HARD'])")


class BacktestResponseModel(BaseModel):
    original_position: int
    alternative_position: int
    position_delta: int
    time_delta: float
    original_strategy: str
    alternative_strategy: str
    driver_name: str
    session_name: str
    total_laps: int
    compound_sequence: str | None = None
    strategy_comparison: dict | None = None


@router.post("/run", response_model=BacktestResponseModel)
async def run_backtest_endpoint(request: BacktestRequest) -> BacktestResponseModel:
    """
    Run a strategy backtest for a single driver on a historical race.

    Loads the specified race session from FastF1, finds the driver's actual
    result, and estimates how the alternative strategy would have changed
    their finishing position and total race time.
    """
    logger.info(
        "backtest_request",
        year=request.year,
        round=request.round,
        driver=request.driver_acronym,
        strategy=request.strategy,
    )

    try:
        result: BacktestResponse = await run_backtest(
            year=request.year,
            round_number=request.round,
            driver_acronym=request.driver_acronym,
            strategy=request.strategy,
            compounds=request.compounds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("backtest_unexpected_error", error=str(exc))
        raise HTTPException(status_code=500, detail="Backtest failed — see server logs") from exc

    return BacktestResponseModel(
        original_position=result.original_position,
        alternative_position=result.alternative_position,
        position_delta=result.position_delta,
        time_delta=result.time_delta,
        original_strategy=result.original_strategy,
        alternative_strategy=result.alternative_strategy,
        driver_name=result.driver_name,
        session_name=result.session_name,
        total_laps=result.total_laps,
        compound_sequence=result.compound_sequence or None,
        strategy_comparison=result.strategy_comparison or None,
    )
