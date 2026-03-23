"""
Strategy decision engine.

Evaluates current race state and generates pit stop recommendations
with confidence scores and reasoning.
"""

from dataclasses import dataclass

from rsw.config.constants import (
    CLIFF_RISK_CONFIDENCE_FACTOR,
    COMPOUND_SELECTION_LONG_LAP_THRESHOLD,
    COMPOUND_SELECTION_MED_LAP_THRESHOLD,
    DECISION_PIT_NOW_CONFIDENCE,
    EXTEND_STINT_REMAINING_LAPS,
    EXTEND_STINT_TYRE_AGE,
    QUICK_REC_CONSIDER_PIT_THRESHOLD,
    QUICK_REC_PIT_NOW_CLIFF_THRESHOLD,
    QUICK_REC_STAY_OUT_REMAINING_LAPS,
    SC_PIT_CONFIDENCE,
    TRAFFIC_CONFIDENCE_THRESHOLD,
    TRAFFIC_SEVERITY_MULTIPLIER,
    UNDERCUT_DEG_DELTA,
    UNDERCUT_GAP_BUFFER,
    WEATHER_PACE_DELTA_PIT_THRESHOLD,
)
from rsw.domain import RecommendationType
from rsw.models.physics.pit_traffic_model import PitTrafficModel
from rsw.models.physics.weather_model import (
    WeatherCondition,
    calculate_weather_pace_delta,
    determine_condition,
    should_pit_for_weather,
)

from .pit_window import PitWindow, find_optimal_window, should_pit_now


@dataclass
class PitDecision:
    """A specific pit stop decision."""

    lap: int
    compound_to: str  # Compound to switch to
    expected_positions_lost: int
    expected_time_gain: float
    confidence: float


@dataclass
class StrategyRecommendation:
    """Complete strategy recommendation."""

    driver_number: int
    recommendation: RecommendationType
    confidence: float  # 0-1
    reason: str

    # Window info
    pit_window: PitWindow | None = None

    # Pit decision if pit is recommended
    pit_decision: PitDecision | None = None

    # Threat assessment
    undercut_threat: bool = False
    overcut_opportunity: bool = False

    # Alternative strategies
    alternatives: list[str] | None = None

    # Multi-stop strategy comparison (when optimizer is available)
    multi_stop_comparison: "StrategyComparison | None" = None


def evaluate_strategy(
    driver_number: int,
    current_lap: int,
    total_laps: int,
    current_position: int,
    deg_slope: float,
    cliff_risk: float,
    current_pace: float,
    tyre_age: int,
    compound: str,
    pit_loss: float,
    gap_to_ahead: float | None = None,
    gap_to_behind: float | None = None,
    ahead_deg: float = 0.05,
    behind_deg: float = 0.05,
    safety_car: bool = False,
    cliff_age: int | None = None,
    rain_expected: bool = False,
    rain_laps_away: int | None = None,
    all_drivers: dict | None = None,
    optimizer: "MultiStopOptimizer | None" = None,
    track_priors: dict | None = None,
    compounds_used: list[str] | None = None,
) -> StrategyRecommendation:
    """
    Evaluate strategy and generate recommendation.

    Args:
        driver_number: Driver being evaluated
        current_lap: Current race lap
        total_laps: Total race laps
        current_position: Current position
        deg_slope: Current degradation rate
        cliff_risk: Cliff risk score
        current_pace: Current lap time
        tyre_age: Current tyre age
        compound: Current compound
        pit_loss: Pit stop time loss
        gap_to_ahead: Gap to car in front
        gap_to_behind: Gap to car behind
        ahead_deg: Car ahead's degradation
        behind_deg: Car behind's degradation
        safety_car: Is safety car out
        cliff_age: Lap where cliff is expected
        rain_expected: Is rain forecast during remaining laps
        rain_laps_away: Estimated laps until rain arrives

    Returns:
        StrategyRecommendation
    """
    remaining_laps = total_laps - current_lap

    # Find optimal pit window
    window = find_optimal_window(
        current_lap=current_lap,
        total_laps=total_laps,
        deg_slope=deg_slope,
        current_pace=current_pace,
        pit_loss=pit_loss,
        tyre_age=tyre_age,
        compound=compound,
        cliff_risk=cliff_risk,
        cliff_age=cliff_age,
    )

    # Check if we should pit now
    should_pit, pit_confidence, pit_reason = should_pit_now(
        current_lap=current_lap,
        window=window,
        cliff_risk=cliff_risk,
        undercut_threat=False,  # Will update below
        safety_car=safety_car,
        gap_to_behind=gap_to_behind,
        pit_loss=pit_loss,
    )

    # Assess threats
    undercut_threat = False
    overcut_opportunity = False

    if gap_to_ahead and gap_to_ahead < pit_loss + UNDERCUT_GAP_BUFFER:
        if ahead_deg > deg_slope + UNDERCUT_DEG_DELTA:
            undercut_threat = True

    if gap_to_behind and gap_to_behind < pit_loss:
        if deg_slope < behind_deg - UNDERCUT_DEG_DELTA:
            overcut_opportunity = True

    # Re-evaluate with threat info
    if undercut_threat and not should_pit:
        should_pit, pit_confidence, pit_reason = should_pit_now(
            current_lap=current_lap,
            window=window,
            cliff_risk=cliff_risk,
            undercut_threat=True,
            safety_car=safety_car,
            gap_to_behind=gap_to_behind,
            pit_loss=pit_loss,
        )

    # --- Weather integration (via weather_model) ---
    weather_override = False
    weather_new_compound = compound
    current_condition = WeatherCondition.DRY
    forecast_condition = WeatherCondition.DRY

    if rain_expected:
        # Classify conditions using weather model
        precipitation = 0.0 if not rain_expected else (1.0 if rain_laps_away and rain_laps_away <= 3 else 0.0)
        current_condition = determine_condition(
            precipitation=precipitation,
            precipitation_probability=80.0 if rain_expected else 0.0,
        )
        forecast_condition = WeatherCondition.WET if rain_expected else WeatherCondition.DRY

        # Check pace delta — are we on the wrong tyres?
        pace_delta = calculate_weather_pace_delta(current_condition, compound.upper())
        if pace_delta > WEATHER_PACE_DELTA_PIT_THRESHOLD:
            weather_override = True
            should_pit = True
            pit_confidence = 0.90
            weather_new_compound = "INTERMEDIATE"
            pit_reason = f"Wrong tyres for conditions — {pace_delta:.1f}s/lap penalty"

        # Forecast-based pit decision
        if not weather_override and rain_laps_away is not None:
            should_weather_pit, new_cpd, w_conf = should_pit_for_weather(
                current_compound=compound.upper(),
                current_condition=current_condition,
                forecast_condition=forecast_condition,
                laps_to_change=rain_laps_away,
                remaining_laps=remaining_laps,
            )
            if should_weather_pit:
                weather_override = True
                should_pit = True
                pit_confidence = w_conf
                weather_new_compound = new_cpd
                pit_reason = f"Weather change in ~{rain_laps_away} laps — switch to {new_cpd}"

    # --- Pit traffic estimation ---
    traffic_severity = 0.0
    if all_drivers and should_pit:
        traffic_model = PitTrafficModel(pit_loss=pit_loss)
        driver_gap = 0.0
        driver_data = all_drivers.get(driver_number)
        if driver_data:
            driver_gap = getattr(driver_data, "gap_to_leader", 0.0) or 0.0
        traffic_severity = traffic_model.check_rejoin_traffic(
            exit_lap_time_prediction=driver_gap,
            current_lap=current_lap,
            race_state_drivers=all_drivers,
        )
        # High traffic reduces pit confidence (prefer staying out in traffic)
        if traffic_severity > TRAFFIC_CONFIDENCE_THRESHOLD:
            pit_confidence *= (1.0 - traffic_severity * TRAFFIC_SEVERITY_MULTIPLIER)

    # Determine recommendation type
    if safety_car and window.min_lap <= current_lap <= window.max_lap:
        rec_type = RecommendationType.PIT_NOW
        confidence = SC_PIT_CONFIDENCE
        reason = "Safety car - free pit stop opportunity"
    elif weather_override:
        rec_type = RecommendationType.PIT_NOW
        confidence = pit_confidence
        reason = pit_reason
    elif should_pit:
        if pit_confidence > DECISION_PIT_NOW_CONFIDENCE:
            rec_type = RecommendationType.PIT_NOW
        else:
            rec_type = RecommendationType.CONSIDER_PIT
        confidence = pit_confidence
        reason = pit_reason
    elif remaining_laps <= EXTEND_STINT_REMAINING_LAPS and tyre_age < EXTEND_STINT_TYRE_AGE:
        rec_type = RecommendationType.EXTEND_STINT
        confidence = 0.8
        reason = f"Only {remaining_laps} laps left - no pit needed"
    else:
        rec_type = RecommendationType.STAY_OUT
        confidence = 1.0 - cliff_risk * CLIFF_RISK_CONFIDENCE_FACTOR
        reason = window.reason

    # Build pit decision if pitting
    pit_decision = None
    if rec_type in (RecommendationType.PIT_NOW, RecommendationType.CONSIDER_PIT):
        # Recommend compound based on conditions
        if weather_override:
            new_compound = weather_new_compound
        elif optimizer is not None:
            new_compound = optimizer.get_optimal_compound(
                remaining_laps=remaining_laps,
                stint_number=2,  # Next stint
                compounds_used=compounds_used or [compound],
                track_priors=track_priors,
            )
        elif remaining_laps > COMPOUND_SELECTION_LONG_LAP_THRESHOLD:
            new_compound = "MEDIUM" if compound == "SOFT" else "HARD"
        elif remaining_laps > COMPOUND_SELECTION_MED_LAP_THRESHOLD:
            new_compound = "MEDIUM"
        else:
            new_compound = "SOFT"

        pit_decision = PitDecision(
            lap=current_lap,
            compound_to=new_compound,
            expected_positions_lost=1 if gap_to_behind and gap_to_behind < pit_loss else 0,
            expected_time_gain=deg_slope * 10,  # Rough estimate
            confidence=confidence,
        )

    # Build alternatives
    alternatives = []
    if rec_type == RecommendationType.STAY_OUT:
        alternatives.append(f"Pit on lap {window.ideal_lap} for optimal timing")
    elif rec_type == RecommendationType.PIT_NOW:
        alternatives.append(f"Extend stint to lap {window.max_lap} if needed")
    if rain_expected and not weather_override:
        alternatives.append("Monitor weather — rain may change strategy")

    # Multi-stop comparison (when optimizer is available)
    multi_stop = None
    if optimizer is not None:
        try:
            multi_stop = optimizer.compare_strategies(
                current_lap=current_lap,
                base_pace=current_pace,
                current_compound=compound,
                compounds_used=compounds_used or [compound],
                track_priors=track_priors,
            )
        except Exception:
            pass  # Non-critical — don't break strategy if comparison fails

    return StrategyRecommendation(
        driver_number=driver_number,
        recommendation=rec_type,
        confidence=confidence,
        reason=reason,
        pit_window=window,
        pit_decision=pit_decision,
        undercut_threat=undercut_threat,
        overcut_opportunity=overcut_opportunity,
        alternatives=alternatives,
        multi_stop_comparison=multi_stop,
    )


def get_quick_recommendation(
    cliff_risk: float,
    tyre_age: int,
    remaining_laps: int,
    in_window: bool,
) -> tuple[str, str]:
    """
    Get a quick recommendation for display.

    Returns:
        Tuple of (recommendation, color)
    """
    if cliff_risk > QUICK_REC_PIT_NOW_CLIFF_THRESHOLD:
        return "PIT NOW", "red"

    if remaining_laps <= QUICK_REC_STAY_OUT_REMAINING_LAPS:
        return "STAY OUT", "green"

    if in_window:
        if cliff_risk > QUICK_REC_CONSIDER_PIT_THRESHOLD:
            return "CONSIDER PIT", "yellow"
        return "IN WINDOW", "cyan"

    return "STAY OUT", "green"
