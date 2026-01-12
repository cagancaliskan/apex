"""
Monte Carlo race simulation for outcome prediction.

Simulates thousands of race scenarios to predict:
- Finish position distributions
- Points probability
- Risk assessment for different strategies
"""

import random
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class OutcomeDistribution:
    """Distribution of race outcomes from Monte Carlo simulation."""

    driver_number: int
    n_simulations: int

    # Position probabilities
    position_probabilities: dict[int, float] = field(default_factory=dict)
    expected_position: float = 0.0
    position_std: float = 0.0

    # Points probabilities
    expected_points: float = 0.0
    points_std: float = 0.0

    # Podium/points finish probabilities
    prob_win: float = 0.0
    prob_podium: float = 0.0
    prob_points: float = 0.0

    # Risk metrics
    worst_case: int = 20
    best_case: int = 1


# F1 points system
POINTS = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}


@dataclass
class RaceScenario:
    """A single simulated race scenario."""

    has_safety_car: bool = False
    safety_car_lap: int = 0
    has_vsc: bool = False
    vsc_lap: int = 0
    rain_probability: float = 0.0


def sample_safety_car(
    remaining_laps: int,
    base_probability: float = 0.3,
) -> tuple[bool, int]:
    """
    Sample whether a safety car occurs.

    Args:
        remaining_laps: Laps remaining in race
        base_probability: Base probability of SC during remaining laps

    Returns:
        Tuple of (has_sc, lap_of_sc)
    """
    if random.random() > base_probability:
        return False, 0

    # SC more likely at start of remaining laps
    weights = [1.5 - (i / remaining_laps) for i in range(remaining_laps)]
    total = sum(weights)
    weights = [w / total for w in weights]

    lap = random.choices(range(remaining_laps), weights=weights)[0]
    return True, lap


def sample_scenario(
    remaining_laps: int,
    sc_probability: float = 0.3,
    vsc_probability: float = 0.2,
) -> RaceScenario:
    """Sample a race scenario with random events."""
    has_sc, sc_lap = sample_safety_car(remaining_laps, sc_probability)
    has_vsc, vsc_lap = sample_safety_car(remaining_laps, vsc_probability)

    return RaceScenario(
        has_safety_car=has_sc,
        safety_car_lap=sc_lap,
        has_vsc=has_vsc and not has_sc,  # Don't overlap
        vsc_lap=vsc_lap if not has_sc else 0,
    )


def simulate_single_race(
    driver_pace: float,
    driver_deg: float,
    competitors: list[tuple[float, float]],  # [(pace, deg), ...]
    remaining_laps: int,
    current_position: int,
    pit_lap: int | None,
    pit_loss: float,
    sc_probability: float = 0.3,
) -> int:
    """
    Simulate a single race outcome.

    Args:
        driver_pace: Our base pace
        driver_deg: Our degradation rate
        competitors: List of (pace, deg) for competitors
        remaining_laps: Laps remaining
        current_position: Current position (1-indexed)
        pit_lap: Lap we plan to pit (None = no pit)
        pit_loss: Pit stop time loss
        sc_probability: Safety car probability

    Returns:
        Final position
    """
    # Sample random events
    scenario = sample_scenario(remaining_laps, sc_probability)

    # Calculate our total race time
    our_time = 0.0
    for lap in range(remaining_laps):
        lap_time = driver_pace + driver_deg * lap

        # Pit stop
        if pit_lap and lap == pit_lap:
            our_time += pit_loss
            # Reset degradation after pit
            driver_deg *= 0.5  # Fresh tyres

        # Safety car
        if scenario.has_safety_car and lap == scenario.safety_car_lap:
            # SC bunches field
            lap_time = driver_pace  # Neutralized
            if pit_lap and lap == pit_lap:
                our_time -= pit_loss * 0.6  # Free pit stop

        our_time += lap_time + random.gauss(0, 0.2)  # Random variance

    # Simulate competitors
    competitor_times = []
    for i, (pace, deg) in enumerate(competitors):
        time = 0.0
        c_deg = deg

        # Random pit lap for competitor
        c_pit_lap = (
            random.randint(remaining_laps // 3, remaining_laps * 2 // 3)
            if remaining_laps > 15
            else None
        )

        for lap in range(remaining_laps):
            lap_time = pace + c_deg * lap

            if c_pit_lap and lap == c_pit_lap:
                time += pit_loss
                c_deg *= 0.5

            if scenario.has_safety_car and lap == scenario.safety_car_lap:
                lap_time = pace
                if c_pit_lap and lap == c_pit_lap:
                    time -= pit_loss * 0.6

            time += lap_time + random.gauss(0, 0.2)

        competitor_times.append((i, time))

    # Sort by time to get positions
    all_times = [("driver", our_time)] + [(i, t) for i, t in competitor_times]
    all_times.sort(key=lambda x: x[1])

    # Find our position
    for pos, (who, _) in enumerate(all_times, 1):
        if who == "driver":
            return pos

    return current_position


def _run_single_sim(args: tuple) -> int:
    """
    Worker function for parallel simulation.

    Takes a tuple of arguments to work with ProcessPoolExecutor.
    """
    (
        driver_pace,
        driver_deg,
        competitors,
        remaining_laps,
        current_position,
        pit_lap,
        pit_loss,
        sc_probability,
        seed,
    ) = args

    # Set random seed for reproducibility
    random.seed(seed)
    np.random.seed(seed)

    return simulate_single_race(
        driver_pace=driver_pace,
        driver_deg=driver_deg,
        competitors=competitors,
        remaining_laps=remaining_laps,
        current_position=current_position,
        pit_lap=pit_lap,
        pit_loss=pit_loss,
        sc_probability=sc_probability,
    )


def simulate_race(
    driver_number: int,
    current_pace: float,
    deg_slope: float,
    current_position: int,
    competitors: list[tuple[float, float]],
    remaining_laps: int,
    pit_loss: float,
    pit_lap: int | None = None,
    n_simulations: int = 500,
    sc_probability: float = 0.3,
    n_workers: int | None = None,
) -> OutcomeDistribution:
    """
    Run Monte Carlo simulation for race outcomes.

    Uses parallel processing when n_simulations > 100 for improved performance.

    Args:
        driver_number: Driver being simulated
        current_pace: Current lap time
        deg_slope: Degradation rate
        current_position: Current position
        competitors: List of (pace, deg) for other drivers
        remaining_laps: Laps remaining
        pit_loss: Pit stop time loss
        pit_lap: Planned pit lap (None for no pit)
        n_simulations: Number of simulations
        sc_probability: Safety car probability
        n_workers: Number of parallel workers (None = auto)

    Returns:
        OutcomeDistribution with full statistics
    """
    # Use parallel processing for large simulation counts
    if n_simulations > 100:
        positions = _simulate_parallel(
            driver_pace=current_pace,
            driver_deg=deg_slope,
            competitors=competitors,
            remaining_laps=remaining_laps,
            current_position=current_position,
            pit_lap=pit_lap,
            pit_loss=pit_loss,
            sc_probability=sc_probability,
            n_simulations=n_simulations,
            n_workers=n_workers,
        )
    else:
        # NOTE: Legacy Competitor List format [(pace, deg)...] is not compatible with GridSimulator
        # which requires full DriverState objects.
        # For this refactor, we will maintain the interface but adapt the internal logic logic
        # slowly. Ideally, we should refactor the inputs to `simulate_race` to take `race_state`
        # but that breaks the API.

        # For now, we will perform a 'Mock' Grid Simulation using simplified objects constructed from the inputs.

        positions = _simulate_sequential_legacy(
            driver_pace=current_pace,
            driver_deg=deg_slope,
            competitors=competitors,
            remaining_laps=remaining_laps,
            current_position=current_position,
            pit_lap=pit_lap,
            pit_loss=pit_loss,
            sc_probability=sc_probability,
            n_simulations=n_simulations,
        )

    return _calculate_statistics(driver_number, positions, n_simulations)


def _simulate_sequential_legacy(
    driver_pace: float,
    driver_deg: float,
    competitors: list[tuple[float, float]],
    remaining_laps: int,
    current_position: int,
    pit_lap: int | None,
    pit_loss: float,
    sc_probability: float,
    n_simulations: int,
) -> list[int]:
    """
    Run simulations sequentially (Legacy wrapper).
    Keeps the old logic for now until we fully wire up GridSimulator with RaceState.
    """
    positions = []

    # We will use the OLD logic for now to ensure we don't break the build
    # while we wait to refactor the call sites in simulation_service.py.
    # The GridSimulator requires the FULL RaceState, which `simulate_race` currently doesn't receive.

    for _ in range(n_simulations):
        pos = simulate_single_race(
            driver_pace=driver_pace,
            driver_deg=driver_deg,
            competitors=competitors,
            remaining_laps=remaining_laps,
            current_position=current_position,
            pit_lap=pit_lap,
            pit_loss=pit_loss,
            sc_probability=sc_probability,
        )
        positions.append(pos)
    return positions


def _simulate_parallel(
    driver_pace: float,
    driver_deg: float,
    competitors: list[tuple[float, float]],
    remaining_laps: int,
    current_position: int,
    pit_lap: int | None,
    pit_loss: float,
    sc_probability: float,
    n_simulations: int,
    n_workers: int | None = None,
) -> list[int]:
    """
    Run simulations in parallel using ProcessPoolExecutor.

    Args:
        n_workers: Number of workers (None = CPU count)

    Returns:
        List of finish positions from all simulations
    """
    import os
    from concurrent.futures import ProcessPoolExecutor

    if n_workers is None:
        n_workers = min(os.cpu_count() or 4, 8)  # Cap at 8 workers

    # Prepare arguments with unique seeds
    base_seed = random.randint(0, 10000)
    args_list = [
        (
            driver_pace,
            driver_deg,
            competitors,
            remaining_laps,
            current_position,
            pit_lap,
            pit_loss,
            sc_probability,
            base_seed + i,
        )
        for i in range(n_simulations)
    ]

    # Run in parallel
    try:
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            positions = list(
                executor.map(
                    _run_single_sim, args_list, chunksize=max(1, n_simulations // n_workers)
                )
            )
        return positions
    except Exception:
        # Fallback to sequential on error
        return _simulate_sequential_legacy(
            driver_pace,
            driver_deg,
            competitors,
            remaining_laps,
            current_position,
            pit_lap,
            pit_loss,
            sc_probability,
            n_simulations,
        )


def _calculate_statistics(
    driver_number: int,
    positions: list[int],
    n_simulations: int,
) -> OutcomeDistribution:
    """Calculate statistics from simulation results."""
    positions_arr = np.array(positions)

    # Calculate statistics
    position_counts = {}
    for p in range(1, 21):
        count = int(np.sum(positions_arr == p))
        if count > 0:
            position_counts[p] = float(count / n_simulations)

    expected_pos = float(np.mean(positions_arr))
    std_pos = float(np.std(positions_arr))

    # Points calculation
    points = [POINTS.get(p, 0) for p in positions]
    expected_points = float(np.mean(points))
    std_points = float(np.std(points))

    prob_win = float(np.sum(positions_arr == 1) / n_simulations)
    prob_podium = float(np.sum(positions_arr <= 3) / n_simulations)
    prob_points = float(np.sum(positions_arr <= 10) / n_simulations)

    return OutcomeDistribution(
        driver_number=driver_number,
        n_simulations=n_simulations,
        position_probabilities=position_counts,
        expected_position=expected_pos,
        position_std=std_pos,
        expected_points=expected_points,
        points_std=std_points,
        prob_win=prob_win,
        prob_podium=prob_podium,
        prob_points=prob_points,
        worst_case=int(np.max(positions_arr)),
        best_case=int(np.min(positions_arr)),
    )


def compare_strategies(
    driver_number: int,
    current_pace: float,
    deg_slope: float,
    current_position: int,
    competitors: list[tuple[float, float]],
    remaining_laps: int,
    pit_loss: float,
    current_lap: int,
    n_simulations: int = 300,
) -> tuple[OutcomeDistribution, OutcomeDistribution]:
    """
    Compare pit now vs stay out strategies.

    Returns:
        Tuple of (pit_now_outcome, stay_out_outcome)
    """
    # Pit now
    pit_now = simulate_race(
        driver_number=driver_number,
        current_pace=current_pace,
        deg_slope=deg_slope,
        current_position=current_position,
        competitors=competitors,
        remaining_laps=remaining_laps,
        pit_loss=pit_loss,
        pit_lap=0,  # Pit immediately
        n_simulations=n_simulations,
    )

    # Stay out (pit later or not at all)
    later_lap = remaining_laps // 2 if remaining_laps > 20 else None
    stay_out = simulate_race(
        driver_number=driver_number,
        current_pace=current_pace,
        deg_slope=deg_slope,
        current_position=current_position,
        competitors=competitors,
        remaining_laps=remaining_laps,
        pit_loss=pit_loss,
        pit_lap=later_lap,
        n_simulations=n_simulations,
    )

    return pit_now, stay_out


def simulate_grid_outcome(
    driver_number: int,
    initial_state: dict[int, Any],  # Dict[int, DriverState]
    remaining_laps: int,
    n_simulations: int = 100,
) -> OutcomeDistribution:
    """
    Run Grid-Wide Monte Carlo simulation.
    Uses GridSimulator to simulate all cars interacting.
    """
    from rsw.strategy.grid_simulator import GridSimulator

    simulator = GridSimulator()
    final_positions_list = []

    # Run simulations
    # TODO: Parallelize this using ProcessPoolExecutor for performance
    for _ in range(n_simulations):
        final_positions = simulator.run_simulation(
            initial_state=initial_state, remaining_laps=remaining_laps
        )
        final_positions_list.append(final_positions.get(driver_number, 20))

    return _calculate_statistics(driver_number, final_positions_list, n_simulations)
