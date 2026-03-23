"""
Neural Pace Prediction Model — NumPy-only MLP for nonlinear tyre degradation.

Complements the linear RLS estimator by predicting:
- Pace delta corrections for the next k laps (nonlinear cliff shape)
- Cliff probability (0-1)
- Model confidence (0-1)

Architecture: input(11) → Dense(32, ReLU) → Dense(16, ReLU) → output(7)

The model works out of the box with heuristic default weights that encode
tyre physics knowledge. Optional offline training via scripts/train_neural_pace.py
can improve accuracy from historical FastF1 data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

# Compound index mapping for one-hot encoding
COMPOUND_INDEX: dict[str, int] = {
    "SOFT": 0,
    "MEDIUM": 1,
    "HARD": 2,
    "INTERMEDIATE": 3,
    "WET": 4,
}

# Network dimensions
INPUT_DIM = 11
HIDDEN1_DIM = 32
HIDDEN2_DIM = 16
OUTPUT_DIM = 7  # pace_delta[5] + cliff_prob + confidence


@dataclass
class NeuralPrediction:
    """Output from the neural pace model."""

    pace_deltas: list[float]  # Corrections for next k laps (seconds)
    cliff_probability: float  # 0-1 probability of imminent tyre cliff
    confidence: float  # 0-1 model confidence


class NeuralPaceMLP:
    """
    NumPy-only MLP for nonlinear pace prediction.

    Uses a singleton pattern so all driver models share the same weights.
    Total parameters: 11*32+32 + 32*16+16 + 16*7+7 = 1,031.

    Input features (11):
        [0:5]  compound one-hot (SOFT, MEDIUM, HARD, INTER, WET)
        [5]    tyre_age / 50.0 (normalized)
        [6]    rls_deg_slope * 10.0 (scaled to ~O(1))
        [7]    base_pace_delta / 5.0 (from session average)
        [8]    fuel_fraction (0.0 = empty, 1.0 = full)
        [9]    track_temp / 50.0 (normalized)
        [10]   n_observations / 20.0 (capped)

    Output (7):
        [0:5]  pace_delta corrections for next 5 laps
        [5]    cliff_probability (sigmoid applied)
        [6]    confidence (sigmoid applied)
    """

    _instance: NeuralPaceMLP | None = None

    def __init__(self) -> None:
        self.W1: NDArray[np.float64] = np.zeros((INPUT_DIM, HIDDEN1_DIM))
        self.b1: NDArray[np.float64] = np.zeros(HIDDEN1_DIM)
        self.W2: NDArray[np.float64] = np.zeros((HIDDEN1_DIM, HIDDEN2_DIM))
        self.b2: NDArray[np.float64] = np.zeros(HIDDEN2_DIM)
        self.W3: NDArray[np.float64] = np.zeros((HIDDEN2_DIM, OUTPUT_DIM))
        self.b3: NDArray[np.float64] = np.zeros(OUTPUT_DIM)

    @classmethod
    def get_instance(cls) -> NeuralPaceMLP:
        """Get or create the singleton MLP instance with default weights."""
        if cls._instance is None:
            cls._instance = cls.create_default()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None

    @classmethod
    def create_default(cls) -> NeuralPaceMLP:
        """
        Create MLP with heuristic weights derived from tyre physics.

        Encodes knowledge from tyre_model.py:
        - SOFT cliff starts ~lap 15, MEDIUM ~25, HARD ~40
        - Degradation rates: SOFT 0.08, MEDIUM 0.05, HARD 0.03 s/lap
        - Cliff is exponential: 0.1 * (e^(severity * laps_past_cliff) - 1)
        """
        mlp = cls()
        rng = np.random.RandomState(42)

        # Xavier initialization (scaled down for conservative defaults)
        mlp.W1 = rng.randn(INPUT_DIM, HIDDEN1_DIM) * np.sqrt(2.0 / INPUT_DIM) * 0.3
        mlp.b1 = np.zeros(HIDDEN1_DIM)
        mlp.W2 = rng.randn(HIDDEN1_DIM, HIDDEN2_DIM) * np.sqrt(2.0 / HIDDEN1_DIM) * 0.3
        mlp.b2 = np.zeros(HIDDEN2_DIM)
        mlp.W3 = rng.randn(HIDDEN2_DIM, OUTPUT_DIM) * np.sqrt(2.0 / HIDDEN2_DIM) * 0.3
        mlp.b3 = np.zeros(OUTPUT_DIM)

        # --- Encode tyre physics knowledge into weights ---

        # Tyre age (feature 5) → strong activation of cliff-detection neurons
        # Needs to be strong enough to overcome the negative bias on cliff output
        mlp.W1[5, 0:8] += 2.5

        # Compound one-hot modulates cliff threshold:
        # SOFT (idx 0) → lower cliff threshold (activates cliff detectors earlier)
        mlp.W1[0, 0:4] += 1.2
        # MEDIUM (idx 1) → moderate
        mlp.W1[1, 0:4] += 0.5
        # HARD (idx 2) → suppresses cliff detectors (higher threshold)
        mlp.W1[2, 0:4] -= 0.5

        # RLS deg_slope (feature 6) → strong correlation with pace degradation
        mlp.W1[6, 8:16] += 1.5
        # Also connects to cliff detection (high deg_slope → cliff likely)
        mlp.W1[6, 0:4] += 0.8

        # n_observations (feature 10) → confidence-related neurons
        mlp.W1[10, 24:32] += 0.8

        # Strengthen the path from cliff-detecting hidden units to cliff output
        # Hidden units 0-7 are cliff detectors → connect them to output[5] (cliff)
        mlp.W2[0:8, 0:4] += 0.3
        mlp.W3[0:4, 5] += 0.8

        # Output biases:
        # Cliff probability → biased low by default (sigmoid(-3) ≈ 0.05)
        mlp.b3[5] = -3.0
        # Confidence → moderate default (sigmoid(0) = 0.5)
        mlp.b3[6] = 0.0
        # Pace deltas → biased toward zero (no correction)
        mlp.b3[0:5] = 0.0

        return mlp

    @classmethod
    def load(cls, path: str | Path) -> NeuralPaceMLP:
        """Load trained weights from .npz file."""
        mlp = cls()
        data = np.load(str(path))
        mlp.W1 = data["W1"]
        mlp.b1 = data["b1"]
        mlp.W2 = data["W2"]
        mlp.b2 = data["b2"]
        mlp.W3 = data["W3"]
        mlp.b3 = data["b3"]
        cls._instance = mlp
        return mlp

    def save(self, path: str | Path) -> None:
        """Save weights to .npz file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            str(path),
            W1=self.W1,
            b1=self.b1,
            W2=self.W2,
            b2=self.b2,
            W3=self.W3,
            b3=self.b3,
        )

    @staticmethod
    def _relu(x: NDArray[np.float64]) -> NDArray[np.float64]:
        return np.maximum(0, x)

    @staticmethod
    def _sigmoid(x: NDArray[np.float64]) -> NDArray[np.float64]:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -10, 10)))

    def forward(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Forward pass through the network.

        Args:
            x: Input feature vector (11,)

        Returns:
            Output vector (7,): [pace_delta[5], cliff_prob, confidence]
        """
        x = np.asarray(x, dtype=np.float64)

        # Layer 1: input → hidden1
        h1 = self._relu(x @ self.W1 + self.b1)

        # Layer 2: hidden1 → hidden2
        h2 = self._relu(h1 @ self.W2 + self.b2)

        # Output layer: hidden2 → output
        out = h2 @ self.W3 + self.b3

        # Apply sigmoid to cliff_probability and confidence outputs
        out[5] = float(self._sigmoid(np.array([out[5]]))[0])
        out[6] = float(self._sigmoid(np.array([out[6]]))[0])

        return out

    def predict(self, features: NDArray[np.float64]) -> NeuralPrediction:
        """
        Make prediction from feature vector.

        Args:
            features: Normalized input vector (11,)

        Returns:
            NeuralPrediction with pace deltas, cliff probability, confidence
        """
        out = self.forward(features)
        return NeuralPrediction(
            pace_deltas=out[0:5].tolist(),
            cliff_probability=float(out[5]),
            confidence=float(out[6]),
        )

    @property
    def param_count(self) -> int:
        """Total number of trainable parameters."""
        return (
            self.W1.size
            + self.b1.size
            + self.W2.size
            + self.b2.size
            + self.W3.size
            + self.b3.size
        )


def build_feature_vector(
    compound: str,
    tyre_age: int,
    rls_deg_slope: float,
    base_pace_delta: float = 0.0,
    fuel_fraction: float = 0.5,
    track_temp: float = 30.0,
    n_observations: int = 0,
) -> NDArray[np.float64]:
    """
    Build normalized input feature vector for the neural model.

    Args:
        compound: Tyre compound name (SOFT, MEDIUM, HARD, INTERMEDIATE, WET)
        tyre_age: Laps on current set of tyres
        rls_deg_slope: Current RLS degradation slope (s/lap)
        base_pace_delta: Difference from session average pace (s)
        fuel_fraction: Remaining fuel as fraction (0-1)
        track_temp: Track temperature in Celsius
        n_observations: Number of RLS observations in current stint

    Returns:
        Feature vector of shape (11,)
    """
    features = np.zeros(INPUT_DIM, dtype=np.float64)

    # One-hot compound encoding
    idx = COMPOUND_INDEX.get(compound.upper(), 1)  # default MEDIUM
    features[idx] = 1.0

    # Normalized continuous features
    features[5] = min(tyre_age, 60) / 50.0
    features[6] = rls_deg_slope * 10.0  # scale to ~O(1)
    features[7] = np.clip(base_pace_delta, -5.0, 5.0) / 5.0
    features[8] = np.clip(fuel_fraction, 0.0, 1.0)
    features[9] = np.clip(track_temp, 10.0, 60.0) / 50.0
    features[10] = min(n_observations, 20) / 20.0

    return features


class NeuralDegradationModel:
    """
    Per-driver wrapper around the shared MLP singleton.

    Manages session-level context (track temp, fuel, avg pace) and
    provides a clean predict() interface for the blending layer.
    """

    def __init__(self) -> None:
        self._mlp = NeuralPaceMLP.get_instance()
        self._track_temp: float = 30.0
        self._fuel_total_laps: int = 57
        self._session_avg_pace: float = 90.0

    def set_session_context(
        self,
        track_temp: float = 30.0,
        total_laps: int = 57,
        session_avg_pace: float = 90.0,
    ) -> None:
        """Set session-level context that doesn't change per lap."""
        self._track_temp = track_temp
        self._fuel_total_laps = total_laps
        self._session_avg_pace = session_avg_pace

    def predict(
        self,
        compound: str,
        tyre_age: int,
        rls_deg_slope: float,
        base_pace: float,
        race_lap: int,
        n_observations: int,
        k: int = 5,
    ) -> NeuralPrediction:
        """
        Get neural prediction for current driver state.

        Args:
            compound: Current tyre compound
            tyre_age: Laps on current set
            rls_deg_slope: Current RLS degradation slope
            base_pace: RLS base pace estimate
            race_lap: Current race lap number
            n_observations: RLS observation count in current stint
            k: Number of future laps to predict (max 5)

        Returns:
            NeuralPrediction with pace deltas, cliff prob, confidence
        """
        fuel_fraction = max(0.0, 1.0 - race_lap / max(1, self._fuel_total_laps))
        base_pace_delta = base_pace - self._session_avg_pace

        features = build_feature_vector(
            compound=compound,
            tyre_age=tyre_age,
            rls_deg_slope=rls_deg_slope,
            base_pace_delta=base_pace_delta,
            fuel_fraction=fuel_fraction,
            track_temp=self._track_temp,
            n_observations=n_observations,
        )

        prediction = self._mlp.predict(features)

        # Truncate pace_deltas to requested k
        if k < 5:
            prediction = NeuralPrediction(
                pace_deltas=prediction.pace_deltas[:k],
                cliff_probability=prediction.cliff_probability,
                confidence=prediction.confidence,
            )

        return prediction
