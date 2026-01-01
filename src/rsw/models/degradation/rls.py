"""
Recursive Least Squares (RLS) estimator for online linear regression.

RLS is ideal for F1 tyre degradation modeling because:
1. Updates incrementally with each new lap (no batch retraining)
2. Forgetting factor allows adaptation to changing conditions
3. Provides parameter uncertainty estimates
4. Computationally efficient (O(n²) per update, where n = features)

Model: lap_time = base_pace + deg_slope * lap_in_stint + noise
"""

import numpy as np
from numpy.typing import NDArray


class RLSEstimator:
    """
    Recursive Least Squares estimator with forgetting factor.
    
    The forgetting factor (λ) controls how much weight is given to
    recent vs. historical observations:
    - λ = 1.0: All observations weighted equally
    - λ = 0.95: Recent observations weighted more heavily
    - λ = 0.90: Strong recency bias (faster adaptation)
    
    Example:
        >>> rls = RLSEstimator(n_features=2, forgetting_factor=0.95)
        >>> # Update with (lap_in_stint, lap_time) observations
        >>> rls.update(np.array([1, 1]), 92.5)  # [intercept, lap_in_stint]
        >>> rls.update(np.array([1, 2]), 92.6)
        >>> rls.update(np.array([1, 3]), 92.8)
        >>> # Predict lap time at lap 5 in stint
        >>> predicted = rls.predict(np.array([1, 5]))
    """
    
    def __init__(
        self,
        n_features: int = 2,
        forgetting_factor: float = 0.95,
        initial_covariance: float = 1000.0,
        regularization: float = 1e-6,
    ):
        """
        Initialize the RLS estimator.
        
        Args:
            n_features: Number of features (including bias/intercept term)
            forgetting_factor: Lambda value (0.9-1.0 typical)
            initial_covariance: Initial P matrix diagonal value
            regularization: Small value for numerical stability
        """
        self.n_features = n_features
        self.lambda_ = forgetting_factor
        self.reg = regularization
        
        # Parameter vector (weights)
        self.theta: NDArray[np.float64] = np.zeros(n_features)
        
        # Covariance matrix (inverse of weighted autocorrelation)
        self.P: NDArray[np.float64] = np.eye(n_features) * initial_covariance
        
        # Tracking
        self.n_updates = 0
        self.residual_sum = 0.0
        self._last_residual = 0.0
    
    def update(self, x: NDArray[np.float64], y: float) -> float:
        """
        Update the model with a new observation.
        
        Args:
            x: Feature vector [1, lap_in_stint] or similar
            y: Target value (lap time)
        
        Returns:
            Prediction error (residual) for this observation
        """
        x = np.asarray(x, dtype=np.float64)
        
        # Prediction before update
        y_pred = self.predict(x)
        error = y - y_pred
        
        # Kalman gain
        Px = self.P @ x
        denom = self.lambda_ + x @ Px
        K = Px / (denom + self.reg)
        
        # Update parameters
        self.theta = self.theta + K * error
        
        # Update covariance matrix
        self.P = (self.P - np.outer(K, x @ self.P)) / self.lambda_
        
        # Ensure numerical stability
        self.P = (self.P + self.P.T) / 2  # Symmetrize
        self.P += np.eye(self.n_features) * self.reg  # Regularize
        
        # Track statistics
        self.n_updates += 1
        self.residual_sum += error ** 2
        self._last_residual = error
        
        return error
    
    def predict(self, x: NDArray[np.float64]) -> float:
        """
        Predict target value for a feature vector.
        
        Args:
            x: Feature vector
        
        Returns:
            Predicted value
        """
        x = np.asarray(x, dtype=np.float64)
        return float(self.theta @ x)
    
    def predict_with_uncertainty(
        self, x: NDArray[np.float64]
    ) -> tuple[float, float]:
        """
        Predict with uncertainty estimate.
        
        Returns:
            Tuple of (prediction, std_dev)
        """
        x = np.asarray(x, dtype=np.float64)
        pred = float(self.theta @ x)
        
        # Prediction variance
        var = float(x @ self.P @ x)
        std = np.sqrt(max(0, var))
        
        return pred, std
    
    def params(self) -> NDArray[np.float64]:
        """Get current parameter estimates [intercept, slope, ...]."""
        return self.theta.copy()
    
    def get_base_pace(self) -> float:
        """Get estimated base pace (intercept)."""
        return float(self.theta[0])
    
    def get_deg_slope(self) -> float:
        """Get estimated degradation slope (seconds per lap)."""
        if self.n_features >= 2:
            return float(self.theta[1])
        return 0.0
    
    def get_rmse(self) -> float:
        """Get root mean squared error of updates."""
        if self.n_updates == 0:
            return 0.0
        return float(np.sqrt(self.residual_sum / self.n_updates))
    
    def reset(self, initial_covariance: float = 1000.0) -> None:
        """Reset the estimator to initial state."""
        self.theta = np.zeros(self.n_features)
        self.P = np.eye(self.n_features) * initial_covariance
        self.n_updates = 0
        self.residual_sum = 0.0
        self._last_residual = 0.0
    
    def warm_start(
        self,
        base_pace: float,
        deg_slope: float,
        uncertainty: float = 10.0,
    ) -> None:
        """
        Initialize with prior estimates (warm start).
        
        Useful for starting with historical/expected degradation rates.
        
        Args:
            base_pace: Expected base lap time
            deg_slope: Expected degradation per lap
            uncertainty: How uncertain we are about these priors
        """
        self.theta[0] = base_pace
        if self.n_features >= 2:
            self.theta[1] = deg_slope
        
        # Set covariance based on uncertainty
        self.P = np.eye(self.n_features) * uncertainty
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "theta": self.theta.tolist(),
            "n_updates": self.n_updates,
            "rmse": self.get_rmse(),
            "base_pace": self.get_base_pace(),
            "deg_slope": self.get_deg_slope(),
        }


def create_feature_vector(lap_in_stint: int, track_evolution: float = 0.0) -> NDArray:
    """
    Create feature vector for RLS model.
    
    Basic model: [1, lap_in_stint] for y = base + slope * x
    Extended model: [1, lap_in_stint, track_evolution] for rubber buildup
    """
    return np.array([1.0, float(lap_in_stint)])
