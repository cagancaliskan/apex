"""
Team Strategy Profiles.

Defines strategy tendencies for each F1 team based on historical patterns.
Used by CompetitorAI to make realistic pit stop predictions.

Design: KISS - Simple dataclass with sensible defaults, no complex inheritance.
"""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class TeamProfile:
    """
    Strategy profile for an F1 team.

    All values are normalized 0.0-1.0 where:
    - 0.0 = Never/Low tendency
    - 0.5 = Average/Neutral
    - 1.0 = Always/High tendency
    """

    team_name: str

    # Pit timing tendencies
    early_stopper_bias: float = 0.5  # 1.0 = always pits early
    extend_stint_tendency: float = 0.5  # 1.0 = pushes tyres to limit

    # Compound selection
    conservative_compound: float = 0.5  # 1.0 = always picks harder compound
    soft_start_preference: float = 0.5  # 1.0 = always starts on softs

    # Tactical aggression
    undercut_tendency: float = 0.5  # 1.0 = always tries undercut
    overcut_tendency: float = 0.5  # 1.0 = prefers overcut

    # Event reactions
    safety_car_opportunism: float = 0.5  # 1.0 = always pits under SC
    weather_gamble_tendency: float = 0.5  # 1.0 = aggressive on weather calls

    # Two-stop vs one-stop
    multi_stop_preference: float = 0.5  # 1.0 = prefers 2-stop strategies


# =============================================================================
# Team Profiles (2023-2024 data-informed estimates)
# =============================================================================

TEAM_PROFILES: dict[str, TeamProfile] = {
    # Red Bull - Dominant, conservative when leading
    "Red Bull Racing": TeamProfile(
        team_name="Red Bull Racing",
        early_stopper_bias=0.4,
        extend_stint_tendency=0.7,
        conservative_compound=0.6,
        soft_start_preference=0.4,
        undercut_tendency=0.5,
        overcut_tendency=0.6,
        safety_car_opportunism=0.8,
        weather_gamble_tendency=0.4,
        multi_stop_preference=0.3,
    ),
    # Mercedes - Flexible, adapts to race
    "Mercedes": TeamProfile(
        team_name="Mercedes",
        early_stopper_bias=0.5,
        extend_stint_tendency=0.5,
        conservative_compound=0.5,
        soft_start_preference=0.5,
        undercut_tendency=0.6,
        overcut_tendency=0.5,
        safety_car_opportunism=0.7,
        weather_gamble_tendency=0.5,
        multi_stop_preference=0.4,
    ),
    # Ferrari - Historically aggressive, sometimes(!) chaotic
    "Ferrari": TeamProfile(
        team_name="Ferrari",
        early_stopper_bias=0.6,
        extend_stint_tendency=0.4,
        conservative_compound=0.4,
        soft_start_preference=0.7,
        undercut_tendency=0.7,
        overcut_tendency=0.3,
        safety_car_opportunism=0.6,
        weather_gamble_tendency=0.6,
        multi_stop_preference=0.5,
    ),
    # McLaren - Calculated, data-driven
    "McLaren": TeamProfile(
        team_name="McLaren",
        early_stopper_bias=0.5,
        extend_stint_tendency=0.6,
        conservative_compound=0.5,
        soft_start_preference=0.5,
        undercut_tendency=0.6,
        overcut_tendency=0.5,
        safety_car_opportunism=0.7,
        weather_gamble_tendency=0.4,
        multi_stop_preference=0.4,
    ),
    # Aston Martin - Conservative approach
    "Aston Martin": TeamProfile(
        team_name="Aston Martin",
        early_stopper_bias=0.4,
        extend_stint_tendency=0.6,
        conservative_compound=0.7,
        soft_start_preference=0.3,
        undercut_tendency=0.4,
        overcut_tendency=0.6,
        safety_car_opportunism=0.7,
        weather_gamble_tendency=0.3,
        multi_stop_preference=0.3,
    ),
    # Alpine - Aggressive midfield fighter
    "Alpine": TeamProfile(
        team_name="Alpine",
        early_stopper_bias=0.6,
        extend_stint_tendency=0.4,
        conservative_compound=0.4,
        soft_start_preference=0.6,
        undercut_tendency=0.7,
        overcut_tendency=0.4,
        safety_car_opportunism=0.8,
        weather_gamble_tendency=0.6,
        multi_stop_preference=0.5,
    ),
    # Williams - Risk-taker in midfield battles
    "Williams": TeamProfile(
        team_name="Williams",
        early_stopper_bias=0.5,
        extend_stint_tendency=0.5,
        conservative_compound=0.5,
        soft_start_preference=0.5,
        undercut_tendency=0.6,
        overcut_tendency=0.5,
        safety_car_opportunism=0.8,
        weather_gamble_tendency=0.7,
        multi_stop_preference=0.4,
    ),
    # RB (AlphaTauri/VCARB) - Follows Red Bull patterns
    "RB": TeamProfile(
        team_name="RB",
        early_stopper_bias=0.5,
        extend_stint_tendency=0.5,
        conservative_compound=0.5,
        soft_start_preference=0.5,
        undercut_tendency=0.5,
        overcut_tendency=0.5,
        safety_car_opportunism=0.7,
        weather_gamble_tendency=0.5,
        multi_stop_preference=0.4,
    ),
    # Haas - Aggressive, nothing to lose
    "Haas F1 Team": TeamProfile(
        team_name="Haas F1 Team",
        early_stopper_bias=0.6,
        extend_stint_tendency=0.4,
        conservative_compound=0.4,
        soft_start_preference=0.6,
        undercut_tendency=0.7,
        overcut_tendency=0.3,
        safety_car_opportunism=0.9,
        weather_gamble_tendency=0.7,
        multi_stop_preference=0.5,
    ),
    # Kick Sauber - Conservative, protecting points
    "Kick Sauber": TeamProfile(
        team_name="Kick Sauber",
        early_stopper_bias=0.5,
        extend_stint_tendency=0.5,
        conservative_compound=0.6,
        soft_start_preference=0.4,
        undercut_tendency=0.4,
        overcut_tendency=0.5,
        safety_car_opportunism=0.7,
        weather_gamble_tendency=0.4,
        multi_stop_preference=0.3,
    ),
}

# Aliases for historical/alternative team names
_TEAM_ALIASES: dict[str, str] = {
    "AlphaTauri": "RB",
    "Alfa Romeo": "Kick Sauber",
    "Sauber": "Kick Sauber",
    "Racing Point": "Aston Martin",
    "Renault": "Alpine",
    "Toro Rosso": "RB",
}

# Default profile for unknown teams
_DEFAULT_PROFILE = TeamProfile(team_name="Unknown")


def get_team_profile(team_name: str) -> TeamProfile:
    """
    Get strategy profile for a team.

    Handles team name aliases and returns default for unknown teams.
    """
    # Direct match
    if team_name in TEAM_PROFILES:
        return TEAM_PROFILES[team_name]

    # Check aliases
    canonical = _TEAM_ALIASES.get(team_name)
    if canonical and canonical in TEAM_PROFILES:
        return TEAM_PROFILES[canonical]

    # Fuzzy match - check if team_name contains a known team
    for known_team in TEAM_PROFILES:
        if known_team.lower() in team_name.lower():
            return TEAM_PROFILES[known_team]

    return _DEFAULT_PROFILE


def calculate_pit_lap_adjustment(profile: TeamProfile, base_pit_lap: int) -> int:
    """
    Adjust ideal pit lap based on team tendencies.

    Returns adjustment in laps (negative = pit earlier).
    """
    # Early stopper bias shifts pit window earlier
    early_shift = int((profile.early_stopper_bias - 0.5) * -4)

    # Extend stint tendency shifts pit window later
    extend_shift = int((profile.extend_stint_tendency - 0.5) * 4)

    return base_pit_lap + early_shift + extend_shift


def will_react_to_safety_car(
    profile: TeamProfile, tyre_age: int, min_tyre_age: int = 8
) -> bool:
    """
    Predict if team will pit under safety car.

    Teams with high SC opportunism and older tyres are more likely to pit.
    """
    if tyre_age < min_tyre_age:
        return False

    # Higher opportunism = lower threshold for pitting
    age_threshold = int(15 - profile.safety_car_opportunism * 10)
    return tyre_age >= age_threshold
