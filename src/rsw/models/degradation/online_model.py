"""
Online degradation model manager for per-driver performance tracking.

This module manages RLS models for each driver's current stint,
providing pace predictions and cliff risk assessment.
"""

from dataclasses import dataclass, field
from datetime import datetime

from rsw.config.constants import DEFAULT_FORGETTING_FACTOR, TRACK_PRIORS_CONFIDENCE_THRESHOLD
from rsw.models.physics.fuel_model import FuelModel

from .calibration import get_cliff_risk_threshold, get_warm_start_params
from .rls import RLSEstimator, create_feature_vector


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
        forgetting_factor: float = DEFAULT_FORGETTING_FACTOR,
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

        # Fuel model for correcting lap times before RLS update
        self.fuel_model = FuelModel()

        # Neural model for nonlinear cliff prediction (Feature #3)
        self._neural_model: "NeuralDegradationModel | None" = None

    def new_stint(
        self,
        stint_number: int,
        compound: str,
        start_lap: int,
        base_pace: float | None = None,
        season_priors: tuple[float | None, float | None] | None = None,
        track_priors: "ResolvedPriors | None" = None,
    ) -> None:
        """
        Start a new stint with a fresh model.

        Args:
            stint_number: Stint number (1-indexed)
            compound: Tyre compound for this stint
            start_lap: Race lap where stint starts
            base_pace: Optional known base pace
            season_priors: Optional (base_pace, deg_slope) from SeasonLearner
                          — overrides generic compound defaults when available
            track_priors: Optional ResolvedPriors from track_priors module
                         — used when season_priors unavailable
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

        # Warm start priority: season_priors > track_priors > static defaults
        bp = base_pace or self.estimated_base_pace
        if season_priors and season_priors[0] is not None:
            warm_base = season_priors[0]
            warm_deg = season_priors[1] if season_priors[1] is not None else get_warm_start_params(compound, bp)[1]
            # Lower uncertainty — we have cross-session data
            rls.warm_start(warm_base, warm_deg, uncertainty=20.0)
        elif track_priors is not None and track_priors.confidence > TRACK_PRIORS_CONFIDENCE_THRESHOLD:
            from .calibration import get_track_aware_warm_start
            warm_base, warm_deg = get_track_aware_warm_start(compound, track_priors, bp)
            # Medium uncertainty — track-level data, not driver-specific
            rls.warm_start(warm_base, warm_deg, uncertainty=30.0)
        else:
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
        race_lap: int | None = None,
    ) -> float:
        """
        Update the model with a new lap observation.

        Applies fuel correction before feeding into RLS so the model
        learns pure tyre degradation, not fuel-burn improvement.

        Args:
            lap_in_stint: Lap number within current stint
            lap_time: Observed lap time in seconds
            is_valid: Whether this is a valid racing lap
            race_lap: Absolute race lap number (for fuel correction)

        Returns:
            Prediction error (residual)
        """
        if self.current_stint is None:
            # Auto-create stint if needed
            self.new_stint(1, "MEDIUM", 1)

        assert self.current_stint is not None

        # Record raw lap time
        self.current_stint.lap_times.append(lap_time)

        # Only update model with valid laps
        if not is_valid or lap_time <= 0:
            return 0.0

        # --- Fuel correction ---
        # Subtract fuel time penalty so RLS learns pure tyre degradation.
        # Without this, the ~0.035s/kg × fuel_mass improvement each lap
        # gets conflated with degradation, making deg_slope systematically wrong.
        corrected_time = lap_time
        if race_lap is not None and race_lap > 0:
            fuel_penalty = self.fuel_model.get_fuel_penalty(race_lap)
            corrected_time = lap_time - fuel_penalty

        # Create feature vector
        x = create_feature_vector(lap_in_stint)

        # Update RLS with fuel-corrected time
        error = self.current_stint.rls.update(x, corrected_time)

        # Update base pace estimate (use corrected time)
        if self.estimated_base_pace is None:
            self.estimated_base_pace = corrected_time
        else:
            # Exponential moving average
            self.estimated_base_pace = 0.9 * self.estimated_base_pace + 0.1 * corrected_time

        return error

    def set_session_context(
        self,
        track_temp: float = 30.0,
        total_laps: int = 57,
        session_avg_pace: float = 90.0,
    ) -> None:
        """
        Set session context and enable the neural blending model.

        Should be called once per session from the simulation/live service.
        Without this call, predictions remain pure RLS (backward-compatible).
        """
        from .neural_model import NeuralDegradationModel

        if self._neural_model is None:
            self._neural_model = NeuralDegradationModel()
        self._neural_model.set_session_context(track_temp, total_laps, session_avg_pace)

    def _compute_blend_alpha(self, tyre_age: int, n_observations: int) -> float:
        """
        Compute blending weight for RLS vs neural predictions.

        Returns alpha where: blended = alpha * rls + (1 - alpha) * neural_adjusted
        Higher alpha → more RLS weight (young tyres, sparse data)
        Lower alpha → more neural weight (old tyres, approaching cliff)
        """
        # Very sparse data → trust RLS warm-start priors
        if n_observations < 3:
            return 0.95
        # Early stint → RLS dominant
        if n_observations <= 8:
            return 0.85
        if tyre_age <= 8:
            return 0.85
        # Old tyres → neural dominant (handles cliff shape)
        if tyre_age >= 25:
            return 0.30
        # Linear ramp between 8 and 25
        t = (tyre_age - 8) / (25 - 8)
        return 0.85 - t * (0.85 - 0.30)

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

        Uses hybrid RLS + Neural ensemble when neural model is enabled:
        - RLS handles linear degradation (dominant for young tyres)
        - Neural MLP handles nonlinear cliff prediction (dominant for old tyres)
        - Blending alpha transitions from RLS-dominant to neural-dominant

        Args:
            k: Number of future laps to predict

        Returns:
            DegradationPrediction or None if insufficient data
        """
        if self.current_stint is None:
            return None

        stint = self.current_stint
        rls = stint.rls

        # Get RLS model parameters
        base_pace = rls.get_base_pace()
        deg_slope = rls.get_deg_slope()

        # Current lap prediction
        current_lap = len(stint.lap_times)
        x_current = create_feature_vector(current_lap)
        predicted_current = rls.predict(x_current)

        # RLS future predictions
        rls_next_k = self.predict_next_k(k)

        # RLS cliff risk
        cliff_threshold = get_cliff_risk_threshold(stint.compound)
        rls_cliff_risk = min(1.0, max(0.0, deg_slope / cliff_threshold))

        # RLS model confidence (EMA-based RMSE)
        if rls.n_updates < self.min_observations:
            rls_confidence = 0.3 * (rls.n_updates / self.min_observations)
        else:
            rmse = rls.get_recent_rmse()
            rls_confidence = max(0.3, 1.0 - min(1.0, rmse / 2.0))

        # --- Neural blending (Feature #3) ---
        if self._neural_model is not None and current_lap > 0:
            neural_pred = self._neural_model.predict(
                compound=stint.compound,
                tyre_age=current_lap,
                rls_deg_slope=deg_slope,
                base_pace=base_pace,
                race_lap=stint.start_lap + current_lap,
                n_observations=rls.n_updates,
                k=k,
            )

            alpha = self._compute_blend_alpha(current_lap, rls.n_updates)

            # Blend predictions: neural provides corrections on top of RLS
            predicted_next_k = []
            for i, rls_pred in enumerate(rls_next_k):
                if i < len(neural_pred.pace_deltas):
                    neural_correction = neural_pred.pace_deltas[i]
                    blended = alpha * rls_pred + (1 - alpha) * (rls_pred + neural_correction)
                    predicted_next_k.append(blended)
                else:
                    predicted_next_k.append(rls_pred)

            # Cliff risk: conservative (max of both sources)
            cliff_risk = max(rls_cliff_risk, neural_pred.cliff_probability)

            # Confidence: weighted average
            model_confidence = alpha * rls_confidence + (1 - alpha) * neural_pred.confidence
        else:
            # Pure RLS mode (no neural model enabled)
            predicted_next_k = rls_next_k
            cliff_risk = rls_cliff_risk
            model_confidence = rls_confidence

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

    def __init__(self, forgetting_factor: float = DEFAULT_FORGETTING_FACTOR):
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
        race_lap: int | None = None,
        season_priors: tuple[float | None, float | None] | None = None,
        track_priors: "ResolvedPriors | None" = None,
    ) -> float:
        """
        Update a driver's model with new lap data.

        Handles stint changes automatically.

        Args:
            race_lap: Absolute race lap number (for fuel correction)
            season_priors: Optional (base_pace, deg_slope) from SeasonLearner
            track_priors: Optional ResolvedPriors from track_priors module
        """
        model = self.get_or_create(driver_number)

        # Check for stint change
        if model.current_stint is None or model.current_stint.stint_number != stint_number:
            model.new_stint(
                stint_number, compound, lap_in_stint,
                season_priors=season_priors, track_priors=track_priors,
            )

        return model.update(lap_in_stint, lap_time, is_valid, race_lap=race_lap)

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
