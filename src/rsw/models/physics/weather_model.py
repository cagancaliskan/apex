"""
Weather Impact Model.

Models how weather conditions affect race strategy:
- Tyre compound selection
- Pace deltas
- Track evolution

Design: Pure functions, no side effects.
"""

from dataclasses import dataclass
from enum import Enum

from rsw.config.constants import (
    WEATHER_CONDITION_CHANGE_LAPS,
    WEATHER_DRYING_PIT_LAPS,
    WEATHER_PACE_DELTA_PIT_THRESHOLD,
    WEATHER_RAIN_PREP_LAPS,
    WEATHER_RAIN_PROBABLE_PCT,
    WEATHER_SC_MULTIPLIERS,
    WEATHER_SC_PROBABILITY_CAP,
    WEATHER_VERY_WET_MM,
    WEATHER_WET_MM,
)


class WeatherCondition(Enum):
    """Track surface condition."""

    DRY = "dry"
    DAMP = "damp"  # Drying or light drizzle
    WET = "wet"  # Steady rain
    VERY_WET = "very_wet"  # Heavy rain, SC likely


@dataclass
class WeatherState:
    """Current weather state for strategy decisions."""

    condition: WeatherCondition
    rain_probability: float  # 0-100
    track_temperature: float  # Celsius
    air_temperature: float  # Celsius

    @property
    def requires_wets(self) -> bool:
        """Conditions require wet tyres."""
        return self.condition in (WeatherCondition.WET, WeatherCondition.VERY_WET)

    @property
    def inters_viable(self) -> bool:
        """Intermediate tyres are optimal."""
        return self.condition == WeatherCondition.DAMP

    @property
    def rain_likely_soon(self) -> bool:
        """Rain is likely in the next 30 minutes."""
        return self.rain_probability >= WEATHER_RAIN_PROBABLE_PCT


# Compound performance in different conditions
# Values are lap time delta vs optimal compound (negative = faster)
COMPOUND_WEATHER_DELTA: dict[WeatherCondition, dict[str, float]] = {
    WeatherCondition.DRY: {
        "SOFT": 0.0,
        "MEDIUM": 0.6,
        "HARD": 1.2,
        "INTERMEDIATE": 8.0,  # Way too slow
        "WET": 15.0,  # Undriveable
    },
    WeatherCondition.DAMP: {
        "SOFT": 3.0,  # Slicks struggle
        "MEDIUM": 2.5,
        "HARD": 2.0,  # Harder slicks slightly better
        "INTERMEDIATE": 0.0,  # Optimal
        "WET": 2.5,  # Slight overheat
    },
    WeatherCondition.WET: {
        "SOFT": 10.0,  # Dangerous
        "MEDIUM": 8.0,
        "HARD": 7.0,
        "INTERMEDIATE": 1.5,  # Bit slow but safe
        "WET": 0.0,  # Optimal
    },
    WeatherCondition.VERY_WET: {
        "SOFT": 15.0,  # Undriveable
        "MEDIUM": 12.0,
        "HARD": 10.0,
        "INTERMEDIATE": 4.0,
        "WET": 0.0,  # Only option
    },
}


def get_optimal_compound(condition: WeatherCondition) -> str:
    """Get the optimal compound for current conditions."""
    if condition == WeatherCondition.DRY:
        return "SOFT"  # Could also be MEDIUM depending on track
    elif condition == WeatherCondition.DAMP:
        return "INTERMEDIATE"
    elif condition in (WeatherCondition.WET, WeatherCondition.VERY_WET):
        return "WET"
    return "MEDIUM"


def calculate_weather_pace_delta(
    condition: WeatherCondition,
    compound: str,
) -> float:
    """
    Calculate pace delta for running a compound in given conditions.

    Returns:
        Seconds per lap slower than optimal. 0 = optimal choice.
    """
    deltas = COMPOUND_WEATHER_DELTA.get(condition, COMPOUND_WEATHER_DELTA[WeatherCondition.DRY])
    return deltas.get(compound.upper(), 5.0)


def determine_condition(
    precipitation: float,
    precipitation_probability: float,
    track_wet: bool = False,
) -> WeatherCondition:
    """
    Determine weather condition from weather data.

    Args:
        precipitation: Current precipitation in mm
        precipitation_probability: Probability of rain (0-100)
        track_wet: Whether track is currently wet from earlier rain
    """
    if precipitation >= WEATHER_VERY_WET_MM:
        return WeatherCondition.VERY_WET
    elif precipitation >= WEATHER_WET_MM:
        return WeatherCondition.WET
    elif precipitation > 0 or track_wet:
        return WeatherCondition.DAMP
    return WeatherCondition.DRY


def should_pit_for_weather(
    current_compound: str,
    current_condition: WeatherCondition,
    forecast_condition: WeatherCondition,
    laps_to_change: int,
    remaining_laps: int,
) -> tuple[bool, str, float]:
    """
    Determine if driver should pit for weather change.

    Args:
        current_compound: Current tyre
        current_condition: Current track condition
        forecast_condition: Expected condition soon
        laps_to_change: Estimated laps until condition changes
        remaining_laps: Laps remaining in race

    Returns:
        Tuple of (should_pit, new_compound, confidence)
    """
    optimal_current = get_optimal_compound(current_condition)
    optimal_forecast = get_optimal_compound(forecast_condition)

    # Calculate current pace delta
    current_delta = calculate_weather_pace_delta(current_condition, current_compound)

    # If already on wrong tyres, pit now
    if current_delta > WEATHER_PACE_DELTA_PIT_THRESHOLD:
        return True, optimal_current, 0.9

    # If conditions changing soon
    if forecast_condition != current_condition and laps_to_change <= WEATHER_CONDITION_CHANGE_LAPS:
        if optimal_forecast != current_compound:
            # Prepare for condition change
            return True, optimal_forecast, 0.75

    # Rain coming and on slicks
    if forecast_condition in (WeatherCondition.WET, WeatherCondition.VERY_WET):
        if current_compound in ("SOFT", "MEDIUM", "HARD"):
            if laps_to_change <= WEATHER_RAIN_PREP_LAPS:
                return True, "INTERMEDIATE", 0.8

    # Drying out - opportunity to switch from wets
    if current_condition == WeatherCondition.DAMP and forecast_condition == WeatherCondition.DRY:
        if current_compound == "INTERMEDIATE":
            if laps_to_change <= WEATHER_DRYING_PIT_LAPS:
                return True, "SOFT", 0.7

    return False, current_compound, 0.5


def calculate_sc_probability_adjustment(
    base_probability: float,
    condition: WeatherCondition,
) -> float:
    """
    Adjust safety car probability for weather conditions.

    Wet conditions increase incident likelihood.
    """
    multiplier = WEATHER_SC_MULTIPLIERS.get(condition.value.upper(), 1.0)
    adjusted = base_probability * multiplier

    return min(WEATHER_SC_PROBABILITY_CAP, adjusted)
