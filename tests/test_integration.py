"""
Integration tests for the full system.
Tests data flow from OpenF1 -> State -> Models -> Frontend.
"""

import pytest
import asyncio
from rsw.ingest import OpenF1Client
from rsw.state import RaceStateStore, RaceState
from rsw.models.degradation import ModelManager
from datetime import datetime, timezone


@pytest.mark.asyncio
class TestSystemIntegration:
    """Integration tests for complete data pipeline."""
    
    async def test_openf1_data_fetching(self):
        """Test fetching real data from OpenF1 API."""
        client = OpenF1Client()
        
        try:
            # Get recent sessions
            sessions = await client.get_sessions(year=2023)
            assert len(sessions) > 0
            
            # Get a race session
            race_sessions = [s for s in sessions if s.session_name == "Race"]
            assert len(race_sessions) > 0
            
            session = race_sessions[0]
            
            # Fetch drivers for that session
            drivers = await client.get_drivers(session.session_key)
            assert len(drivers) > 0
            assert drivers[0].name_acronym != ""
            
            # Fetch some laps
            laps = await client.get_laps(session.session_key)
            assert len(laps) > 0
            # Some laps may not have duration (e.g., in/out laps)
            has_duration = any(lap.lap_duration is not None for lap in laps)
            assert has_duration, "No laps with duration found"
            
        finally:
            await client.close()
    
    async def test_state_management_flow(self):
        """Test state updates through reducers."""
        from rsw.ingest.base import UpdateBatch, DriverInfo, LapData
        from datetime import datetime
        
        store = RaceStateStore()
        
        # Initialize with session
        initial_state = RaceState(
            session_key=9999,
            session_name="Test Race",
            total_laps=50,
        )
        await store.reset(initial_state)
        
        # Add driver info
        batch1 = UpdateBatch(
            session_key=9999,
            timestamp=datetime.now(timezone.utc),
            drivers=[
                DriverInfo(
                    driver_number=44,
                    name_acronym="HAM",
                    full_name="Lewis HAMILTON",
                    team_name="Mercedes",
                    team_colour="00D2BE",
                    country_code="GBR",  # Add required field
                )
            ],
        )
        await store.apply(batch1)
        
        state = store.get()
        assert 44 in state.drivers
        assert state.drivers[44].name_acronym == "HAM"
        
        # Add lap data
        batch2 = UpdateBatch(
            session_key=9999,
            timestamp=datetime.now(timezone.utc),
            current_lap=1,
            laps=[
                LapData(
                    driver_number=44,
                    lap_number=1,
                    lap_duration=92.5,
                )
            ],
        )
        await store.apply(batch2)
        
        state = store.get()
        assert state.current_lap == 1
        assert state.drivers[44].last_lap_time == 92.5
    
    async def test_model_integration(self):
        """Test model manager with state updates."""
        manager = ModelManager(forgetting_factor=0.95)
        
        # Simulate 20 laps for a driver
        for lap in range(1, 21):
            # Simulate degrading lap times
            lap_time = 92.0 + 0.07 * lap
            
            manager.update_driver(
                driver_number=44,
                lap_in_stint=lap,
                lap_time=lap_time,
                stint_number=1,
                compound="SOFT",
                is_valid=True,
            )
        
        # Get predictions
        predictions = manager.get_all_predictions(k=5)
        
        assert 44 in predictions
        pred = predictions[44]
        
        # Should detect degradation
        assert pred.deg_slope > 0.05
        assert pred.deg_slope < 0.10
        
        # Predictions should exist
        assert len(pred.predicted_next_k) == 5
        
        # Should show increasing times
        assert pred.predicted_next_k[4] > pred.predicted_next_k[0]
