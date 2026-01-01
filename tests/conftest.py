"""
Pytest configuration and fixtures.

Provides shared fixtures for testing the RSW application.
"""

import asyncio
import json
import pytest
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import httpx
from fastapi.testclient import TestClient


# ============================================================================
# Event Loop Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Application Fixtures
# ============================================================================

@pytest.fixture
def app():
    """Get FastAPI application."""
    from rsw.main import app
    return app


@pytest.fixture
def client(app):
    """Get synchronous test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Get async test client."""
    async with httpx.AsyncClient(
        app=app,
        base_url="http://test",
    ) as client:
        yield client


# ============================================================================
# Mock Data Fixtures
# ============================================================================

@pytest.fixture
def sample_session() -> dict:
    """Sample session data."""
    return {
        "session_key": 9158,
        "session_name": "Race",
        "session_type": "Race",
        "country_name": "Bahrain",
        "circuit_short_name": "Sakhir",
        "year": 2023,
        "date_start": "2023-03-05T15:00:00",
    }


@pytest.fixture
def sample_driver() -> dict:
    """Sample driver data."""
    return {
        "driver_number": 1,
        "name_acronym": "VER",
        "full_name": "Max VERSTAPPEN",
        "team_name": "Red Bull Racing",
        "team_colour": "3671C6",
    }


@pytest.fixture
def sample_lap() -> dict:
    """Sample lap data."""
    return {
        "driver_number": 1,
        "lap_number": 15,
        "lap_duration": 92.456,
        "sector_1_time": 29.123,
        "sector_2_time": 31.234,
        "sector_3_time": 32.099,
        "is_pit_out_lap": False,
    }


@pytest.fixture
def sample_stint() -> dict:
    """Sample stint data."""
    return {
        "driver_number": 1,
        "stint_number": 1,
        "compound": "SOFT",
        "lap_start": 1,
        "lap_end": 20,
        "tyre_age_at_start": 0,
    }


@pytest.fixture
def sample_race_state(sample_driver) -> dict:
    """Sample race state."""
    return {
        "session_key": 9158,
        "session_name": "Race",
        "track_name": "Sakhir",
        "country": "Bahrain",
        "current_lap": 25,
        "total_laps": 57,
        "safety_car": False,
        "virtual_safety_car": False,
        "red_flag": False,
        "drivers": [
            {
                **sample_driver,
                "position": 1,
                "current_lap": 25,
                "last_lap_time": 92.456,
                "gap_to_leader": 0.0,
                "gap_to_ahead": 0.0,
                "compound": "SOFT",
                "tyre_age": 15,
            }
        ],
    }


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_openf1_client():
    """Mock OpenF1 client."""
    from rsw.ingest.base import Session, Driver, Lap, Stint, Pit
    
    mock = AsyncMock()
    
    # Configure mock responses
    mock.get_sessions.return_value = [
        Session(
            session_key=9158,
            session_name="Race",
            session_type="Race",
            country_name="Bahrain",
            circuit_short_name="Sakhir",
            year=2023,
        )
    ]
    
    mock.get_drivers.return_value = [
        Driver(
            driver_number=1,
            name_acronym="VER",
            full_name="Max VERSTAPPEN",
            team_name="Red Bull Racing",
            team_colour="3671C6",
        )
    ]
    
    mock.get_laps.return_value = [
        Lap(
            driver_number=1,
            lap_number=i,
            lap_duration=92.0 + i * 0.1,
        )
        for i in range(1, 20)
    ]
    
    return mock


@pytest.fixture
def mock_model_manager():
    """Mock ML model manager."""
    from rsw.models.degradation import ModelManager
    
    mock = MagicMock(spec=ModelManager)
    mock.get_all_predictions.return_value = {}
    
    return mock


# ============================================================================
# Temporary File Fixtures
# ============================================================================

@pytest.fixture
def temp_session_file(tmp_path, sample_race_state) -> Path:
    """Create temporary session cache file."""
    session_file = tmp_path / "sessions" / "9158.json"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "session_key": 9158,
        "session_info": {
            "session_name": "Race",
            "country_name": "Bahrain",
            "circuit_short_name": "Sakhir",
        },
        "drivers": [sample_race_state["drivers"][0]],
        "laps": [
            {"driver_number": 1, "lap_number": i, "lap_duration": 92.0 + i * 0.1}
            for i in range(1, 20)
        ],
        "stints": [],
        "pits": [],
        "race_control": [],
    }
    
    with open(session_file, "w") as f:
        json.dump(data, f)
    
    return session_file


# ============================================================================
# Database Fixtures (when using real DB)
# ============================================================================

@pytest.fixture
async def db_session():
    """Get test database session."""
    # This would connect to test database
    # For now, skip if DB not configured
    pytest.skip("Database not configured for testing")
