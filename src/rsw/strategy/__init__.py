"""
Strategy engine for race pit stop optimization.
"""

from .pitloss import calculate_pit_loss, estimate_position_loss
from .pit_window import find_optimal_window, PitWindow
from .monte_carlo import simulate_race, OutcomeDistribution
from .decision import evaluate_strategy, PitDecision, StrategyRecommendation
from .explain import explain_recommendation

__all__ = [
    "calculate_pit_loss",
    "estimate_position_loss",
    "find_optimal_window",
    "PitWindow",
    "simulate_race",
    "OutcomeDistribution",
    "evaluate_strategy",
    "PitDecision",
    "StrategyRecommendation",
    "explain_recommendation",
]
