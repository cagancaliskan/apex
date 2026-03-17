"""
Explainability API route.

GET /api/strategy/explain/{driver_number}
Returns structured explainability payload with factor ranking,
sensitivity analysis, and what-if scenarios.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from rsw.config.constants import DEFAULT_PIT_LOSS_SECONDS, DEFAULT_TOTAL_LAPS
from rsw.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Will be set during app startup
_app_state = None

# In-memory cache: {driver_number: (lap_number, timestamp, payload)}
_explain_cache: dict[int, tuple[int, float, dict]] = {}
_CACHE_TTL_SECONDS = 10  # Cache for 10 seconds


def init_explain_routes(app_state: Any) -> None:
    """Initialize with app state reference."""
    global _app_state
    _app_state = app_state


@router.get("/strategy/explain/{driver_number}")
async def get_strategy_explanation(driver_number: int) -> dict[str, Any]:
    """
    Get full explainability payload for a driver's strategy recommendation.

    Returns:
        - strategy: base recommendation with confidence
        - explanation: human-readable text
        - top_factors: ranked list of contributing factors
        - sensitivity: per-parameter sensitivity analysis
        - what_if_scenarios: alternative outcomes
    """
    if _app_state is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Get current race state
    race_state = _app_state.store.get()
    if not race_state or not race_state.drivers:
        raise HTTPException(status_code=404, detail="No active race session")

    driver = race_state.drivers.get(driver_number)
    if driver is None:
        raise HTTPException(status_code=404, detail=f"Driver {driver_number} not found")

    # Check cache — return cached result if same lap and within TTL
    current_lap = race_state.current_lap or 0
    cached = _explain_cache.get(driver_number)
    if cached is not None:
        cached_lap, cached_time, cached_payload = cached
        if cached_lap == current_lap and (time.time() - cached_time) < _CACHE_TTL_SECONDS:
            return {"driver_number": driver_number, **cached_payload}

    try:
        from rsw.strategy.decision import evaluate_strategy
        from rsw.strategy.explain import format_explainability_payload

        # Determine pit loss from track characteristics
        pit_loss = DEFAULT_PIT_LOSS_SECONDS
        cliff_age = None
        sim_service = _app_state.simulation_service
        if sim_service and sim_service._track_characteristics:
            tc = sim_service._track_characteristics
            if tc.pit_stop_count > 0:
                pit_loss = tc.actual_pit_loss_mean
            compound = driver.compound or "MEDIUM"
            cd = tc.compound_degradation.get(compound.upper())
            if cd:
                cliff_age = cd.cliff_lap

        # Evaluate strategy
        logger.debug(
            "explain_inputs",
            driver=driver_number,
            deg_slope=driver.deg_slope,
            cliff_risk=driver.cliff_risk,
            tyre_age=driver.tyre_age,
            pace=driver.last_lap_time,
            lap=race_state.current_lap,
            compound=driver.compound,
            pit_loss=pit_loss,
        )
        rec = evaluate_strategy(
            driver_number=driver.driver_number,
            current_lap=race_state.current_lap or 1,
            total_laps=race_state.total_laps or DEFAULT_TOTAL_LAPS,
            current_position=driver.position or 10,
            deg_slope=driver.deg_slope,
            cliff_risk=driver.cliff_risk,
            current_pace=driver.last_lap_time or 92.0,
            tyre_age=driver.tyre_age,
            compound=driver.compound or "MEDIUM",
            pit_loss=pit_loss,
            gap_to_ahead=driver.gap_to_ahead,
            gap_to_behind=None,
            safety_car=race_state.safety_car,
            cliff_age=cliff_age,
        )

        # Generate full explainability payload
        payload = format_explainability_payload(
            rec=rec,
            driver_number=driver.driver_number,
            current_lap=race_state.current_lap or 1,
            total_laps=race_state.total_laps or DEFAULT_TOTAL_LAPS,
            current_position=driver.position or 10,
            deg_slope=driver.deg_slope,
            cliff_risk=driver.cliff_risk,
            current_pace=driver.last_lap_time or 92.0,
            tyre_age=driver.tyre_age,
            compound=driver.compound or "MEDIUM",
            pit_loss=pit_loss,
            gap_to_ahead=driver.gap_to_ahead,
            gap_to_behind=None,
            safety_car=race_state.safety_car,
            cliff_age=cliff_age,
        )

        # Cache the result
        _explain_cache[driver_number] = (current_lap, time.time(), payload)

        return {"driver_number": driver_number, **payload}

    except Exception as e:
        logger.exception("explain_error", driver=driver_number, error=str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
