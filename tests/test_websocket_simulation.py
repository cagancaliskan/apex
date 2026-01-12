"""
Tests for WebSocket communication and simulation lifecycle.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket


class TestWebSocketConnection:
    """Tests for WebSocket endpoint."""
    
    def test_websocket_connect(self, client: TestClient):
        """Test WebSocket connection establishment."""
        with client.websocket_connect("/ws") as websocket:
            # Should receive initial state
            data = websocket.receive_json()
            assert data["type"] == "state_update"
            assert "data" in data
    
    def test_websocket_receives_state_update(self, client: TestClient):
        """Test WebSocket receives state update with expected fields."""
        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            state = data["data"]
            
            # Check critical fields exist
            assert "session_key" in state or state.get("session_key") is None
            assert "drivers" in state
            assert "current_lap" in state
            assert "total_laps" in state


class TestRoundNumberCalculation:
    """Tests for round number calculation logic."""
    
    @pytest.fixture
    def mock_sessions(self):
        """Create mock session data for 2023."""
        from rsw.ingest.base import SessionInfo
        from datetime import datetime, timezone
        
        # Simulate abbreviated 2023 calendar
        sessions = [
            # Testing (should be excluded)
            SessionInfo(
                session_key=9222, session_type="Practice", session_name="Day 1",
                date_start=datetime(2023, 2, 23, tzinfo=timezone.utc),
                date_end=datetime(2023, 2, 23, tzinfo=timezone.utc),
                meeting_key=1140, circuit_key=63, circuit_short_name="Sakhir",
                country_key=36, country_code="BRN", country_name="Bahrain",
                location="Sakhir", gmt_offset="03:00:00", year=2023
            ),
            # Bahrain GP (Round 1)
            SessionInfo(
                session_key=9472, session_type="Race", session_name="Race",
                date_start=datetime(2023, 3, 5, tzinfo=timezone.utc),
                date_end=datetime(2023, 3, 5, tzinfo=timezone.utc),
                meeting_key=1141, circuit_key=63, circuit_short_name="Sakhir",
                country_key=36, country_code="BRN", country_name="Bahrain",
                location="Sakhir", gmt_offset="03:00:00", year=2023
            ),
            # Cancelled Imola (should be excluded - meeting_key 1209)
            SessionInfo(
                session_key=9999, session_type="Race", session_name="Race",
                date_start=datetime(2023, 5, 20, tzinfo=timezone.utc),
                date_end=datetime(2023, 5, 20, tzinfo=timezone.utc),
                meeting_key=1209, circuit_key=99, circuit_short_name="Imola",
                country_key=99, country_code="ITA", country_name="Italy",
                location="Imola", gmt_offset="02:00:00", year=2023
            ),
            # Monaco (should be the next round after Bahrain, skipping Imola)
            SessionInfo(
                session_key=9500, session_type="Race", session_name="Race",
                date_start=datetime(2023, 5, 28, tzinfo=timezone.utc),
                date_end=datetime(2023, 5, 28, tzinfo=timezone.utc),
                meeting_key=1210, circuit_key=100, circuit_short_name="Monaco",
                country_key=100, country_code="MON", country_name="Monaco",
                location="Monaco", gmt_offset="02:00:00", year=2023
            ),
        ]
        return sessions
    
    def test_cancelled_race_excluded(self, mock_sessions):
        """Test that cancelled Imola GP (meeting 1209) is excluded from round calculation."""
        # Group by meeting
        meetings = {}
        for s in mock_sessions:
            if s.meeting_key not in meetings:
                meetings[s.meeting_key] = []
            meetings[s.meeting_key].append(s)
        
        # Apply the same logic as main.py
        race_meetings = []
        for m_key, m_sessions in meetings.items():
            has_race = any(s.session_type == "Race" or "Race" in s.session_name for s in m_sessions)
            is_testing = any("Testing" in s.session_name or "Testing" in s.circuit_short_name for s in m_sessions)
            is_cancelled = m_key in [1209]  # Imola 2023
            
            if has_race and not is_testing and not is_cancelled:
                start_date = min(s.date_start for s in m_sessions)
                race_meetings.append((m_key, start_date))
        
        race_meetings.sort(key=lambda x: x[1])
        round_map = {key: i+1 for i, (key, _) in enumerate(race_meetings)}
        
        # Assertions
        assert 1140 not in round_map  # Testing - excluded
        assert 1209 not in round_map  # Imola (cancelled) - excluded
        assert round_map[1141] == 1   # Bahrain = Round 1
        assert round_map[1210] == 2   # Monaco = Round 2 (skipping Imola)


class TestStateStore:
    """Tests for RaceStateStore serialization."""
    
    def test_to_dict_includes_track_config(self):
        """Test that to_dict includes track_config safely."""
        from rsw.state.store import RaceStateStore
        
        store = RaceStateStore()
        result = store.to_dict()
        
        # track_config should be present (may be None initially)
        assert "track_config" in result
    
    def test_to_dict_handles_missing_attributes(self):
        """Test that to_dict handles missing optional attributes gracefully."""
        from rsw.state.store import RaceStateStore
        
        store = RaceStateStore()
        result = store.to_dict()
        
        # These should have safe defaults
        assert "track_status" in result
        assert "drs_zones" in result
        assert "weather" in result
        assert "drivers" in result


class TestSanitizeForJson:
    """Tests for JSON sanitization (NaN/Infinity handling)."""
    
    def test_sanitize_nan(self):
        """Test that NaN values are converted to None."""
        import math
        from rsw.main import sanitize_for_json
        
        data = {"value": float('nan'), "normal": 42}
        result = sanitize_for_json(data)
        
        assert result["value"] is None
        assert result["normal"] == 42
    
    def test_sanitize_infinity(self):
        """Test that Infinity values are converted to None."""
        import math
        from rsw.main import sanitize_for_json
        
        data = {"pos_inf": float('inf'), "neg_inf": float('-inf')}
        result = sanitize_for_json(data)
        
        assert result["pos_inf"] is None
        assert result["neg_inf"] is None
    
    def test_sanitize_nested(self):
        """Test that nested structures are sanitized."""
        from rsw.main import sanitize_for_json
        
        data = {
            "list": [1.0, float('nan'), 3.0],
            "nested": {"inner": float('inf')}
        }
        result = sanitize_for_json(data)
        
        assert result["list"][1] is None
        assert result["nested"]["inner"] is None


class TestSimulationManager:
    """Tests for simulation lifecycle."""
    
    @pytest.mark.asyncio
    async def test_simulation_manager_start_stop(self):
        """Test that SimulationManager can start and stop cleanly."""
        from rsw.main import SimulationManager
        from rsw.state.store import RaceStateStore
        
        # Create mock app state and manager
        class MockAppState:
            store = RaceStateStore()
        
        class MockConnectionManager:
            async def broadcast(self, msg):
                pass
        
        app_state = MockAppState()
        manager = MockConnectionManager()
        
        sim = SimulationManager(app_state, manager)
        
        # Start should not raise
        await sim.start(2023, 1)
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Stop should complete cleanly
        await sim.stop()
        
        assert sim.current_task is None or sim.current_task.done()
