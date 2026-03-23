"""
Backtest Service — Alternative Strategy Simulator.

Given a historical race session, a driver, and an alternative pit strategy,
estimates whether the alternative strategy would have produced a better or
worse result using physics-based simulation (TyreModel + FuelModel + TrackModel)
with track-learned priors when available.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rsw.ingest import fastf1_service
from rsw.logging_config import get_logger
from rsw.models.degradation.track_priors import (
    resolve_all_compounds,
    resolve_pit_loss,
)
from rsw.models.physics.track_characteristics import TrackLearner
from rsw.strategy.multi_stop_optimizer import (
    MultiStopOptimizer,
    StintPlan,
    StrategyComparison,
    StrategyPlan,
)

logger = get_logger(__name__)

# Maps strategy string to number of pit stops
STRATEGY_STOPS: dict[str, int] = {
    "1-stop": 1,
    "2-stop": 2,
    "3-stop": 3,
}

# Default compound sequences per stop count (fallback)
_DEFAULT_COMPOUNDS: dict[int, list[str]] = {
    1: ["SOFT", "HARD"],
    2: ["SOFT", "MEDIUM", "HARD"],
    3: ["SOFT", "MEDIUM", "HARD", "MEDIUM"],
}


@dataclass
class BacktestResponse:
    """Result of a single-driver alternative strategy backtest."""

    original_position: int
    alternative_position: int
    position_delta: int       # positive = gained positions
    time_delta: float         # seconds; negative = alternative was faster
    original_strategy: str    # e.g. "2-stop (S-M-H)"
    alternative_strategy: str # e.g. "1-stop (S-H)"
    driver_name: str
    session_name: str
    total_laps: int
    compound_sequence: str = ""  # e.g. "S-H"
    strategy_comparison: dict = field(default_factory=dict)


def _describe_strategy(stints: list) -> str:
    """Build human-readable strategy string like '2-stop (S-M-H)'."""
    stop_count = max(0, len(stints) - 1)
    compounds = [s.compound[0] if s.compound else "?" for s in stints]
    compounds_str = "-".join(compounds)
    return f"{stop_count}-stop ({compounds_str})" if compounds_str else f"{stop_count}-stop"


def _build_actual_strategy(
    driver_stints: list,
    total_laps: int,
) -> StrategyPlan:
    """Build a StrategyPlan from actual historical stints."""
    stints = []
    for s in driver_stints:
        stints.append(StintPlan(
            compound=s.compound or "MEDIUM",
            start_lap=s.lap_start,
            end_lap=s.lap_end if s.lap_end else total_laps,
        ))

    # Ensure last stint reaches end of race
    if stints and stints[-1].end_lap < total_laps:
        stints[-1] = StintPlan(
            compound=stints[-1].compound,
            start_lap=stints[-1].start_lap,
            end_lap=total_laps,
        )

    n_stops = max(0, len(stints) - 1)
    return StrategyPlan(
        n_stops=n_stops,
        stints=stints,
        total_pit_loss=0.0,  # Not needed for actual time (we use real times)
    )


def _build_alternative_strategy(
    alt_stops: int,
    total_laps: int,
    pit_loss: float,
    compounds: list[str] | None = None,
) -> StrategyPlan:
    """Build an evenly-spaced alternative strategy plan."""
    if compounds is None:
        compounds = _DEFAULT_COMPOUNDS.get(alt_stops, ["MEDIUM", "HARD"])

    # Ensure compound count matches stint count
    n_stints = alt_stops + 1
    while len(compounds) < n_stints:
        compounds.append("MEDIUM")
    compounds = compounds[:n_stints]

    # Evenly space pit laps
    interval = total_laps / n_stints
    stints = []
    for i in range(n_stints):
        start = round(interval * i) if i > 0 else 1
        end = round(interval * (i + 1)) if i < n_stints - 1 else total_laps
        stints.append(StintPlan(
            compound=compounds[i],
            start_lap=start,
            end_lap=end,
        ))

    return StrategyPlan(
        n_stops=alt_stops,
        stints=stints,
        total_pit_loss=pit_loss * alt_stops,
    )


async def run_backtest(
    year: int,
    round_number: int,
    driver_acronym: str,
    strategy: str,
    compounds: list[str] | None = None,
) -> BacktestResponse:
    """
    Run a strategy backtest for a single driver.

    Uses physics-based simulation (TyreModel + FuelModel + TrackModel)
    with track-learned priors when available.

    Args:
        year: Season year (e.g. 2023)
        round_number: Round number within the season
        driver_acronym: 3-letter driver code (e.g. "VER")
        strategy: One of "1-stop", "2-stop", "3-stop"
        compounds: Optional compound sequence (e.g. ["SOFT", "HARD"])

    Returns:
        BacktestResponse with actual vs simulated position and time delta
    """
    alt_stops = STRATEGY_STOPS.get(strategy)
    if alt_stops is None:
        raise ValueError(f"Unknown strategy '{strategy}'. Use 1-stop, 2-stop, or 3-stop.")

    # ── Load session ──────────────────────────────────────────────────────────
    logger.info("backtest_loading_session", year=year, round=round_number)
    session = await fastf1_service.get_or_load_session(year, round_number, "R")
    drivers, all_laps, all_stints, all_pits, _ = fastf1_service.extract_race_data(session)

    session_name = getattr(session.event, "EventName", f"{year} Round {round_number}")

    # ── Find the target driver ────────────────────────────────────────────────
    acronym_upper = driver_acronym.upper()
    target = next((d for d in drivers if (d.name_acronym or "").upper() == acronym_upper), None)
    if target is None:
        available = [d.name_acronym for d in drivers]
        raise ValueError(
            f"Driver '{driver_acronym}' not found in {session_name}. "
            f"Available: {available}"
        )

    driver_number = target.driver_number
    actual_position = target.position or 0

    # ── Collect driver's laps and stints ─────────────────────────────────────
    driver_laps = [lap for lap in all_laps if lap.driver_number == driver_number]
    driver_stints = sorted(
        [s for s in all_stints if s.driver_number == driver_number],
        key=lambda s: s.stint_number,
    )

    if not driver_laps:
        raise ValueError(f"No lap data for driver {driver_acronym} in {session_name}")

    total_laps = max(lap.lap_number for lap in driver_laps)

    # ── Actual race time ─────────────────────────────────────────────────────
    valid_lap_times = [lap.lap_duration for lap in driver_laps if lap.lap_duration is not None]
    if not valid_lap_times:
        raise ValueError(f"No valid lap times for driver {driver_acronym}")
    actual_race_time = sum(valid_lap_times)

    # ── Calibrate base pace from session data ────────────────────────────────
    all_valid_times = [
        lap.lap_duration for lap in all_laps
        if lap.lap_duration and 60.0 < lap.lap_duration < 150.0 and not lap.is_pit_out_lap
    ]
    if all_valid_times:
        all_valid_times.sort()
        base_pace = all_valid_times[max(0, len(all_valid_times) // 4)]
    else:
        base_pace = 90.0

    # ── Load track-learned priors ────────────────────────────────────────────
    event = getattr(session, "event", None)
    circuit_key = (getattr(event, "Location", "unknown").lower().replace(" ", "_"))

    track_learner = TrackLearner()
    track_chars = track_learner.load(circuit_key)
    resolved_priors = resolve_all_compounds(track_chars=track_chars)
    pit_loss = resolve_pit_loss(track_chars)

    # ── Create optimizer ─────────────────────────────────────────────────────
    optimizer = MultiStopOptimizer(pit_loss=pit_loss, total_laps=total_laps)

    # ── Build actual strategy plan and simulate ──────────────────────────────
    actual_plan = _build_actual_strategy(driver_stints, total_laps)
    actual_sim_time = optimizer.simulate_strategy(actual_plan, base_pace, resolved_priors)

    # ── Build and simulate alternative strategy ──────────────────────────────
    alt_plan = _build_alternative_strategy(alt_stops, total_laps, pit_loss, compounds)
    alt_sim_time = optimizer.simulate_strategy(alt_plan, base_pace, resolved_priors)

    # ── Time delta (physics-based) ───────────────────────────────────────────
    # Delta = how much slower/faster the alternative is vs actual
    sim_delta = alt_sim_time - actual_sim_time
    simulated_race_time = actual_race_time + sim_delta

    # ── Infer simulated position ─────────────────────────────────────────────
    race_times: dict[int, float] = {}
    for d in drivers:
        d_laps = [lap.lap_duration for lap in all_laps
                  if lap.driver_number == d.driver_number and lap.lap_duration is not None]
        if d_laps:
            race_times[d.driver_number] = sum(d_laps)

    race_times[driver_number] = simulated_race_time

    sorted_drivers = sorted(race_times.items(), key=lambda kv: kv[1])
    simulated_position = next(
        (i + 1 for i, (dn, _) in enumerate(sorted_drivers) if dn == driver_number),
        actual_position,
    )

    position_delta = actual_position - simulated_position

    # ── Full strategy comparison ─────────────────────────────────────────────
    comparison = optimizer.compare_strategies(
        current_lap=1,
        base_pace=base_pace,
        current_compound=driver_stints[0].compound if driver_stints else "MEDIUM",
        track_priors=resolved_priors,
    )
    comparison_dict = _comparison_to_dict(comparison)

    # ── Strategy description ─────────────────────────────────────────────────
    original_strategy_str = _describe_strategy(driver_stints) if driver_stints else f"{len(driver_stints)-1}-stop"
    alt_seq = "-".join(s.compound[0] for s in alt_plan.stints)
    alt_strategy_str = f"{alt_stops}-stop ({alt_seq})"

    logger.info(
        "backtest_complete",
        driver=driver_acronym,
        original_pos=actual_position,
        simulated_pos=simulated_position,
        time_delta=round(sim_delta, 2),
        pit_loss=round(pit_loss, 1),
        priors_source=resolved_priors.get("SOFT", None) and resolved_priors["SOFT"].source,
    )

    return BacktestResponse(
        original_position=actual_position,
        alternative_position=simulated_position,
        position_delta=position_delta,
        time_delta=round(sim_delta, 2),
        original_strategy=original_strategy_str,
        alternative_strategy=alt_strategy_str,
        driver_name=target.full_name or driver_acronym,
        session_name=session_name,
        total_laps=total_laps,
        compound_sequence=alt_seq,
        strategy_comparison=comparison_dict,
    )


def _comparison_to_dict(comparison: StrategyComparison) -> dict:
    """Serialize StrategyComparison for API response."""
    return {
        "recommended": {
            "stops": comparison.recommended.n_stops,
            "sequence": comparison.recommended.compound_sequence,
            "time": round(comparison.recommended.estimated_race_time, 1),
            "confidence": round(comparison.recommended.confidence, 2),
        },
        "reason": comparison.recommendation_reason,
        "alternatives": {k: v for k, v in comparison.time_deltas.items()},
    }
