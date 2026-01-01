"""
Strategy Service - handles pit strategy calculations.

Single Responsibility: Contains all strategy-related business logic.
Open/Closed: Extensible via strategy calculators.
"""

from dataclasses import dataclass
from typing import Any

from rsw.interfaces import IStrategyCalculator
from rsw.logging_config import get_logger
from rsw.state.schemas import DriverState, RaceState

logger = get_logger(__name__)


@dataclass
class PitWindow:
    """Pit window result - immutable data transfer object."""
    min_lap: int
    max_lap: int
    ideal_lap: int
    reason: str


@dataclass
class Recommendation:
    """Strategy recommendation - immutable DTO."""
    action: str
    confidence: float
    reason: str
    undercut_threat: bool = False
    overcut_opportunity: bool = False


class StrategyService(IStrategyCalculator):
    """
    Service for strategy calculations.
    
    Follows:
    - SRP: Only handles strategy calculations
    - OCP: Can be extended with new strategies
    - DIP: Uses StrategyConfig abstraction
    """
    
    def __init__(self, config: Any) -> None:
        """
        Initialize with configuration.
        
        Args:
            config: Strategy configuration (StrategyConfig)
        """
        self.config = config
        self._pit_loss_cache: dict[str, float] = {}
    
    def calculate_pit_window(
        self,
        driver: DriverState,
        total_laps: int,
        pit_loss: float,
    ) -> dict:
        """
        Calculate optimal pit window.
        
        Encapsulation: Hides complex calculation details.
        """
        from rsw.strategy.pit_window import find_optimal_window
        
        window = find_optimal_window(
            current_lap=driver.current_lap,
            total_laps=total_laps,
            deg_slope=driver.deg_slope,
            current_pace=driver.last_lap_time or 90.0,
            pit_loss=pit_loss,
            tyre_age=driver.tyre_age,
            compound=driver.compound or "MEDIUM",
            cliff_risk=driver.cliff_risk,
        )
        
        return {
            "min_lap": window.min_lap,
            "max_lap": window.max_lap,
            "ideal_lap": window.ideal_lap,
            "reason": window.reason,
        }
    
    def get_recommendation(
        self,
        driver: DriverState,
        race_state: RaceState,
    ) -> dict:
        """
        Get pit recommendation for a driver.
        
        Encapsulation: Complex decision logic hidden.
        """
        from rsw.strategy.decision import evaluate_strategy
        
        rec = evaluate_strategy(
            driver_number=driver.driver_number,
            current_lap=race_state.current_lap,
            total_laps=race_state.total_laps or 50,
            current_position=driver.position,
            deg_slope=driver.deg_slope,
            cliff_risk=driver.cliff_risk,
            current_pace=driver.last_lap_time or 90.0,
            tyre_age=driver.tyre_age,
            compound=driver.compound or "MEDIUM",
            pit_loss=22.0,  # TODO: get from track config
            safety_car=race_state.safety_car,
        )
        
        return {
            "recommendation": rec.recommendation.value,
            "confidence": rec.confidence,
            "reason": rec.reason,
            "undercut_threat": rec.undercut_threat,
            "overcut_opportunity": rec.overcut_opportunity,
            "pit_window": {
                "min": rec.pit_window.min_lap if rec.pit_window else 0,
                "max": rec.pit_window.max_lap if rec.pit_window else 0,
                "ideal": rec.pit_window.ideal_lap if rec.pit_window else 0,
            } if rec.pit_window else None,
        }
    
    def run_monte_carlo(
        self,
        driver: DriverState,
        competitors: list[DriverState],
        remaining_laps: int,
        pit_loss: float,
        n_simulations: int | None = None,
    ) -> dict:
        """
        Run Monte Carlo simulation.
        
        Follows KISS: Simple interface, complex logic hidden.
        """
        from rsw.strategy.monte_carlo import simulate_race
        
        outcome = simulate_race(
            driver_number=driver.driver_number,
            current_pace=driver.last_lap_time or 90.0,
            deg_slope=driver.deg_slope,
            current_position=driver.position,
            competitors=[(c.last_lap_time or 90.0, c.deg_slope) for c in competitors],
            remaining_laps=remaining_laps,
            pit_loss=pit_loss,
            n_simulations=n_simulations or self.config.monte_carlo_simulations,
        )
        
        return {
            "expected_position": outcome.expected_position,
            "position_std": outcome.position_std,
            "prob_win": outcome.prob_win,
            "prob_podium": outcome.prob_podium,
            "prob_points": outcome.prob_points,
        }
