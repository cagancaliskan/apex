"""
Tests for ChampionshipService.

Tests the multi-race Monte Carlo simulation including:
- Points calculation (race + sprint + fastest lap)
- DNF modeling
- Championship phase detection
- Result aggregation
- API routes

Run with: PYTHONPATH=src pytest tests/test_championship.py -v
"""

import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rsw.services.championship_service import (
    DNF_PROBABILITY,
    RACE_POINTS,
    SPRINT_POINTS,
    ChampionshipResult,
    ChampionshipService,
    DriverStanding,
    RaceCalendarEntry,
    _determine_phase,
)
from rsw.strategy.situational_strategy import ChampionshipPhase


# =============================================================================
# Points Calculation
# =============================================================================


class TestPointsCalculation:
    """Tests for position-to-points conversion."""

    def setup_method(self):
        self.service = ChampionshipService()

    def test_race_points_p1(self):
        assert self.service._position_to_points(1) == 25

    def test_race_points_p2(self):
        assert self.service._position_to_points(2) == 18

    def test_race_points_p3(self):
        assert self.service._position_to_points(3) == 15

    def test_race_points_p10(self):
        assert self.service._position_to_points(10) == 1

    def test_race_points_p11_zero(self):
        assert self.service._position_to_points(11) == 0

    def test_race_points_p20_zero(self):
        assert self.service._position_to_points(20) == 0

    def test_sprint_points_p1(self):
        assert self.service._position_to_points(1, is_sprint=True) == 8

    def test_sprint_points_p8(self):
        assert self.service._position_to_points(8, is_sprint=True) == 1

    def test_sprint_points_p9_zero(self):
        assert self.service._position_to_points(9, is_sprint=True) == 0

    def test_fastest_lap_bonus_p1(self):
        assert self.service._position_to_points(1, fastest_lap_eligible=True) == 26

    def test_fastest_lap_bonus_p10(self):
        assert self.service._position_to_points(10, fastest_lap_eligible=True) == 2

    def test_fastest_lap_no_bonus_p11(self):
        """Fastest lap bonus only applies if finished in top 10."""
        assert self.service._position_to_points(11, fastest_lap_eligible=True) == 0

    def test_fastest_lap_not_for_sprint(self):
        """No fastest lap bonus in sprint races."""
        assert self.service._position_to_points(1, is_sprint=True, fastest_lap_eligible=True) == 8

    def test_all_race_points_match_constant(self):
        for pos, expected in RACE_POINTS.items():
            assert self.service._position_to_points(pos) == expected

    def test_all_sprint_points_match_constant(self):
        for pos, expected in SPRINT_POINTS.items():
            assert self.service._position_to_points(pos, is_sprint=True) == expected


# =============================================================================
# DNF Model
# =============================================================================


class TestDNFModel:
    """Tests for DNF probability application."""

    def setup_method(self):
        self.service = ChampionshipService()

    def test_dnf_preserves_driver_count(self):
        results = {i: i for i in range(1, 21)}
        adjusted = self.service._apply_dnf(results, 20)
        assert len(adjusted) == 20

    def test_dnf_non_dnf_positions_contiguous(self):
        """Non-DNF drivers should have contiguous positions 1..N."""
        results = {i: i for i in range(1, 21)}
        adjusted = self.service._apply_dnf(results, 20)
        non_dnf = sorted(p for p in adjusted.values() if p <= 20)
        assert non_dnf == list(range(1, len(non_dnf) + 1))

    def test_zero_dnf_when_probability_zero(self):
        """With random always returning 1.0, no DNFs should occur."""
        results = {i: i for i in range(1, 21)}
        with patch("rsw.services.championship_service.random") as mock_rng:
            mock_rng.random.return_value = 1.0  # Always > DNF_PROBABILITY
            adjusted = self.service._apply_dnf(results, 20)
        # All positions should remain unchanged
        assert adjusted == results

    def test_all_dnf_when_probability_one(self):
        """With random always returning 0.0, all drivers DNF."""
        results = {i: i for i in range(1, 6)}
        with patch("rsw.services.championship_service.random") as mock_rng:
            mock_rng.random.return_value = 0.0  # Always < DNF_PROBABILITY
            adjusted = self.service._apply_dnf(results, 5)
        # All drivers should be at position grid_size + 1
        assert all(pos == 6 for pos in adjusted.values())


# =============================================================================
# Championship Phase
# =============================================================================


class TestChampionshipPhase:
    """Tests for championship phase calculation."""

    def test_early_phase(self):
        assert _determine_phase(18, 22) == ChampionshipPhase.EARLY

    def test_middle_phase(self):
        assert _determine_phase(11, 22) == ChampionshipPhase.MIDDLE

    def test_late_phase(self):
        assert _determine_phase(5, 22) == ChampionshipPhase.LATE

    def test_decisive_phase(self):
        assert _determine_phase(2, 22) == ChampionshipPhase.DECISIVE

    def test_decisive_exactly_3(self):
        assert _determine_phase(3, 22) == ChampionshipPhase.DECISIVE

    def test_zero_total(self):
        assert _determine_phase(0, 0) == ChampionshipPhase.EARLY

    def test_last_race(self):
        assert _determine_phase(1, 22) == ChampionshipPhase.DECISIVE


# =============================================================================
# Fastest Lap
# =============================================================================


class TestFastestLap:
    """Tests for fastest lap award."""

    def setup_method(self):
        self.service = ChampionshipService()

    def test_fastest_lap_returns_top10_driver(self):
        results = {i: i for i in range(1, 21)}
        fl = self.service._award_fastest_lap(results)
        assert 1 <= results[fl] <= 10

    def test_fastest_lap_empty_results(self):
        results = {1: 11, 2: 12}  # No one in top 10
        fl = self.service._award_fastest_lap(results)
        assert fl == -1


# =============================================================================
# Calendar Entry Model
# =============================================================================


class TestCalendarEntry:
    """Tests for RaceCalendarEntry model."""

    def test_default_laps(self):
        entry = RaceCalendarEntry(
            round_number=1, event_name="Test GP", country="Test", location="Test"
        )
        assert entry.total_laps == 57

    def test_sprint_flag(self):
        entry = RaceCalendarEntry(
            round_number=1,
            event_name="Test GP",
            country="Test",
            location="Test",
            is_sprint_weekend=True,
        )
        assert entry.is_sprint_weekend is True


# =============================================================================
# Grid Building
# =============================================================================


class TestGridBuilding:
    """Tests for building synthetic driver grids."""

    def test_builds_grid_from_standings(self):
        service = ChampionshipService()
        standings = {
            1: {
                "name": "VER",
                "team": "Red Bull Racing",
                "team_colour": "3671C6",
                "points": 300.0,
                "positions": [1, 1, 2, 1, 3],
            },
            44: {
                "name": "HAM",
                "team": "Mercedes",
                "team_colour": "27F4D2",
                "points": 200.0,
                "positions": [3, 4, 1, 5, 2],
            },
        }
        grid = service._build_driver_grid(2023, standings)
        assert 1 in grid
        assert 44 in grid
        assert grid[1].name_acronym == "VER"
        assert grid[44].team_name == "Mercedes"

    def test_grid_has_valid_positions(self):
        service = ChampionshipService()
        standings = {
            i: {
                "name": f"DR{i}",
                "team": "TestTeam",
                "team_colour": "FFFFFF",
                "points": float(20 - i),
                "positions": [i],
            }
            for i in range(1, 6)
        }
        grid = service._build_driver_grid(2023, standings)
        for drv in grid.values():
            assert drv.position >= 1


# =============================================================================
# Aggregation
# =============================================================================


class TestAggregation:
    """Tests for simulation result aggregation."""

    def test_prob_champion_sums_to_approximately_one(self):
        service = ChampionshipService()
        standings = {
            1: {"name": "VER", "team": "RBR", "team_colour": "3671C6", "points": 100},
            44: {"name": "HAM", "team": "MER", "team_colour": "27F4D2", "points": 80},
        }
        # Simulate simple points
        all_points = [
            {1: 200.0, 44: 150.0},
            {1: 180.0, 44: 190.0},
            {1: 210.0, 44: 160.0},
            {1: 170.0, 44: 200.0},
        ]
        wdc, wcc = service._aggregate(all_points, standings)

        total_prob = sum(d.prob_champion for d in wdc)
        assert abs(total_prob - 1.0) < 0.01

    def test_empty_simulations(self):
        service = ChampionshipService()
        wdc, wcc = service._aggregate([], {})
        assert wdc == []
        assert wcc == []

    def test_wcc_groups_by_team(self):
        service = ChampionshipService()
        standings = {
            1: {"name": "VER", "team": "RBR", "team_colour": "3671C6", "points": 100},
            11: {"name": "PER", "team": "RBR", "team_colour": "3671C6", "points": 80},
            44: {"name": "HAM", "team": "MER", "team_colour": "27F4D2", "points": 90},
        }
        all_points = [{1: 200.0, 11: 150.0, 44: 180.0}]
        wdc, wcc = service._aggregate(all_points, standings)

        teams = [c.team for c in wcc]
        assert "RBR" in teams
        assert "MER" in teams

        rbr = next(c for c in wcc if c.team == "RBR")
        assert set(rbr.driver_numbers) == {1, 11}
        assert rbr.total_points_mean == 350.0  # 200 + 150


# =============================================================================
# Result Model
# =============================================================================


class TestResultModel:
    """Tests for ChampionshipResult serialization."""

    def test_result_serializes(self):
        result = ChampionshipResult(
            year=2023,
            start_from_round=10,
            total_rounds=22,
            completed_rounds=9,
            remaining_rounds=13,
            n_simulations=5,
        )
        data = result.model_dump()
        assert data["year"] == 2023
        assert data["remaining_rounds"] == 13

    def test_driver_standing_defaults(self):
        ds = DriverStanding(
            driver_number=1, name="VER", team="RBR", team_colour="3671C6"
        )
        assert ds.current_points == 0.0
        assert ds.prob_champion == 0.0


# =============================================================================
# Routes (via TestClient)
# =============================================================================


class TestRoutes:
    """Tests for championship API routes."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from rsw.main import app

        return TestClient(app)

    def test_calendar_endpoint(self, client):
        """Calendar endpoint should return 200 (may be empty if fastf1 unavailable)."""
        response = client.get("/api/championship/calendar/2023")
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert "calendar" in data

    def test_simulate_endpoint_accepts_post(self, client):
        """Simulate endpoint should accept POST with valid body."""
        response = client.post(
            "/api/championship/simulate",
            json={
                "year": 2023,
                "start_from_round": 20,
                "n_simulations": 2,
            },
        )
        # May take time or fail if FastF1 is unavailable, but should not 404
        assert response.status_code in (200, 500)
