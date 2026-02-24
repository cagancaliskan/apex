"""
Driver Behavior Modeling.

Models individual driver characteristics that affect strategy decisions.
Used to personalize predictions beyond team-level patterns.

Design: KISS - Simple dataclass with computed properties, DRY via shared base.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DriverBehavior:
    """
    Individual driver characteristics affecting strategy.

    All values normalized 0.0-1.0 where:
    - 0.0 = Low ability/tendency
    - 0.5 = Average
    - 1.0 = Exceptional/High tendency
    """

    driver_number: int
    name_acronym: str

    # Driving style
    tyre_management: float = 0.5  # 1.0 = exceptional tyre preservation
    overtaking_aggression: float = 0.5  # 1.0 = very aggressive overtaker
    defensive_skill: float = 0.5  # 1.0 = excellent at holding position

    # Conditions
    wet_weather_ability: float = 0.5  # 1.0 = rain master
    consistency: float = 0.5  # 1.0 = rarely makes mistakes

    # Strategy interaction
    follows_team_orders: float = 0.5  # 1.0 = always complies
    risk_tolerance: float = 0.5  # 1.0 = takes big risks for gains


# =============================================================================
# Driver Profiles (based on 2022-2024 performance data)
# =============================================================================

DRIVER_BEHAVIORS: dict[int, DriverBehavior] = {
    # Max Verstappen - Complete package, excellent management (DU DU DU DU, MAX VERSTAPPENNN!)
    1: DriverBehavior(
        driver_number=1,
        name_acronym="VER",
        tyre_management=0.9,
        overtaking_aggression=0.8,
        defensive_skill=0.9,
        wet_weather_ability=0.9,
        consistency=0.95,
        follows_team_orders=0.7,
        risk_tolerance=0.6,
    ),
    # Sergio Perez - Good tyre whisperer
    11: DriverBehavior(
        driver_number=11,
        name_acronym="PER",
        tyre_management=0.8,
        overtaking_aggression=0.5,
        defensive_skill=0.7,
        wet_weather_ability=0.7,
        consistency=0.6,
        follows_team_orders=0.9,
        risk_tolerance=0.4,
    ),
    # Lewis Hamilton - All-time great, exceptional in all conditions
    44: DriverBehavior(
        driver_number=44,
        name_acronym="HAM",
        tyre_management=0.85,
        overtaking_aggression=0.8,
        defensive_skill=0.85,
        wet_weather_ability=0.95,
        consistency=0.9,
        follows_team_orders=0.6,
        risk_tolerance=0.65,
    ),
    # George Russell - Consistent, calculating
    63: DriverBehavior(
        driver_number=63,
        name_acronym="RUS",
        tyre_management=0.75,
        overtaking_aggression=0.7,
        defensive_skill=0.75,
        wet_weather_ability=0.75,
        consistency=0.85,
        follows_team_orders=0.7,
        risk_tolerance=0.5,
    ),
    # Charles Leclerc - Fast but error-prone
    16: DriverBehavior(
        driver_number=16,
        name_acronym="LEC",
        tyre_management=0.7,
        overtaking_aggression=0.8,
        defensive_skill=0.75,
        wet_weather_ability=0.7,
        consistency=0.65,
        follows_team_orders=0.6,
        risk_tolerance=0.75,
    ),
    # Carlos Sainz - Smooth operator, consistent
    55: DriverBehavior(
        driver_number=55,
        name_acronym="SAI",
        tyre_management=0.75,
        overtaking_aggression=0.65,
        defensive_skill=0.8,
        wet_weather_ability=0.65,
        consistency=0.8,
        follows_team_orders=0.7,
        risk_tolerance=0.5,
    ),
    # Lando Norris - Quick but can overcook tyres
    4: DriverBehavior(
        driver_number=4,
        name_acronym="NOR",
        tyre_management=0.65,
        overtaking_aggression=0.75,
        defensive_skill=0.7,
        wet_weather_ability=0.8,
        consistency=0.75,
        follows_team_orders=0.75,
        risk_tolerance=0.6,
    ),
    # Oscar Piastri - Mature beyond years
    81: DriverBehavior(
        driver_number=81,
        name_acronym="PIA",
        tyre_management=0.75,
        overtaking_aggression=0.7,
        defensive_skill=0.75,
        wet_weather_ability=0.7,
        consistency=0.8,
        follows_team_orders=0.8,
        risk_tolerance=0.5,
    ),
    # Fernando Alonso - Master strategist
    14: DriverBehavior(
        driver_number=14,
        name_acronym="ALO",
        tyre_management=0.9,
        overtaking_aggression=0.7,
        defensive_skill=0.95,
        wet_weather_ability=0.85,
        consistency=0.85,
        follows_team_orders=0.5,
        risk_tolerance=0.6,
    ),
    # Lance Stroll - Solid, occasional brilliance
    18: DriverBehavior(
        driver_number=18,
        name_acronym="STR",
        tyre_management=0.6,
        overtaking_aggression=0.55,
        defensive_skill=0.6,
        wet_weather_ability=0.7,
        consistency=0.55,
        follows_team_orders=0.8,
        risk_tolerance=0.5,
    ),
}

# Default for drivers not in database
_DEFAULT_BEHAVIOR = DriverBehavior(driver_number=0, name_acronym="UNK")


def get_driver_behavior(driver_number: int) -> DriverBehavior:
    """Get behavior profile for a driver, returns default if not found."""
    return DRIVER_BEHAVIORS.get(driver_number, _DEFAULT_BEHAVIOR)


def calculate_effective_cliff_lap(
    base_cliff_lap: int,
    driver: DriverBehavior,
    compound: str = "MEDIUM",
) -> int:
    """
    Adjust tyre cliff lap based on driver's tyre management skill.

    Better managers can extend the tyre life before hitting the cliff.

    Args:
        base_cliff_lap: Standard cliff lap for the compound
        driver: Driver behavior profile
        compound: Current tyre compound

    Returns:
        Adjusted cliff lap
    """
    # Tyre management extends cliff by up to 5 laps
    management_bonus = int((driver.tyre_management - 0.5) * 10)

    # Soft tyres are harder to manage - reduce bonus
    if compound == "SOFT":
        management_bonus = int(management_bonus * 0.6)
    elif compound == "HARD":
        management_bonus = int(management_bonus * 1.2)

    return base_cliff_lap + management_bonus


def calculate_overtake_probability(
    attacker: DriverBehavior,
    defender: DriverBehavior,
    pace_delta: float,
    drs_available: bool = True,
) -> float:
    """
    Calculate probability of successful overtake.

    Args:
        attacker: Attacking driver's behavior
        defender: Defending driver's behavior
        pace_delta: Pace advantage (positive = attacker faster)
        drs_available: Whether DRS is available

    Returns:
        Probability 0.0-1.0 of successful pass
    """
    if pace_delta <= 0:
        return 0.1  # Very unlikely without pace advantage

    # Base probability from pace delta
    base_prob = min(0.5, pace_delta * 0.15)  # 0.5s = 7.5%, capped at 50%

    # Attacker aggression bonus
    attack_bonus = (attacker.overtaking_aggression - 0.5) * 0.2

    # Defender skill penalty
    defend_penalty = (defender.defensive_skill - 0.5) * 0.15

    # DRS boost
    drs_boost = 0.15 if drs_available else 0.0

    prob = base_prob + attack_bonus - defend_penalty + drs_boost

    return max(0.05, min(0.9, prob))


def should_extend_stint(driver: DriverBehavior, remaining_tyre_life: int) -> bool:
    """
    Determine if driver can safely extend stint.

    Good tyre managers can push further into the marginal tyre window.
    """
    # High tyre management allows smaller buffer
    safe_buffer = int(5 - driver.tyre_management * 4)  # 1-5 laps

    return remaining_tyre_life > safe_buffer
