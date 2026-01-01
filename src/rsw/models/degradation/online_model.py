"""
Online degradation model manager for per-driver performance tracking.

This module manages RLS models for each driver's current stint,
providing pace predictions and cliff risk assessment.
"""

import numpy as np
from dataclasses import dataclass, field
from datetime import datetime

from .rls import RLSEstimator, create_feature_vector
from .calibration import get_warm_start_params, get_cliff_risk_threshold


@dataclass
class StintModel:
    """Model state for a single stint."""
    stint_number: int
    compound: str
    start_lap: int
    rls: RLSEstimator
    lap_times: list[float] = field(default_factory=list)
    is_active: bool = True


@dataclass
class DegradationPrediction:
    """Prediction output from degradation model."""
    driver_number: int
    stint_number: int
    compound: str
    
    # Model parameters
    base_pace: float
    deg_slope: float  # Seconds per lap of degradation
    
    # Predictions
    predicted_current: float  # Predicted time for current lap
    predicted_next_k: list[float]  # Predicted times for next k laps
    
    # Risk scores
    cliff_risk: float  # 0-1 score for tyre cliff risk
    model_confidence: float  # 0-1 score for model confidence
    
    # Metadata
    n_observations: int
    last_update: datetime = field(default_factory=datetime.utcnow)


class DriverDegradationModel:
    """
    Manages degradation models for a single driver across stints.
    
    Creates a new RLS model for each stint, with warm-start from priors.
    Provides pace predictions and risk assessment.
    """
    
    def __init__(
        self,
        driver_number: int,
        forgetting_factor: float = 0.95,
        min_observations: int = 3,
    ):
        """
        Initialize driver model.
        
        Args:
            driver_number: Driver's car number
            forgetting_factor: RLS forgetting factor
            min_observations: Minimum laps before making predictions
        """
        self.driver_number = driver_number
        self.forgetting_factor = forgetting_factor
        self.min_observations = min_observations
        
        # Current and historical stint models
        self.current_stint: StintModel | None = None
        self.stint_history: list[StintModel] = []
        
        # Base pace estimate (updated from first stint)
        self.estimated_base_pace: float | None = None
    
    def new_stint(
        self,
        stint_number: int,
        compound: str,
        start_lap: int,
        base_pace: float | None = None,
    ) -> None:
        """
        Start a new stint with a fresh model.
        
        Args:
            stint_number: Stint number (1-indexed)
            compound: Tyre compound for this stint
            start_lap: Race lap where stint starts
            base_pace: Optional known base pace
        """
        # Archive current stint
        if self.current_stint is not None:
            self.current_stint.is_active = False
            self.stint_history.append(self.current_stint)
        
        # Create new RLS estimator
        rls = RLSEstimator(
            n_features=2,  # [intercept, lap_in_stint]
            forgetting_factor=self.forgetting_factor,
        )
        
        # Warm start with priors
        bp = base_pace or self.estimated_base_pace
        warm_base, warm_deg = get_warm_start_params(compound, bp)
        rls.warm_start(warm_base, warm_deg, uncertainty=50.0)
        
        self.current_stint = StintModel(
            stint_number=stint_number,
            compound=compound,
            start_lap=start_lap,
            rls=rls,
        )
    
    def update(
        self,
        lap_in_stint: int,
        lap_time: float,
        is_valid: bool = True,
    ) -> float:
        """
        Update the model with a new lap observation.
        
        Args:
            lap_in_stint: Lap number within current stint
            lap_time: Observed lap time in seconds
            is_valid: Whether this is a valid racing lap
        
        Returns:
            Prediction error (residual)
        """
        if self.current_stint is None:
            # Auto-create stint if needed
            self.new_stint(1, "MEDIUM", 1)
        
        assert self.current_stint is not None
        
        # Record lap time
        self.current_stint.lap_times.append(lap_time)
        
        # Only update model with valid laps
        if not is_valid or lap_time <= 0:
            return 0.0
        
        # Create feature vector
        x = create_feature_vector(lap_in_stint)
        
        # Update RLS
        error = self.current_stint.rls.update(x, lap_time)
        
        # Update base pace estimate
        if self.estimated_base_pace is None:
            self.estimated_base_pace = lap_time
        else:
            # Exponential moving average
            self.estimated_base_pace = 0.9 * self.estimated_base_pace + 0.1 * lap_time
        
        return error
    
    def predict_next_k(self, k: int = 5) -> list[float]:
        """
        Predict lap times for the next k laps.
        
        Returns:
            List of predicted lap times
        """
        if self.current_stint is None:
            return []
        
        rls = self.current_stint.rls
        current_lap = len(self.current_stint.lap_times)
        
        predictions = []
        for i in range(1, k + 1):
            lap_in_stint = current_lap + i
            x = create_feature_vector(lap_in_stint)
            pred = rls.predict(x)
            predictions.append(pred)
        
        return predictions
    
    def get_prediction(self, k: int = 5) -> DegradationPrediction | None:
        """
        Get full prediction output with risk assessment.
        
        Args:
            k: Number of future laps to predict
        
        Returns:
            DegradationPrediction or None if insufficient data
        """
        if self.current_stint is None:
            return None
        
        stint = self.current_stint
        rls = stint.rls
        
        # Get model parameters
        base_pace = rls.get_base_pace()
        deg_slope = rls.get_deg_slope()
        
        # Current lap prediction
        current_lap = len(stint.lap_times)
        x_current = create_feature_vector(current_lap)
        predicted_current = rls.predict(x_current)
        
        # Future predictions
        predicted_next_k = self.predict_next_k(k)
        
        # Calculate cliff risk
        cliff_threshold = get_cliff_risk_threshold(stint.compound)
        cliff_risk = min(1.0, max(0.0, deg_slope / cliff_threshold))
        
        # Model confidence (based on observations and RMSE)
        if rls.n_updates < self.min_observations:
            model_confidence = 0.3 * (rls.n_updates / self.min_observations)
        else:
            rmse = rls.get_rmse()
            # Lower RMSE = higher confidence
            model_confidence = max(0.3, 1.0 - min(1.0, rmse / 2.0))
        
        return DegradationPrediction(
            driver_number=self.driver_number,
            stint_number=stint.stint_number,
            compound=stint.compound,
            base_pace=base_pace,
            deg_slope=deg_slope,
            predicted_current=predicted_current,
            predicted_next_k=predicted_next_k,
            cliff_risk=cliff_risk,
            model_confidence=model_confidence,
            n_observations=rls.n_updates,
        )
    
    def get_deg_slope(self) -> float:
        """Get current degradation slope."""
        if self.current_stint is None:
            return 0.0
        return self.current_stint.rls.get_deg_slope()
    
    def get_cliff_risk(self) -> float:
        """Get current cliff risk score (0-1)."""
        if self.current_stint is None:
            return 0.0
        
        deg_slope = self.get_deg_slope()
        threshold = get_cliff_risk_threshold(self.current_stint.compound)
        return min(1.0, max(0.0, deg_slope / threshold))
    
    def to_dict(self) -> dict:
        """Serialize model state."""
        if self.current_stint is None:
            return {
                "driver_number": self.driver_number,
                "has_model": False,
            }
        
        return {
            "driver_number": self.driver_number,
            "has_model": True,
            "stint_number": self.current_stint.stint_number,
            "compound": self.current_stint.compound,
            "deg_slope": self.get_deg_slope(),
            "cliff_risk": self.get_cliff_risk(),
            "n_observations": self.current_stint.rls.n_updates,
            "rls": self.current_stint.rls.to_dict(),
        }


class ModelManager:
    """
    Manages degradation models for all drivers in a race.
    """
    
    def __init__(self, forgetting_factor: float = 0.95):
        self.forgetting_factor = forgetting_factor
        self.models: dict[int, DriverDegradationModel] = {}
    
    def get_or_create(self, driver_number: int) -> DriverDegradationModel:
        """Get or create model for a driver."""
        if driver_number not in self.models:
            self.models[driver_number] = DriverDegradationModel(
                driver_number=driver_number,
                forgetting_factor=self.forgetting_factor,
            )
        return self.models[driver_number]
    
    def update_driver(
        self,
        driver_number: int,
        lap_in_stint: int,
        lap_time: float,
        stint_number: int,
        compound: str,
        is_valid: bool = True,
    ) -> float:
        """
        Update a driver's model with new lap data.
        
        Handles stint changes automatically.
        """
        model = self.get_or_create(driver_number)
        
        # Check for stint change
        if (
            model.current_stint is None
            or model.current_stint.stint_number != stint_number
        ):
            model.new_stint(stint_number, compound, lap_in_stint)
        
        return model.update(lap_in_stint, lap_time, is_valid)
    
    def get_all_predictions(self, k: int = 5) -> dict[int, DegradationPrediction]:
        """Get predictions for all drivers."""
        predictions = {}
        for driver_num, model in self.models.items():
            pred = model.get_prediction(k)
            if pred:
                predictions[driver_num] = pred
        return predictions
    
    def reset(self) -> None:
        """Reset all models."""
        self.models.clear()
