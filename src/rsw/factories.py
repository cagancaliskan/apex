"""
Factory classes for object creation.

Follows: Factory Pattern, Single Responsibility
Encapsulates object creation logic.
"""

from typing import Any
from dataclasses import dataclass

from rsw.domain import TyreCompound, PitWindow, StrategyRecommendation, RecommendationType
from rsw.runtime_config import get_config


class DataProviderFactory:
    """
    Factory for creating data providers.
    
    Follows:
    - Factory Pattern: Encapsulates creation
    - OCP: New providers added without modifying existing code
    """
    
    @staticmethod
    def create(provider_type: str = "openf1") -> Any:
        """
        Create a data provider instance.
        
        Args:
            provider_type: Type of provider ("openf1", "cached", "mock")
            
        Returns:
            Data provider instance
        """
        if provider_type == "openf1":
            from rsw.ingest import OpenF1Client
            return OpenF1Client()
        
        elif provider_type == "cached":
            from rsw.ingest.cached import CachedDataProvider
            config = get_config()
            return CachedDataProvider(config.sessions_dir)
        
        elif provider_type == "mock":
            from rsw.ingest.mock import MockDataProvider
            return MockDataProvider()
        
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")


class StrategyFactory:
    """
    Factory for creating strategy calculators.
    
    Enables swapping strategy implementations.
    """
    
    @staticmethod
    def create(strategy_type: str = "default") -> Any:
        """
        Create a strategy calculator.
        
        Args:
            strategy_type: Type of strategy ("default", "aggressive", "conservative")
            
        Returns:
            Strategy calculator instance
        """
        from rsw.services.strategy_service import StrategyService
        
        config = get_config()
        service = StrategyService(config.strategy)
        
        # Could customize behavior based on strategy_type
        return service


class PitWindowFactory:
    """
    Factory for creating pit windows.
    
    Encapsulates complex pit window creation.
    """
    
    @staticmethod
    def from_calculation(
        current_lap: int,
        total_laps: int,
        deg_slope: float,
        pit_loss: float,
        compound: TyreCompound | str,
        tyre_age: int = 0,
    ) -> PitWindow:
        """
        Create pit window from calculation.
        
        Args:
            current_lap: Current race lap
            total_laps: Total laps in race
            deg_slope: Degradation slope (s/lap)
            pit_loss: Pit stop time loss
            compound: Current tyre compound
            tyre_age: Current tyre age
            
        Returns:
            Calculated PitWindow
        """
        if isinstance(compound, str):
            compound = TyreCompound(compound)
        
        # Adjust for compound characteristics
        deg_factor = compound.degradation_factor
        adjusted_deg = deg_slope * deg_factor
        
        # Calculate optimal stint length
        # Pit when degradation cost exceeds pit loss
        if adjusted_deg > 0:
            optimal_stint = int(pit_loss / adjusted_deg / 2)
        else:
            optimal_stint = 25  # Default
        
        # Calculate window
        remaining = total_laps - current_lap
        ideal = min(current_lap + optimal_stint - tyre_age, total_laps - 10)
        min_lap = max(current_lap + 3, ideal - 5)  # At least 3 more laps
        max_lap = min(ideal + 8, total_laps - 5)   # Leave margin
        
        # Ensure valid window
        ideal = max(min_lap, min(ideal, max_lap))
        
        reason = f"Based on {adjusted_deg:.3f} s/lap degradation"
        
        return PitWindow(
            min_lap=min_lap,
            max_lap=max_lap,
            ideal_lap=ideal,
            reason=reason,
        )


class RecommendationFactory:
    """
    Factory for creating strategy recommendations.
    
    Encapsulates recommendation creation logic.
    """
    
    @staticmethod
    def pit_now(reason: str, confidence: float = 0.9) -> StrategyRecommendation:
        """Create PIT_NOW recommendation."""
        return StrategyRecommendation(
            recommendation=RecommendationType.PIT_NOW,
            confidence=confidence,
            reason=reason,
        )
    
    @staticmethod
    def stay_out(reason: str, confidence: float = 0.8) -> StrategyRecommendation:
        """Create STAY_OUT recommendation."""
        return StrategyRecommendation(
            recommendation=RecommendationType.STAY_OUT,
            confidence=confidence,
            reason=reason,
        )
    
    @staticmethod
    def consider_pit(
        reason: str,
        window: PitWindow,
        confidence: float = 0.7,
    ) -> StrategyRecommendation:
        """Create CONSIDER_PIT recommendation with window."""
        return StrategyRecommendation(
            recommendation=RecommendationType.CONSIDER_PIT,
            confidence=confidence,
            reason=reason,
            pit_window=window,
        )
