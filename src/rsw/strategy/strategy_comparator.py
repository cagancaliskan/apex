"""
Strategy Comparator.

Compares different pit strategies using Monte Carlo simulation.
Returns ranked results with confidence intervals.

Design: Single responsibility - only comparison logic, delegates simulation.
"""

from dataclasses import dataclass

from .monte_carlo import simulate_race
from .strategy_generator import PitStrategy, generate_all_strategies


@dataclass
class StrategyResult:
    """
    Result of simulating a strategy.

    Contains expected outcomes and risk metrics.
    """

    strategy: PitStrategy
    expected_position: float
    position_std: float
    best_case: int
    worst_case: int
    prob_podium: float
    prob_points: float
    risk_score: float  # 0 = safe, 1 = high risk

    @property
    def score(self) -> float:
        """Overall strategy score (higher = better)."""
        # Weighted combination of expected position and consistency
        position_score = 20 - self.expected_position  # Convert to higher=better
        consistency_bonus = max(0, 5 - self.position_std)
        podium_bonus = self.prob_podium * 5

        return position_score + consistency_bonus + podium_bonus


def compare_strategies(
    driver_number: int,
    current_pace: float,
    deg_slope: float,
    current_position: int,
    competitors: list[tuple[float, float]],
    remaining_laps: int,
    pit_loss: float,
    current_lap: int,
    total_laps: int,
    current_compound: str = "MEDIUM",
    strategies: list[PitStrategy] | None = None,
    n_simulations: int = 200,
) -> list[StrategyResult]:
    """
    Compare multiple pit strategies using Monte Carlo simulation.

    Args:
        driver_number: Driver being analyzed
        current_pace: Current lap time
        deg_slope: Current degradation rate
        current_position: Current race position
        competitors: List of (pace, deg) for competitors
        remaining_laps: Laps remaining
        pit_loss: Pit stop time loss
        current_lap: Current lap number
        total_laps: Total race laps
        current_compound: Current tyre compound
        strategies: List of strategies to compare (auto-generated if None)
        n_simulations: Simulations per strategy

    Returns:
        List of StrategyResult sorted by score (best first)
    """
    # Generate strategies if not provided
    if strategies is None:
        strategies = generate_all_strategies(
            total_laps=total_laps,
            current_lap=current_lap,
            start_compound=current_compound,
            include_two_stop=remaining_laps > 35,
        )

    if not strategies:
        return []

    results = []

    for strategy in strategies:
        # Determine pit lap for this strategy
        # Use first stop lap if not yet pitted for this strategy
        pit_lap = None
        if strategy.stop_laps:
            # Find next pit lap that's in the future
            future_stops = [l for l in strategy.stop_laps if l > current_lap]
            if future_stops:
                pit_lap = future_stops[0]

        # Run Monte Carlo simulation
        outcome = simulate_race(
            driver_number=driver_number,
            current_pace=current_pace,
            deg_slope=deg_slope,
            current_position=current_position,
            competitors=competitors,
            remaining_laps=remaining_laps,
            pit_loss=pit_loss,
            pit_lap=pit_lap,
            n_simulations=n_simulations,
        )

        # Calculate risk score
        # Higher variance = higher risk
        # More stops = higher risk
        variance_risk = min(1.0, outcome.position_std / 5)
        stops_risk = strategy.n_stops * 0.15
        risk_score = min(1.0, variance_risk + stops_risk)

        result = StrategyResult(
            strategy=strategy,
            expected_position=outcome.expected_position,
            position_std=outcome.position_std,
            best_case=outcome.best_case,
            worst_case=outcome.worst_case,
            prob_podium=outcome.prob_podium,
            prob_points=outcome.prob_points,
            risk_score=risk_score,
        )

        results.append(result)

    # Sort by score (higher = better)
    return sorted(results, key=lambda r: r.score, reverse=True)


def get_best_strategy(
    driver_number: int,
    current_pace: float,
    deg_slope: float,
    current_position: int,
    competitors: list[tuple[float, float]],
    remaining_laps: int,
    pit_loss: float,
    current_lap: int,
    total_laps: int,
    current_compound: str = "MEDIUM",
    risk_tolerance: float = 0.5,
) -> StrategyResult | None:
    """
    Get the best strategy considering risk tolerance.

    Args:
        risk_tolerance: 0 = very conservative, 1 = very aggressive

    Returns:
        Best StrategyResult or None if no viable strategies
    """
    results = compare_strategies(
        driver_number=driver_number,
        current_pace=current_pace,
        deg_slope=deg_slope,
        current_position=current_position,
        competitors=competitors,
        remaining_laps=remaining_laps,
        pit_loss=pit_loss,
        current_lap=current_lap,
        total_laps=total_laps,
        current_compound=current_compound,
    )

    if not results:
        return None

    # Filter by risk tolerance
    acceptable = [r for r in results if r.risk_score <= risk_tolerance + 0.2]

    if not acceptable:
        # If nothing acceptable, take the lowest risk option
        return min(results, key=lambda r: r.risk_score)

    return acceptable[0]  # Best scoring that's within risk tolerance


def compare_one_vs_two_stop(
    driver_number: int,
    current_pace: float,
    deg_slope: float,
    current_position: int,
    competitors: list[tuple[float, float]],
    remaining_laps: int,
    pit_loss: float,
    current_lap: int,
    total_laps: int,
    current_compound: str = "MEDIUM",
) -> tuple[StrategyResult | None, StrategyResult | None, str]:
    """
    Compare best 1-stop vs best 2-stop strategy.

    Returns:
        Tuple of (best_1_stop, best_2_stop, recommendation)
    """
    results = compare_strategies(
        driver_number=driver_number,
        current_pace=current_pace,
        deg_slope=deg_slope,
        current_position=current_position,
        competitors=competitors,
        remaining_laps=remaining_laps,
        pit_loss=pit_loss,
        current_lap=current_lap,
        total_laps=total_laps,
        current_compound=current_compound,
    )

    one_stops = [r for r in results if r.strategy.n_stops == 1]
    two_stops = [r for r in results if r.strategy.n_stops == 2]

    best_one = one_stops[0] if one_stops else None
    best_two = two_stops[0] if two_stops else None

    # Generate recommendation
    if best_one and best_two:
        pos_diff = best_one.expected_position - best_two.expected_position
        if abs(pos_diff) < 0.5:
            recommendation = "Strategies are equivalent - prefer 1-stop for simplicity"
        elif pos_diff < 0:
            recommendation = f"1-stop is {-pos_diff:.1f} positions better"
        else:
            recommendation = f"2-stop is {pos_diff:.1f} positions better"
    elif best_one:
        recommendation = "Only 1-stop strategies viable"
    elif best_two:
        recommendation = "Only 2-stop strategies viable"
    else:
        recommendation = "No viable strategies found"

    return best_one, best_two, recommendation
