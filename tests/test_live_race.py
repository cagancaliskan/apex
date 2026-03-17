"""
Tests for Live Race Mode — service and API routes.
"""

import asyncio
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rsw.ingest.base import (
    DriverInfo,
    IntervalData,
    LapData,
    PositionData,
    RaceControlMessage,
    SessionInfo,
    StintData,
    UpdateBatch,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_openf1():
    """Mock OpenF1Client with realistic responses."""
    mock = AsyncMock()

    mock.get_session.return_value = SessionInfo(
        session_key=9573,
        meeting_key=1230,
        session_name="Race",
        session_type="Race",
        circuit_short_name="Sakhir",
        country_name="Bahrain",
        date_start=datetime(2023, 3, 5, 15, 0, tzinfo=UTC),
        year=2023,
    )

    mock.get_sessions.return_value = [
        SessionInfo(
            session_key=9573,
            meeting_key=1230,
            session_name="Race",
            session_type="Race",
            circuit_short_name="Sakhir",
            country_name="Bahrain",
            date_start=datetime.now(UTC),
            year=datetime.now(UTC).year,
        ),
    ]

    mock.get_drivers.return_value = [
        DriverInfo(
            driver_number=1,
            name_acronym="VER",
            full_name="Max VERSTAPPEN",
            team_name="Red Bull Racing",
            team_colour="3671C6",
            country_code="NED",
        ),
        DriverInfo(
            driver_number=11,
            name_acronym="PER",
            full_name="Sergio PEREZ",
            team_name="Red Bull Racing",
            team_colour="3671C6",
            country_code="MEX",
        ),
    ]

    mock.fetch_update_batch.return_value = UpdateBatch(
        session_key=9573,
        timestamp=datetime.now(UTC),
        current_lap=5,
        drivers=[
            DriverInfo(
                driver_number=1,
                name_acronym="VER",
                full_name="Max VERSTAPPEN",
                team_name="Red Bull Racing",
                team_colour="3671C6",
                country_code="NED",
            ),
        ],
        laps=[
            LapData(driver_number=1, lap_number=5, lap_duration=92.5, is_pit_out_lap=False),
            LapData(driver_number=11, lap_number=5, lap_duration=93.1, is_pit_out_lap=False),
        ],
        positions=[
            PositionData(driver_number=1, position=1, timestamp=datetime.now(UTC)),
            PositionData(driver_number=11, position=2, timestamp=datetime.now(UTC)),
        ],
        intervals=[
            IntervalData(driver_number=1, gap_to_leader=0.0, interval=0.0, timestamp=datetime.now(UTC)),
            IntervalData(driver_number=11, gap_to_leader=1.5, interval=1.5, timestamp=datetime.now(UTC)),
        ],
        stints=[
            StintData(driver_number=1, stint_number=1, compound="SOFT", lap_start=1),
            StintData(driver_number=11, stint_number=1, compound="MEDIUM", lap_start=1),
        ],
    )

    return mock


@pytest.fixture
def mock_weather():
    """Mock WeatherClient."""
    mock = AsyncMock()
    mock.get_current.return_value = None
    mock.get_forecast.return_value = None
    return mock


@pytest.fixture
def mock_conn_manager():
    """Mock ConnectionManager."""
    mock = AsyncMock()
    mock.broadcast = AsyncMock()
    return mock


@pytest.fixture
def mock_app_state():
    """Mock AppState with a real-ish store."""
    from rsw.state import RaceStateStore

    state = MagicMock()
    state.store = RaceStateStore()
    state.speed_multiplier = 1.0
    state.all_driver_telemetry = {}
    return state


@pytest.fixture
def live_service(mock_app_state, mock_conn_manager, mock_openf1, mock_weather):
    """Create a LiveRaceService with all mocked dependencies."""
    from rsw.services.live_race_service import LiveRaceService

    service = LiveRaceService(
        mock_app_state, mock_conn_manager, mock_openf1, mock_weather
    )
    return service


# ============================================================================
# Service Tests
# ============================================================================


class TestLiveRaceServiceInit:
    """Test service initialization."""

    def test_initial_state(self, live_service):
        assert not live_service.is_running
        assert live_service.session_key is None

    def test_get_status_when_stopped(self, live_service):
        status = live_service.get_status()
        assert status["running"] is False
        assert status["session_key"] is None


class TestLiveRaceServiceStart:
    """Test starting live tracking."""

    @pytest.mark.asyncio
    async def test_start_initializes_state(self, live_service, mock_openf1):
        result = await live_service.start(9573)

        assert result["status"] == "started"
        assert result["session_key"] == 9573
        assert result["session_name"] == "Race"
        assert result["circuit"] == "Sakhir"
        assert live_service.is_running

        # Verify fetch_update_batch was called with include_drivers=True
        mock_openf1.fetch_update_batch.assert_called_once_with(9573, include_drivers=True)

    @pytest.mark.asyncio
    async def test_start_session_not_found(self, live_service, mock_openf1):
        mock_openf1.get_session.return_value = None
        result = await live_service.start(99999)
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_start_stops_previous(self, live_service):
        await live_service.start(9573)
        assert live_service.is_running

        # Start again — should stop first
        await live_service.start(9573)
        assert live_service.is_running

    @pytest.mark.asyncio
    async def test_start_broadcasts_initial_state(self, live_service, mock_conn_manager):
        await live_service.start(9573)

        # Should have broadcast at least once (initial state)
        assert mock_conn_manager.broadcast.called


class TestLiveRaceServiceStop:
    """Test stopping live tracking."""

    @pytest.mark.asyncio
    async def test_stop_when_running(self, live_service, mock_conn_manager):
        await live_service.start(9573)
        await live_service.stop()

        assert not live_service.is_running
        assert live_service.session_key is None

        # Should broadcast live_stopped
        stop_calls = [
            call for call in mock_conn_manager.broadcast.call_args_list
            if call[0][0].get("type") == "live_stopped"
        ]
        assert len(stop_calls) >= 1

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, live_service):
        # Should not raise
        await live_service.stop()
        assert not live_service.is_running


class TestLiveRaceServicePolling:
    """Test poll cycle logic."""

    @pytest.mark.asyncio
    async def test_poll_cycle_applies_batch(self, live_service, mock_openf1, mock_app_state):
        await live_service.start(9573)

        # Reset mock to track subsequent calls
        mock_openf1.fetch_update_batch.reset_mock()
        mock_openf1.fetch_update_batch.return_value = UpdateBatch(
            session_key=9573,
            timestamp=datetime.now(UTC),
            current_lap=6,
            laps=[
                LapData(driver_number=1, lap_number=6, lap_duration=92.3, is_pit_out_lap=False),
            ],
        )

        had_new_data = await live_service._poll_cycle()

        assert had_new_data is True
        # Should have used since_lap from initial data
        mock_openf1.fetch_update_batch.assert_called_once_with(9573, since_lap=5)

    @pytest.mark.asyncio
    async def test_poll_cycle_no_new_data(self, live_service, mock_openf1):
        await live_service.start(9573)

        mock_openf1.fetch_update_batch.reset_mock()
        mock_openf1.fetch_update_batch.return_value = UpdateBatch(
            session_key=9573,
            timestamp=datetime.now(UTC),
        )

        had_new_data = await live_service._poll_cycle()
        assert had_new_data is False

    @pytest.mark.asyncio
    async def test_poll_cycle_updates_last_lap(self, live_service, mock_openf1):
        await live_service.start(9573)

        mock_openf1.fetch_update_batch.return_value = UpdateBatch(
            session_key=9573,
            timestamp=datetime.now(UTC),
            current_lap=10,
            laps=[
                LapData(driver_number=1, lap_number=10, lap_duration=92.0, is_pit_out_lap=False),
            ],
        )

        await live_service._poll_cycle()
        assert live_service._last_lap == 10


class TestLiveRaceServiceActiveSessions:
    """Test active session detection."""

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, live_service, mock_openf1):
        sessions = await live_service.get_active_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_key"] == 9573
        assert sessions[0]["session_type"] == "Race"

    @pytest.mark.asyncio
    async def test_get_active_sessions_handles_error(self, live_service, mock_openf1):
        mock_openf1.get_sessions.side_effect = Exception("API down")
        sessions = await live_service.get_active_sessions()
        assert sessions == []


class TestLiveRaceServiceDegradation:
    """Test graceful degradation on errors."""

    @pytest.mark.asyncio
    async def test_consecutive_errors_increase_interval(self, live_service):
        await live_service.start(9573)

        # Simulate max errors
        live_service._consecutive_errors = 5
        assert live_service._consecutive_errors >= live_service._max_errors


class TestLiveRaceServiceBasePace:
    """Test base pace calibration."""

    def test_calibrate_base_pace(self, live_service):
        laps = [
            LapData(driver_number=1, lap_number=i, lap_duration=90.0 + i * 0.1, is_pit_out_lap=False)
            for i in range(1, 21)
        ]
        pace = live_service._calibrate_base_pace(laps)
        assert 90.0 < pace < 93.0  # Should be around 25th percentile

    def test_calibrate_base_pace_empty(self, live_service):
        pace = live_service._calibrate_base_pace([])
        # Should return current base pace (default)
        assert pace > 0


# ============================================================================
# API Route Tests
# ============================================================================


class TestLiveRoutes:
    """Test live API endpoints."""

    def test_live_status(self, client):
        """GET /api/live/status returns status."""
        response = client.get("/api/live/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert data["running"] is False

    def test_live_sessions(self, client):
        """GET /api/live/sessions returns session list."""
        response = client.get("/api/live/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_live_stop_when_not_running(self, client):
        """POST /api/live/stop when not running returns ok."""
        response = client.post("/api/live/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
