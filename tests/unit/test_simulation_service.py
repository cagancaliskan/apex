"""
Unit Tests for SimulationService.

Tests the simulation engine's core functionality including:
- Lifecycle management (start/stop)
- Speed control
- JSON sanitization
- State updates

Run with: pytest tests/unit/test_simulation_service.py -v
"""

from __future__ import annotations

import asyncio
import math
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the service
from rsw.services.simulation_service import SimulationService, sanitize_for_json


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_app_state():
    """Create mock application state."""
    state = MagicMock()
    state.speed_multiplier = 1.0
    state.all_driver_telemetry = {}
    state.store = MagicMock()
    state.store.get.return_value = MagicMock(
        session_key=12345,
        session_name="Test GP",
        current_lap=1,
        total_laps=50,
        drivers={},
    )
    state.store.to_dict.return_value = {"session_key": 12345}
    return state


@pytest.fixture
def mock_connection_manager():
    """Create mock connection manager."""
    manager = MagicMock()
    manager.broadcast = AsyncMock()
    return manager


@pytest.fixture
def simulation_service(mock_app_state, mock_connection_manager):
    """Create SimulationService instance."""
    return SimulationService(mock_app_state, mock_connection_manager)


# =============================================================================
# Tests: sanitize_for_json
# =============================================================================

class TestSanitizeForJson:
    """Tests for JSON sanitization utility."""

    def test_sanitize_nan(self):
        """NaN values should become None."""
        data = {"value": float("nan")}
        result = sanitize_for_json(data)
        assert result["value"] is None

    def test_sanitize_infinity(self):
        """Infinity values should become None."""
        data = {"pos_inf": float("inf"), "neg_inf": float("-inf")}
        result = sanitize_for_json(data)
        assert result["pos_inf"] is None
        assert result["neg_inf"] is None

    def test_sanitize_nested_dict(self):
        """Nested dicts should be sanitized recursively."""
        data = {
            "level1": {
                "level2": {
                    "bad_value": float("nan"),
                    "good_value": 42.0,
                }
            }
        }
        result = sanitize_for_json(data)
        assert result["level1"]["level2"]["bad_value"] is None
        assert result["level1"]["level2"]["good_value"] == 42.0

    def test_sanitize_list(self):
        """Lists should be sanitized recursively."""
        data = {"items": [1.0, float("nan"), 3.0, float("inf")]}
        result = sanitize_for_json(data)
        assert result["items"] == [1.0, None, 3.0, None]

    def test_sanitize_valid_float(self):
        """Valid floats should pass through unchanged."""
        data = {"value": 123.456}
        result = sanitize_for_json(data)
        assert result["value"] == 123.456

    def test_sanitize_non_numeric(self):
        """Non-numeric values should pass through unchanged."""
        data = {"string": "hello", "none": None, "int": 42}
        result = sanitize_for_json(data)
        assert result == data


# =============================================================================
# Tests: SimulationService Lifecycle
# =============================================================================

class TestSimulationServiceLifecycle:
    """Tests for simulation lifecycle management."""

    def test_init(self, simulation_service, mock_app_state):
        """Service should initialize with correct state."""
        assert simulation_service.state == mock_app_state
        assert not simulation_service.is_running
        assert simulation_service._task is None

    @pytest.mark.asyncio
    async def test_set_speed(self, simulation_service, mock_app_state):
        """set_speed should update speed multiplier."""
        await simulation_service.set_speed(5.0)
        assert mock_app_state.speed_multiplier == 5.0

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, simulation_service):
        """stop() should be safe when not running."""
        await simulation_service.stop()
        assert not simulation_service.is_running

    @pytest.mark.asyncio
    async def test_start_creates_task(self, simulation_service):
        """start() should create background task."""
        with patch.object(
            simulation_service, "_run_loop", new_callable=AsyncMock
        ) as mock_run:
            await simulation_service.start(2023, 1)
            
            # Give task a moment to start
            await asyncio.sleep(0.1)
            
            assert simulation_service.is_running
            assert simulation_service._task is not None
            
            # Stop immediately
            await simulation_service.stop()

    @pytest.mark.asyncio
    async def test_start_stops_existing_simulation(self, simulation_service):
        """Starting new simulation should stop existing one."""
        with patch.object(
            simulation_service, "_run_loop", new_callable=AsyncMock
        ):
            await simulation_service.start(2023, 1)
            first_task = simulation_service._task
            
            await simulation_service.start(2023, 2)
            second_task = simulation_service._task
            
            assert first_task != second_task
            
            await simulation_service.stop()

    def test_is_running_property(self, simulation_service):
        """is_running should reflect internal state."""
        assert not simulation_service.is_running
        
        simulation_service._running = True
        assert simulation_service.is_running
        
        simulation_service._running = False
        assert not simulation_service.is_running


# =============================================================================
# Tests: SimulationService Helper Methods
# =============================================================================

class TestSimulationServiceHelpers:
    """Tests for simulation helper methods."""

    def test_default_weather(self, simulation_service):
        """_default_weather should return valid weather dict."""
        weather = simulation_service._default_weather()
        
        assert "track_temp" in weather
        assert "air_temp" in weather
        assert "is_raining" in weather
        assert weather["is_raining"] is False

    def test_get_average_lap_time_with_valid_laps(self, simulation_service):
        """Should return average from valid lap times."""
        laps = [MagicMock(lap_duration=92.5), MagicMock(lap_duration=None)]
        result = simulation_service._get_average_lap_time(laps)
        assert result == 92.5

    def test_get_average_lap_time_empty(self, simulation_service):
        """Should return 90 for empty lap list."""
        result = simulation_service._get_average_lap_time([])
        assert result == 90.0

    def test_get_average_lap_time_no_valid(self, simulation_service):
        """Should return 90 when no valid lap times."""
        laps = [MagicMock(lap_duration=None), MagicMock(lap_duration=30)]
        result = simulation_service._get_average_lap_time(laps)
        assert result == 90.0


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
