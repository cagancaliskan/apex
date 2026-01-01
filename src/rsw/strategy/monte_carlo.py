"""
Monte Carlo race simulation for outcome prediction.

Simulates thousands of race scenarios to predict:
- Finish position distributions
- Points probability
- Risk assessment for different strategies
"""

import random
from dataclasses import dataclass, field
from typing import Optional
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
        c_pit_lap = random.randint(remaining_laps // 3, remaining_laps * 2 // 3) if remaining_laps > 15 else None
        
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
) -> OutcomeDistribution:
    """
    Run Monte Carlo simulation for race outcomes.
    
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
    
    Returns:
        OutcomeDistribution with full statistics
    """
    positions = []
    
    for _ in range(n_simulations):
        pos = simulate_single_race(
            driver_pace=current_pace,
            driver_deg=deg_slope,
            competitors=competitors,
            remaining_laps=remaining_laps,
            current_position=current_position,
            pit_lap=pit_lap,
            pit_loss=pit_loss,
            sc_probability=sc_probability,
        )
        positions.append(pos)
    
    positions = np.array(positions)
    
    # Calculate statistics
    position_counts = {}
    for p in range(1, 21):
        count = np.sum(positions == p)
        if count > 0:
            position_counts[p] = count / n_simulations
    
    expected_pos = np.mean(positions)
    std_pos = np.std(positions)
    
    # Points calculation
    points = [POINTS.get(p, 0) for p in positions]
    expected_points = np.mean(points)
    std_points = np.std(points)
    
    prob_win = np.sum(positions == 1) / n_simulations
    prob_podium = np.sum(positions <= 3) / n_simulations
    prob_points = np.sum(positions <= 10) / n_simulations
    
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
        worst_case=int(np.max(positions)),
        best_case=int(np.min(positions)),
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
