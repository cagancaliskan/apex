"""
Tests for Feature #3: Neural Pace Prediction — Hybrid RLS + Neural Ensemble.

Tests the NumPy-only MLP, feature vector construction, blending logic,
and integration with the existing DriverDegradationModel.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from rsw.models.degradation.neural_model import (
    COMPOUND_INDEX,
    INPUT_DIM,
    NeuralDegradationModel,
    NeuralPaceMLP,
    NeuralPrediction,
    build_feature_vector,
)
from rsw.models.degradation.online_model import (
    DegradationPrediction,
    DriverDegradationModel,
    ModelManager,
)


# ============================================================================
# NeuralPaceMLP Tests
# ============================================================================


class TestNeuralPaceMLP:
    """Tests for the core MLP model."""

    def setup_method(self) -> None:
        NeuralPaceMLP.reset_instance()

    def test_forward_output_shape(self) -> None:
        mlp = NeuralPaceMLP.create_default()
        x = np.zeros(INPUT_DIM)
        out = mlp.forward(x)
        assert out.shape == (7,)

    def test_sigmoid_outputs_bounded(self) -> None:
        """Cliff probability and confidence must be in [0, 1]."""
        mlp = NeuralPaceMLP.create_default()
        rng = np.random.RandomState(123)
        for _ in range(50):
            x = rng.randn(INPUT_DIM) * 2.0
            out = mlp.forward(x)
            assert 0.0 <= out[5] <= 1.0, f"cliff_prob out of bounds: {out[5]}"
            assert 0.0 <= out[6] <= 1.0, f"confidence out of bounds: {out[6]}"

    def test_pace_deltas_near_zero_young_tyres(self) -> None:
        """Fresh tyres should produce small pace corrections."""
        mlp = NeuralPaceMLP.create_default()
        features = build_feature_vector(
            compound="MEDIUM",
            tyre_age=2,
            rls_deg_slope=0.05,
            base_pace_delta=0.0,
            fuel_fraction=0.9,
            track_temp=30.0,
            n_observations=2,
        )
        pred = mlp.predict(features)
        for delta in pred.pace_deltas:
            assert abs(delta) < 3.0, f"Pace delta too large for young tyres: {delta}"

    def test_cliff_probability_increases_with_age(self) -> None:
        """Cliff probability should generally increase as tyres age (SOFT)."""
        mlp = NeuralPaceMLP.create_default()
        probs = []
        for age in [5, 15, 25, 40]:
            features = build_feature_vector(
                compound="SOFT",
                tyre_age=age,
                rls_deg_slope=0.08 + age * 0.002,  # slope increases with age
                base_pace_delta=0.0,
                fuel_fraction=0.5,
                track_temp=30.0,
                n_observations=age,
            )
            pred = mlp.predict(features)
            probs.append(pred.cliff_probability)
        # The trend should be increasing (allow some non-monotonicity due to heuristic weights)
        assert probs[-1] > probs[0], (
            f"Cliff prob should increase with age: {probs}"
        )

    def test_param_count(self) -> None:
        mlp = NeuralPaceMLP.create_default()
        expected = 11 * 32 + 32 + 32 * 16 + 16 + 16 * 7 + 7
        assert mlp.param_count == expected, (
            f"Expected {expected} params, got {mlp.param_count}"
        )

    def test_save_load_roundtrip(self) -> None:
        mlp = NeuralPaceMLP.create_default()
        features = build_feature_vector("SOFT", 10, 0.08)
        pred_before = mlp.predict(features)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_weights.npz"
            mlp.save(path)
            assert path.exists()

            NeuralPaceMLP.reset_instance()
            loaded = NeuralPaceMLP.load(path)
            pred_after = loaded.predict(features)

        np.testing.assert_allclose(
            pred_before.pace_deltas, pred_after.pace_deltas, atol=1e-10
        )
        assert abs(pred_before.cliff_probability - pred_after.cliff_probability) < 1e-10
        assert abs(pred_before.confidence - pred_after.confidence) < 1e-10

    def test_singleton_returns_same_instance(self) -> None:
        a = NeuralPaceMLP.get_instance()
        b = NeuralPaceMLP.get_instance()
        assert a is b

    def test_predict_returns_neural_prediction(self) -> None:
        mlp = NeuralPaceMLP.create_default()
        features = build_feature_vector("MEDIUM", 10, 0.05)
        pred = mlp.predict(features)
        assert isinstance(pred, NeuralPrediction)
        assert len(pred.pace_deltas) == 5
        assert isinstance(pred.cliff_probability, float)
        assert isinstance(pred.confidence, float)


# ============================================================================
# Feature Vector Tests
# ============================================================================


class TestBuildFeatureVector:
    def test_output_shape_11(self) -> None:
        fv = build_feature_vector("MEDIUM", 10, 0.05)
        assert fv.shape == (11,)

    def test_compound_onehot_correct(self) -> None:
        for compound, idx in COMPOUND_INDEX.items():
            fv = build_feature_vector(compound, 10, 0.05)
            assert fv[idx] == 1.0
            # All other compound positions should be 0
            for other_idx in range(5):
                if other_idx != idx:
                    assert fv[other_idx] == 0.0

    def test_normalization_ranges(self) -> None:
        """All features should be roughly in reasonable ranges."""
        fv = build_feature_vector(
            compound="SOFT",
            tyre_age=30,
            rls_deg_slope=0.1,
            base_pace_delta=2.0,
            fuel_fraction=0.5,
            track_temp=40.0,
            n_observations=15,
        )
        # Continuous features (indices 5-10) should be roughly in [-2, 2]
        for i in range(5, 11):
            assert -2.5 <= fv[i] <= 2.5, f"Feature {i} out of range: {fv[i]}"

    def test_unknown_compound_defaults_to_medium(self) -> None:
        fv = build_feature_vector("UNKNOWN_COMPOUND", 10, 0.05)
        assert fv[1] == 1.0  # MEDIUM index


# ============================================================================
# NeuralDegradationModel Tests
# ============================================================================


class TestNeuralDegradationModel:
    def setup_method(self) -> None:
        NeuralPaceMLP.reset_instance()

    def test_predict_returns_neural_prediction(self) -> None:
        model = NeuralDegradationModel()
        pred = model.predict(
            compound="SOFT",
            tyre_age=10,
            rls_deg_slope=0.08,
            base_pace=90.0,
            race_lap=15,
            n_observations=10,
        )
        assert isinstance(pred, NeuralPrediction)
        assert len(pred.pace_deltas) == 5

    def test_session_context_affects_output(self) -> None:
        model = NeuralDegradationModel()
        model.set_session_context(track_temp=25.0, total_laps=57, session_avg_pace=90.0)
        pred1 = model.predict("SOFT", 20, 0.1, 91.0, 30, 15)

        model.set_session_context(track_temp=45.0, total_laps=57, session_avg_pace=90.0)
        pred2 = model.predict("SOFT", 20, 0.1, 91.0, 30, 15)

        # Different track temp should produce different predictions
        assert pred1.pace_deltas != pred2.pace_deltas or pred1.cliff_probability != pred2.cliff_probability

    def test_fuel_fraction_decreases_with_race_lap(self) -> None:
        model = NeuralDegradationModel()
        model.set_session_context(total_laps=57)

        # Early race: high fuel
        pred_early = model.predict("MEDIUM", 5, 0.05, 90.0, 5, 5)
        # Late race: low fuel
        pred_late = model.predict("MEDIUM", 5, 0.05, 90.0, 50, 5)

        # Should produce different outputs due to fuel fraction difference
        assert pred_early.pace_deltas != pred_late.pace_deltas

    def test_truncate_pace_deltas(self) -> None:
        model = NeuralDegradationModel()
        pred = model.predict("MEDIUM", 10, 0.05, 90.0, 15, 10, k=3)
        assert len(pred.pace_deltas) == 3


# ============================================================================
# Blending Tests (via DriverDegradationModel)
# ============================================================================


class TestBlending:
    """Test the RLS + Neural blending in DriverDegradationModel."""

    def setup_method(self) -> None:
        NeuralPaceMLP.reset_instance()

    def _create_model_with_data(
        self, n_laps: int = 10, compound: str = "MEDIUM"
    ) -> DriverDegradationModel:
        """Create a model, enable neural, and feed it some laps."""
        model = DriverDegradationModel(driver_number=1)
        model.new_stint(1, compound, 1)
        model.set_session_context(track_temp=30.0, total_laps=57, session_avg_pace=90.0)

        # Feed realistic lap data
        for i in range(1, n_laps + 1):
            lap_time = 90.0 + 0.05 * i  # linear degradation
            model.update(lap_in_stint=i, lap_time=lap_time, is_valid=True, race_lap=i)

        return model

    def test_alpha_high_for_young_tyres(self) -> None:
        model = self._create_model_with_data(n_laps=5)
        alpha = model._compute_blend_alpha(tyre_age=5, n_observations=5)
        assert alpha >= 0.85

    def test_alpha_low_for_old_tyres(self) -> None:
        model = self._create_model_with_data(n_laps=10)
        alpha = model._compute_blend_alpha(tyre_age=30, n_observations=25)
        assert alpha <= 0.30

    def test_alpha_decreases_monotonically(self) -> None:
        model = self._create_model_with_data(n_laps=10)
        alphas = [
            model._compute_blend_alpha(tyre_age=age, n_observations=age)
            for age in range(10, 30)
        ]
        for i in range(1, len(alphas)):
            assert alphas[i] <= alphas[i - 1], (
                f"Alpha increased at age {10+i}: {alphas[i]} > {alphas[i-1]}"
            )

    def test_cliff_risk_uses_max_of_rls_and_neural(self) -> None:
        """Cliff risk should be conservative: max(rls, neural)."""
        model = self._create_model_with_data(n_laps=15, compound="SOFT")
        pred = model.get_prediction(k=5)
        assert pred is not None

        # Get RLS-only cliff risk for comparison
        rls = model.current_stint.rls
        from rsw.models.degradation.calibration import get_cliff_risk_threshold

        rls_cliff = min(1.0, max(0.0, rls.get_deg_slope() / get_cliff_risk_threshold("SOFT")))

        # Blended cliff_risk should be >= RLS cliff risk
        assert pred.cliff_risk >= rls_cliff - 0.01  # small tolerance

    def test_blended_prediction_structure_unchanged(self) -> None:
        """DegradationPrediction fields should all be present."""
        model = self._create_model_with_data(n_laps=10)
        pred = model.get_prediction(k=5)
        assert pred is not None
        assert isinstance(pred, DegradationPrediction)
        assert pred.driver_number == 1
        assert pred.stint_number == 1
        assert pred.compound == "MEDIUM"
        assert isinstance(pred.base_pace, float)
        assert isinstance(pred.deg_slope, float)
        assert isinstance(pred.predicted_current, float)
        assert len(pred.predicted_next_k) == 5
        assert 0.0 <= pred.cliff_risk <= 1.0
        assert 0.0 <= pred.model_confidence <= 1.0
        assert pred.n_observations == 10

    def test_pure_rls_when_no_neural_model(self) -> None:
        """Without set_session_context(), predictions should be pure RLS."""
        model = DriverDegradationModel(driver_number=1)
        model.new_stint(1, "MEDIUM", 1)
        # Do NOT call set_session_context

        for i in range(1, 11):
            model.update(lap_in_stint=i, lap_time=90.0 + 0.05 * i, is_valid=True, race_lap=i)

        pred = model.get_prediction(k=5)
        assert pred is not None
        # Should work fine without neural model
        assert isinstance(pred, DegradationPrediction)
        assert len(pred.predicted_next_k) == 5


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    def setup_method(self) -> None:
        NeuralPaceMLP.reset_instance()

    def test_model_manager_with_neural_blending(self) -> None:
        """ModelManager should work with neural-enabled models."""
        mgr = ModelManager(forgetting_factor=0.95)

        # Update a driver
        for i in range(1, 11):
            mgr.update_driver(
                driver_number=44,
                lap_in_stint=i,
                lap_time=91.0 + 0.06 * i,
                stint_number=1,
                compound="SOFT",
                is_valid=True,
                race_lap=i,
            )

        # Enable neural for this driver
        model = mgr.get_or_create(44)
        model.set_session_context(track_temp=35.0, total_laps=57, session_avg_pace=91.0)

        predictions = mgr.get_all_predictions(k=5)
        assert 44 in predictions
        pred = predictions[44]
        assert isinstance(pred, DegradationPrediction)
        assert len(pred.predicted_next_k) == 5

    def test_prediction_near_cliff(self) -> None:
        """Neural model should contribute when tyres are old (near cliff)."""
        model = DriverDegradationModel(driver_number=16)
        model.new_stint(1, "SOFT", 1)
        model.set_session_context(track_temp=30.0, total_laps=57, session_avg_pace=90.0)

        # Feed 20 laps (SOFT cliff starts ~lap 15 in physics model)
        for i in range(1, 21):
            # Simulate accelerating degradation near cliff
            deg = 0.08 * i + (0.02 * max(0, i - 15) ** 1.5)
            model.update(lap_in_stint=i, lap_time=90.0 + deg, is_valid=True, race_lap=i)

        pred = model.get_prediction(k=5)
        assert pred is not None
        # With 20 laps on SOFT, cliff risk should be elevated
        assert pred.cliff_risk > 0.3, f"Cliff risk too low at lap 20 on SOFT: {pred.cliff_risk}"

    def test_multiple_stints_with_neural(self) -> None:
        """Neural model should work across stint transitions."""
        model = DriverDegradationModel(driver_number=1)

        # Stint 1: SOFT with cliff-level degradation
        model.new_stint(1, "SOFT", 1)
        model.set_session_context(track_temp=30.0, total_laps=57, session_avg_pace=90.0)
        for i in range(1, 16):
            model.update(lap_in_stint=i, lap_time=90.0 + 0.10 * i, is_valid=True, race_lap=i)
        pred1 = model.get_prediction(k=5)

        # Stint 2: HARD — fresh tyres, start from scratch
        # Feed enough laps (20) with very low deg so RLS converges away from warm-start
        model.new_stint(2, "HARD", 16)
        for i in range(1, 21):
            model.update(lap_in_stint=i, lap_time=91.2 + 0.01 * i, is_valid=True, race_lap=15 + i)
        pred2 = model.get_prediction(k=5)

        assert pred1 is not None
        assert pred2 is not None
        assert isinstance(pred1, DegradationPrediction)
        assert isinstance(pred2, DegradationPrediction)
        # HARD with 20 laps of 0.01 deg should converge to low cliff risk
        assert pred2.cliff_risk < pred1.cliff_risk, (
            f"HARD cliff_risk={pred2.cliff_risk} should be < SOFT cliff_risk={pred1.cliff_risk}"
        )
