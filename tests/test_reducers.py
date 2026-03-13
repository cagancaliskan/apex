from src.rsw.state.reducers import apply_pits
from src.rsw.state.schemas import RaceState, DriverState
from src.rsw.ingest.base import PitData
from datetime import datetime


def test_apply_pits_includes_compound():
    """recent_pits records must include the driver's compound at pit time."""
    driver = DriverState(driver_number=44, compound="SOFT")
    state = RaceState(session_key=1, drivers={44: driver})  # integer key
    pit = PitData(
        driver_number=44,
        lap_number=32,
        pit_duration=23.4,
        timestamp=datetime(2024, 1, 1),
    )

    new_state = apply_pits(state, [pit])

    assert len(new_state.recent_pits) == 1
    record = new_state.recent_pits[0]
    assert record["driver_number"] == 44
    assert record["lap_number"] == 32
    assert record["pit_duration"] == 23.4
    assert record["compound"] == "SOFT"


def test_apply_pits_compound_none_for_unknown_driver():
    """Compound is None when driver not found in state."""
    state = RaceState(session_key=1, drivers={})  # empty — driver 99 not present
    pit = PitData(
        driver_number=99,
        lap_number=10,
        pit_duration=20.0,
        timestamp=datetime(2024, 1, 1),
    )

    new_state = apply_pits(state, [pit])

    assert new_state.recent_pits[0]["compound"] is None
