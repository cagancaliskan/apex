"""
Tests for P0 fuel correction, P1 SensitivityAnalyzer, P1 SeasonLearner,
P1 circuit SC curves, and weather→strategy integration.
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from rsw.models.degradation.online_model import DriverDegradationModel, ModelManager
from rsw.models.physics.fuel_model import FuelModel
from rsw.strategy.decision import evaluate_strategy
from rsw.strategy.monte_carlo import CIRCUIT_SC_RATES, get_circuit_sc_probability
from rsw.strategy.sensitivity import SensitivityAnalyzer


# =============================================================================
# P0: Fuel Correction Tests
# =============================================================================


class TestFuelCorrection:
    """Test that RLS learns from fuel-corrected lap times."""

    def test_fuel_penalty_subtracted(self):
        """RLS should see corrected times, not raw."""
        model = DriverDegradationModel(driver_number=44)
        model.new_stint(stint_number=1, compound="SOFT", start_lap=1)

        # Feed raw lap times that decrease due to fuel burn
        fuel = FuelModel()
        raw_times = [90.0, 89.9, 89.8, 89.7, 89.6]  # Getting faster (fuel burn)

        for i, t in enumerate(raw_times):
            race_lap = i + 1
            model.update(lap_in_stint=i + 1, lap_time=t, race_lap=race_lap)

        # The model should have a base pace close to the fuel-corrected value
        # rather than the raw value
        assert model.estimated_base_pace is not None
        fuel_pen_lap1 = fuel.get_fuel_penalty(1)
        fuel_pen_lap5 = fuel.get_fuel_penalty(5)
        # Base pace should be adjusted — not the raw 90.0
        assert model.estimated_base_pace != 90.0

    def test_fuel_correction_without_race_lap(self):
        """When race_lap is None, no correction applied (backward compatible)."""
        model = DriverDegradationModel(driver_number=1)
        model.new_stint(stint_number=1, compound="MEDIUM", start_lap=1)

        # Without race_lap, raw time should be used
        error = model.update(lap_in_stint=1, lap_time=90.0, race_lap=None)
        assert model.estimated_base_pace == 90.0

    def test_model_manager_passes_race_lap(self):
        """ModelManager.update_driver should forward race_lap."""
        mgr = ModelManager()
        mgr.update_driver(
            driver_number=44,
            lap_in_stint=1,
            lap_time=90.0,
            stint_number=1,
            compound="SOFT",
            race_lap=5,
        )
        model = mgr.models[44]
        assert model.current_stint is not None
        assert len(model.current_stint.lap_times) == 1


# =============================================================================
# P1: Sensitivity Analyzer Tests
# =============================================================================


class TestSensitivityAnalyzer:
    """Test the explainability engine."""

    @pytest.fixture
    def analyzer(self):
        return SensitivityAnalyzer()

    @pytest.fixture
    def base_params(self):
        return {
            "driver_number": 44,
            "current_lap": 25,
            "total_laps": 50,
            "current_position": 3,
            "deg_slope": 0.06,
            "cliff_risk": 0.4,
            "current_pace": 92.0,
            "tyre_age": 15,
            "compound": "SOFT",
            "pit_loss": 22.0,
        }

    def test_returns_top_factors(self, analyzer, base_params):
        result = analyzer.analyze(**base_params)
        assert len(result.top_factors) > 0
        assert len(result.top_factors) <= 3
        for f in result.top_factors:
            assert 0 <= f.score <= 1
            assert f.direction in ("positive", "negative")

    def test_sensitivity_covers_all_params(self, analyzer, base_params):
        result = analyzer.analyze(**base_params)
        param_names = {s.param_name for s in result.sensitivity}
        assert "pit_loss" in param_names
        assert "deg_slope" in param_names
        assert "cliff_risk" in param_names

    def test_sensitivity_delta_non_negative(self, analyzer, base_params):
        result = analyzer.analyze(**base_params)
        for s in result.sensitivity:
            assert s.confidence_delta >= 0

    def test_to_dict_serializable(self, analyzer, base_params):
        result = analyzer.analyze(**base_params)
        d = result.to_dict()
        # Should be JSON-serializable
        json_str = json.dumps(d)
        assert len(json_str) > 50

    def test_what_if_scenarios_generated(self, analyzer, base_params):
        result = analyzer.analyze(**base_params)
        # May or may not have what-if scenarios depending on sensitivity
        assert isinstance(result.what_if_scenarios, list)


# =============================================================================
# P1: Circuit SC Probability Tests
# =============================================================================


class TestCircuitSCProbability:
    """Test circuit-specific safety car probability model."""

    def test_known_circuit_higher_than_default(self):
        """Monaco should have higher SC probability than generic."""
        monaco_p = get_circuit_sc_probability("monaco", 10, 50)
        generic_p = get_circuit_sc_probability("unknown_circuit", 10, 50)
        assert monaco_p > generic_p

    def test_lap1_higher_probability(self):
        """SC probability should be higher on lap 1 than mid-race."""
        p_lap1 = get_circuit_sc_probability("bahrain", 1, 50)
        p_lap25 = get_circuit_sc_probability("bahrain", 25, 50)
        assert p_lap1 > p_lap25

    def test_wet_weather_multiplier(self):
        """Wet conditions should increase SC probability."""
        p_dry = get_circuit_sc_probability("spa", 10, 50, is_wet=False)
        p_wet = get_circuit_sc_probability("spa", 10, 50, is_wet=True)
        assert p_wet > p_dry

    def test_capped_at_15_percent(self):
        """Per-lap probability should never exceed 15%."""
        p = get_circuit_sc_probability("monaco", 1, 50, is_wet=True)
        assert p <= 0.15

    def test_all_circuits_have_valid_rates(self):
        """All historical rates should be between 0 and 1."""
        for circuit, rate in CIRCUIT_SC_RATES.items():
            assert 0 < rate < 1, f"{circuit} has invalid rate: {rate}"


# =============================================================================
# P1: Weather → Strategy Integration Tests
# =============================================================================


class TestWeatherStrategyIntegration:
    """Test rain_expected parameter in evaluate_strategy."""

    def test_rain_imminent_triggers_pit(self):
        """Rain in 3 laps should trigger pit for intermediates."""
        rec = evaluate_strategy(
            driver_number=44,
            current_lap=20,
            total_laps=50,
            current_position=5,
            deg_slope=0.03,
            cliff_risk=0.1,
            current_pace=90.0,
            tyre_age=8,
            compound="SOFT",
            pit_loss=22.0,
            rain_expected=True,
            rain_laps_away=3,
        )
        assert rec.recommendation.value == "PIT_NOW"
        assert rec.pit_decision is not None
        assert rec.pit_decision.compound_to == "INTERMEDIATE"

    def test_no_rain_normal_behavior(self):
        """Without rain, recommendation should not change."""
        rec_no_rain = evaluate_strategy(
            driver_number=44,
            current_lap=20,
            total_laps=50,
            current_position=5,
            deg_slope=0.03,
            cliff_risk=0.1,
            current_pace=90.0,
            tyre_age=5,
            compound="MEDIUM",
            pit_loss=22.0,
            rain_expected=False,
        )
        # Should be STAY_OUT or EXTEND_STINT with low deg and young tyres
        assert rec_no_rain.recommendation.value in ("STAY_OUT", "EXTEND_STINT")

    def test_rain_already_on_inters(self):
        """If already on intermediates, rain shouldn't trigger another pit."""
        rec = evaluate_strategy(
            driver_number=44,
            current_lap=20,
            total_laps=50,
            current_position=5,
            deg_slope=0.04,
            cliff_risk=0.2,
            current_pace=95.0,
            tyre_age=10,
            compound="INTERMEDIATE",
            pit_loss=22.0,
            rain_expected=True,
            rain_laps_away=3,
        )
        # Should not recommend pit for inters when already on inters
        assert rec.pit_decision is None or rec.pit_decision.compound_to != "INTERMEDIATE" or rec.recommendation.value != "PIT_NOW"


# =============================================================================
# P1: Season Learner Tests
# =============================================================================


class TestSeasonLearner:
    """Test cross-session learning persistence."""

    def test_save_and_load(self):
        """Season data should survive save/load cycle."""
        from rsw.models.physics.season_learner import SeasonData, SeasonLearner

        with tempfile.TemporaryDirectory() as tmpdir:
            learner = SeasonLearner(data_dir=Path(tmpdir))
            season = learner.load(2025)
            assert season.year == 2025
            assert len(season.driver_profiles) == 0

            # Save and reload
            learner.save(season)
            reloaded = SeasonLearner(data_dir=Path(tmpdir)).load(2025)
            assert reloaded.year == 2025

    def test_get_driver_priors_empty(self):
        """Should return (None, None) for unknown driver."""
        from rsw.models.physics.season_learner import SeasonLearner

        with tempfile.TemporaryDirectory() as tmpdir:
            learner = SeasonLearner(data_dir=Path(tmpdir))
            pace, deg = learner.get_driver_priors(2025, 99, "SOFT")
            assert pace is None
            assert deg is None

    def test_season_priors_warm_start(self):
        """Degradation model should use season priors when provided."""
        model = DriverDegradationModel(driver_number=44)
        model.new_stint(
            stint_number=1,
            compound="SOFT",
            start_lap=1,
            season_priors=(88.5, 0.07),
        )
        # Model should warm-start with lower uncertainty (20.0)
        assert model.current_stint is not None
        # RLS should have the warm-started parameters
        theta = model.current_stint.rls.theta
        assert abs(theta[0] - 88.5) < 1.0  # Base pace close to prior
