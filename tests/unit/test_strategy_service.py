"""
Unit Tests for StrategyService.

Tests the strategy calculation engine including:
- Pit window calculations
- Recommendation generation
- Monte Carlo simulations

Run with: pytest tests/unit/test_strategy_service.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rsw.services.strategy_service import StrategyService, PitWindow, Recommendation


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_config():
    """Create mock strategy configuration."""
    config = MagicMock()
    config.monte_carlo_simulations = 1000
    return config


@pytest.fixture
def strategy_service(mock_config):
    """Create StrategyService instance."""
    return StrategyService(mock_config)


@pytest.fixture
def mock_driver():
    """Create mock driver state."""
    driver = MagicMock()
    driver.driver_number = 1
    driver.current_lap = 20
    driver.tyre_age = 15
    driver.deg_slope = 0.06
    driver.cliff_risk = 0.4
    driver.last_lap_time = 92.5
    driver.compound = "SOFT"
    driver.position = 1
    return driver


@pytest.fixture
def mock_race_state():
    """Create mock race state."""
    state = MagicMock()
    state.current_lap = 20
    state.total_laps = 57
    state.safety_car = False
    return state


# =============================================================================
# Tests: Data Classes
# =============================================================================

class TestDataClasses:
    """Tests for strategy data classes."""

    def test_pit_window_creation(self):
        """PitWindow should store lap information."""
        window = PitWindow(min_lap=20, max_lap=30, ideal_lap=25, reason="Tyre degradation")
        
        assert window.min_lap == 20
        assert window.max_lap == 30
        assert window.ideal_lap == 25
        assert window.reason == "Tyre degradation"

    def test_recommendation_creation(self):
        """Recommendation should store strategy advice."""
        rec = Recommendation(
            action="PIT_NOW",
            confidence=0.85,
            reason="High degradation",
            undercut_threat=True,
        )
        
        assert rec.action == "PIT_NOW"
        assert rec.confidence == 0.85
        assert rec.undercut_threat is True
        assert rec.overcut_opportunity is False  # Default


# =============================================================================
# Tests: StrategyService Initialization
# =============================================================================

class TestStrategyServiceInit:
    """Tests for service initialization."""

    def test_init_with_config(self, strategy_service, mock_config):
        """Service should initialize with config."""
        assert strategy_service.config == mock_config

    def test_pit_loss_cache_empty(self, strategy_service):
        """Pit loss cache should start empty."""
        assert strategy_service._pit_loss_cache == {}


# =============================================================================
# Tests: Pit Window Calculation
# =============================================================================

class TestPitWindowCalculation:
    """Tests for pit window calculations."""

    def test_calculate_pit_window_returns_dict(self, strategy_service, mock_driver):
        """calculate_pit_window should return expected structure."""
        with patch("rsw.strategy.pit_window.find_optimal_window") as mock_find:
            mock_find.return_value = MagicMock(
                min_lap=18,
                max_lap=28,
                ideal_lap=23,
                reason="Optimal tyre life",
            )
            
            result = strategy_service.calculate_pit_window(
                driver=mock_driver,
                total_laps=57,
                pit_loss=22.0,
            )
            
            assert "min_lap" in result
            assert "max_lap" in result
            assert "ideal_lap" in result
            assert "reason" in result
            assert result["min_lap"] == 18
            assert result["ideal_lap"] == 23


# =============================================================================
# Tests: Recommendation Generation
# =============================================================================

class TestRecommendationGeneration:
    """Tests for strategy recommendations."""

    def test_get_recommendation_returns_dict(
        self, strategy_service, mock_driver, mock_race_state
    ):
        """get_recommendation should return expected structure."""
        with patch("rsw.strategy.decision.evaluate_strategy") as mock_eval:
            mock_eval.return_value = MagicMock(
                recommendation=MagicMock(value="CONSIDER_PIT"),
                confidence=0.75,
                reason="Approaching cliff",
                undercut_threat=False,
                overcut_opportunity=True,
                pit_window=MagicMock(min_lap=20, max_lap=30, ideal_lap=25),
            )
            
            result = strategy_service.get_recommendation(
                driver=mock_driver,
                race_state=mock_race_state,
            )
            
            assert "recommendation" in result
            assert "confidence" in result
            assert "reason" in result
            assert "undercut_threat" in result
            assert "overcut_opportunity" in result
            assert result["recommendation"] == "CONSIDER_PIT"
            assert result["overcut_opportunity"] is True

    def test_get_recommendation_with_no_pit_window(
        self, strategy_service, mock_driver, mock_race_state
    ):
        """get_recommendation should handle missing pit window."""
        with patch("rsw.strategy.decision.evaluate_strategy") as mock_eval:
            mock_eval.return_value = MagicMock(
                recommendation=MagicMock(value="EXTEND_STINT"),
                confidence=0.9,
                reason="Fresh tyres",
                undercut_threat=False,
                overcut_opportunity=False,
                pit_window=None,
            )
            
            result = strategy_service.get_recommendation(
                driver=mock_driver,
                race_state=mock_race_state,
            )
            
            assert result["pit_window"] is None


# =============================================================================
# Tests: Monte Carlo Simulation
# =============================================================================

class TestMonteCarloSimulation:
    """Tests for Monte Carlo race simulations."""

    def test_run_monte_carlo_returns_probabilities(
        self, strategy_service, mock_driver, mock_config
    ):
        """run_monte_carlo should return probability metrics."""
        competitors = [MagicMock(last_lap_time=93.0, deg_slope=0.05)]
        
        with patch("rsw.strategy.monte_carlo.simulate_race") as mock_sim:
            mock_sim.return_value = MagicMock(
                expected_position=2.3,
                position_std=1.1,
                prob_win=0.35,
                prob_podium=0.78,
                prob_points=0.95,
            )
            
            result = strategy_service.run_monte_carlo(
                driver=mock_driver,
                competitors=competitors,
                remaining_laps=37,
                pit_loss=22.0,
            )
            
            assert "expected_position" in result
            assert "position_std" in result
            assert "prob_win" in result
            assert "prob_podium" in result
            assert "prob_points" in result
            assert 0 <= result["prob_win"] <= 1
            assert 0 <= result["prob_podium"] <= 1

    def test_run_monte_carlo_uses_config_simulations(
        self, strategy_service, mock_driver, mock_config
    ):
        """run_monte_carlo should use config's simulation count."""
        with patch("rsw.strategy.monte_carlo.simulate_race") as mock_sim:
            mock_sim.return_value = MagicMock(
                expected_position=1.0,
                position_std=0.0,
                prob_win=1.0,
                prob_podium=1.0,
                prob_points=1.0,
            )
            
            strategy_service.run_monte_carlo(
                driver=mock_driver,
                competitors=[],
                remaining_laps=10,
                pit_loss=22.0,
            )
            
            # Verify simulation count from config
            call_kwargs = mock_sim.call_args.kwargs
            assert call_kwargs.get("n_simulations") == mock_config.monte_carlo_simulations

    def test_run_monte_carlo_custom_simulations(
        self, strategy_service, mock_driver
    ):
        """run_monte_carlo should accept custom simulation count."""
        with patch("rsw.strategy.monte_carlo.simulate_race") as mock_sim:
            mock_sim.return_value = MagicMock(
                expected_position=3.0,
                position_std=2.0,
                prob_win=0.1,
                prob_podium=0.4,
                prob_points=0.8,
            )
            
            strategy_service.run_monte_carlo(
                driver=mock_driver,
                competitors=[],
                remaining_laps=10,
                pit_loss=22.0,
                n_simulations=500,
            )
            
            # Verify custom count used
            call_kwargs = mock_sim.call_args.kwargs
            assert call_kwargs.get("n_simulations") == 500


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
