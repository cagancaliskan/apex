"""
Championship Simulator — Multi-Race Monte Carlo Prediction.

Orchestrates full-season Monte Carlo simulations to predict
WDC (World Drivers' Championship) and WCC (World Constructors'
Championship) standings. Uses GridSimulator for each remaining
race and integrates ChampionshipContext for risk-adjusted strategy.

Usage:
    service = ChampionshipService()
    result = await service.simulate(year=2023, start_from_round=10, n_simulations=200)
"""

from __future__ import annotations

import asyncio
import copy
import random
import time
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from rsw.logging_config import get_logger
from rsw.models.physics.season_learner import SeasonLearner
from rsw.state.schemas import DriverState
from rsw.strategy.grid_simulator import GridSimulator
from rsw.strategy.situational_strategy import (
    ChampionshipContext,
    ChampionshipPhase,
    calculate_risk_modifier,
)

logger = get_logger(__name__)

# =============================================================================
# Constants
# =============================================================================

RACE_POINTS = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}
SPRINT_POINTS = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}
DNF_PROBABILITY = 0.07

# Team pace tiers: base lap time estimates when SeasonLearner has no data
TEAM_PACE_TIERS: dict[str, float] = {
    "Red Bull Racing": 87.5,
    "Mercedes": 88.0,
    "Ferrari": 88.2,
    "McLaren": 88.5,
    "Aston Martin": 89.0,
    "Alpine": 89.5,
    "Williams": 90.0,
    "AlphaTauri": 89.8,
    "RB": 89.8,
    "Alfa Romeo": 90.0,
    "Haas F1 Team": 90.5,
    "Kick Sauber": 90.5,
}
DEFAULT_PACE = 90.0
DEFAULT_DEG = 0.05


# =============================================================================
# Data Models
# =============================================================================


class RaceCalendarEntry(BaseModel):
    """Single race in the season calendar."""

    round_number: int
    event_name: str
    country: str
    location: str
    total_laps: int = 57
    is_sprint_weekend: bool = False
    completed: bool = False


class DriverStanding(BaseModel):
    """Single driver's championship prediction."""

    driver_number: int
    name: str
    team: str
    team_colour: str
    current_points: float = 0.0
    simulated_points_mean: float = 0.0
    simulated_points_std: float = 0.0
    total_points_mean: float = 0.0
    total_points_p10: float = 0.0
    total_points_p90: float = 0.0
    predicted_position: float = 0.0
    prob_champion: float = 0.0
    prob_top3: float = 0.0
    prob_top10: float = 0.0


class ConstructorStanding(BaseModel):
    """Single constructor's championship prediction."""

    team: str
    team_colour: str
    driver_numbers: list[int] = Field(default_factory=list)
    current_points: float = 0.0
    total_points_mean: float = 0.0
    total_points_p10: float = 0.0
    total_points_p90: float = 0.0
    predicted_position: float = 0.0
    prob_champion: float = 0.0


class ChampionshipResult(BaseModel):
    """Full championship simulation result."""

    year: int
    start_from_round: int
    total_rounds: int
    completed_rounds: int
    remaining_rounds: int
    n_simulations: int
    calendar: list[RaceCalendarEntry] = Field(default_factory=list)
    wdc: list[DriverStanding] = Field(default_factory=list)
    wcc: list[ConstructorStanding] = Field(default_factory=list)
    elapsed_seconds: float = 0.0


# =============================================================================
# Helper
# =============================================================================


def _determine_phase(races_remaining: int, total_races: int) -> ChampionshipPhase:
    """Determine championship phase from progress."""
    if total_races == 0:
        return ChampionshipPhase.EARLY
    fraction_complete = 1.0 - (races_remaining / total_races)
    if races_remaining <= 3:
        return ChampionshipPhase.DECISIVE
    if fraction_complete < 0.33:
        return ChampionshipPhase.EARLY
    if fraction_complete < 0.66:
        return ChampionshipPhase.MIDDLE
    return ChampionshipPhase.LATE


# =============================================================================
# Service
# =============================================================================


class ChampionshipService:
    """Orchestrates multi-race Monte Carlo championship simulation."""

    def __init__(self) -> None:
        self._season_learner = SeasonLearner()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def simulate(
        self,
        year: int,
        start_from_round: int,
        n_simulations: int = 200,
        include_sprints: bool = True,
    ) -> ChampionshipResult:
        """
        Run full championship simulation.

        Fetches actual results for completed races, then Monte Carlo
        simulates remaining races to predict WDC/WCC outcomes.
        """
        t0 = time.monotonic()

        calendar = await self._fetch_calendar(year, start_from_round)
        standings = await self._fetch_completed_standings(year, start_from_round)

        remaining = [r for r in calendar if not r.completed]
        completed_count = len(calendar) - len(remaining)

        if not remaining:
            # All races completed — just return actual standings
            wdc, wcc = self._standings_to_results(standings)
            return ChampionshipResult(
                year=year,
                start_from_round=start_from_round,
                total_rounds=len(calendar),
                completed_rounds=completed_count,
                remaining_rounds=0,
                n_simulations=0,
                calendar=calendar,
                wdc=wdc,
                wcc=wcc,
                elapsed_seconds=round(time.monotonic() - t0, 2),
            )

        driver_grid = self._build_driver_grid(year, standings)

        # Run CPU-heavy simulation in thread to keep event loop free
        wdc, wcc = await asyncio.to_thread(
            self._run_simulations,
            standings,
            driver_grid,
            remaining,
            len(calendar),
            n_simulations,
            include_sprints,
        )

        return ChampionshipResult(
            year=year,
            start_from_round=start_from_round,
            total_rounds=len(calendar),
            completed_rounds=completed_count,
            remaining_rounds=len(remaining),
            n_simulations=n_simulations,
            calendar=calendar,
            wdc=wdc,
            wcc=wcc,
            elapsed_seconds=round(time.monotonic() - t0, 2),
        )

    async def fetch_calendar(self, year: int) -> list[RaceCalendarEntry]:
        """Public wrapper for calendar fetching."""
        return await self._fetch_calendar(year, start_from_round=999)

    async def fetch_standings(
        self, year: int, up_to_round: int
    ) -> dict[int, dict[str, Any]]:
        """Public wrapper for completed standings."""
        return await self._fetch_completed_standings(year, up_to_round)

    # -------------------------------------------------------------------------
    # Data Fetching
    # -------------------------------------------------------------------------

    async def _fetch_calendar(
        self, year: int, start_from_round: int
    ) -> list[RaceCalendarEntry]:
        """Fetch season calendar from FastF1."""

        def _load():
            import fastf1

            schedule = fastf1.get_event_schedule(year, include_testing=False)
            entries = []
            for _, event in schedule.iterrows():
                rnd = int(event["RoundNumber"])
                if rnd == 0:
                    continue  # skip testing
                fmt = str(event.get("EventFormat", "")).lower()
                is_sprint = "sprint" in fmt
                entries.append(
                    RaceCalendarEntry(
                        round_number=rnd,
                        event_name=str(event["EventName"]),
                        country=str(event["Country"]),
                        location=str(event.get("Location", "")),
                        total_laps=57,  # default; overridden per-circuit if known
                        is_sprint_weekend=is_sprint,
                        completed=rnd < start_from_round,
                    )
                )
            return sorted(entries, key=lambda e: e.round_number)

        return await asyncio.to_thread(_load)

    async def _fetch_completed_standings(
        self, year: int, up_to_round: int
    ) -> dict[int, dict[str, Any]]:
        """
        Fetch actual race results for completed rounds.

        Returns {driver_number: {name, team, team_colour, points, positions: []}}.
        """

        def _load():
            import fastf1

            standings: dict[int, dict[str, Any]] = {}

            for rnd in range(1, up_to_round):
                try:
                    session = fastf1.get_session(year, rnd, "R")
                    session.load(telemetry=False, weather=False, messages=False)
                    results = session.results
                    if results is None or results.empty:
                        continue

                    for _, row in results.iterrows():
                        drv_num = int(row["DriverNumber"])
                        pos_str = str(row.get("ClassifiedPosition", ""))
                        if pos_str.isdigit():
                            pos = int(pos_str)
                        else:
                            pos = 20  # DNF/DNS

                        points = RACE_POINTS.get(pos, 0)

                        if drv_num not in standings:
                            standings[drv_num] = {
                                "name": str(
                                    row.get("Abbreviation", str(drv_num))
                                ),
                                "team": str(row.get("TeamName", "Unknown")),
                                "team_colour": str(
                                    row.get("TeamColor", "FFFFFF")
                                ),
                                "points": 0.0,
                                "positions": [],
                            }

                        standings[drv_num]["points"] += points
                        standings[drv_num]["positions"].append(pos)

                except Exception as e:
                    logger.warning(
                        "championship_round_load_failed",
                        year=year,
                        round=rnd,
                        error=str(e),
                    )
                    continue

            return standings

        return await asyncio.to_thread(_load)

    # -------------------------------------------------------------------------
    # Grid Building
    # -------------------------------------------------------------------------

    def _build_driver_grid(
        self, year: int, standings: dict[int, dict[str, Any]]
    ) -> dict[int, DriverState]:
        """Build synthetic DriverState objects for all drivers."""
        grid: dict[int, DriverState] = {}

        for drv_num, info in standings.items():
            base_pace, deg_slope = self._season_learner.get_driver_priors(
                year, drv_num, "MEDIUM"
            )
            if base_pace is None:
                base_pace = TEAM_PACE_TIERS.get(info["team"], DEFAULT_PACE)
            if deg_slope is None:
                deg_slope = DEFAULT_DEG

            # Derive starting position from average recent results
            positions = info.get("positions", [])
            avg_pos = (
                int(round(np.mean(positions[-5:]))) if positions else 10
            )

            grid[drv_num] = DriverState(
                driver_number=drv_num,
                name_acronym=info["name"],
                team_name=info["team"],
                team_colour=info.get("team_colour", "FFFFFF"),
                position=avg_pos,
                current_lap=1,
                last_lap_time=base_pace,
                compound="MEDIUM",
                tyre_age=0,
                stint_number=1,
                deg_slope=deg_slope,
            )

        return grid

    # -------------------------------------------------------------------------
    # Simulation Core
    # -------------------------------------------------------------------------

    def _run_simulations(
        self,
        standings: dict[int, dict[str, Any]],
        driver_grid: dict[int, DriverState],
        remaining_races: list[RaceCalendarEntry],
        total_rounds: int,
        n_simulations: int,
        include_sprints: bool,
    ) -> tuple[list[DriverStanding], list[ConstructorStanding]]:
        """Run N full-season simulations. Returns (wdc, wcc) standings."""
        # all_season_points[sim_idx][driver_number] = total season points
        all_season_points: list[dict[int, float]] = []

        for _ in range(n_simulations):
            # Start from actual points
            sim_points = {
                drv: info["points"] for drv, info in standings.items()
            }

            races_left = len(remaining_races)

            for race in remaining_races:
                # Simulate race
                race_results = self._simulate_single_race(
                    driver_grid, race, sim_points, races_left, total_rounds
                )

                # Apply DNF
                race_results = self._apply_dnf(
                    race_results, len(driver_grid)
                )

                # Award points
                fl_driver = self._award_fastest_lap(race_results)
                for drv, pos in race_results.items():
                    is_fl = drv == fl_driver
                    pts = self._position_to_points(
                        pos, is_sprint=False, fastest_lap_eligible=is_fl
                    )
                    sim_points.setdefault(drv, 0.0)
                    sim_points[drv] += pts

                # Sprint race
                if race.is_sprint_weekend and include_sprints:
                    sprint_results = self._simulate_single_race(
                        driver_grid,
                        race,
                        sim_points,
                        races_left,
                        total_rounds,
                    )
                    sprint_results = self._apply_dnf(
                        sprint_results, len(driver_grid)
                    )
                    for drv, pos in sprint_results.items():
                        pts = self._position_to_points(
                            pos, is_sprint=True
                        )
                        sim_points.setdefault(drv, 0.0)
                        sim_points[drv] += pts

                races_left -= 1

            all_season_points.append(sim_points)

        return self._aggregate(all_season_points, standings)

    def _simulate_single_race(
        self,
        driver_grid: dict[int, DriverState],
        race: RaceCalendarEntry,
        current_points: dict[int, float],
        races_remaining: int,
        total_rounds: int,
    ) -> dict[int, int]:
        """Simulate a single race using GridSimulator with championship context."""
        # Build championship context per driver
        sorted_by_pts = sorted(
            current_points.items(), key=lambda x: x[1], reverse=True
        )
        leader_pts = sorted_by_pts[0][1] if sorted_by_pts else 0

        phase = _determine_phase(races_remaining, total_rounds)

        # Compute average risk modifier for SC probability adjustment
        risk_mods = []
        for rank, (drv, pts) in enumerate(sorted_by_pts, 1):
            behind_pts = (
                sorted_by_pts[rank][1]
                if rank < len(sorted_by_pts)
                else 0
            )
            ctx = ChampionshipContext(
                driver_number=drv,
                championship_position=rank,
                points_gap_to_leader=int(leader_pts - pts),
                points_gap_to_behind=int(pts - behind_pts),
                races_remaining=races_remaining,
                phase=phase,
            )
            from rsw.strategy.situational_strategy import RaceContext

            race_ctx = RaceContext(
                current_lap=1,
                total_laps=race.total_laps,
                driver_position=rank,
                gap_to_ahead=None,
                gap_to_behind=None,
                safety_car_active=False,
                is_wet=False,
            )
            risk_mods.append(calculate_risk_modifier(ctx, race_ctx))

        avg_risk = np.mean(risk_mods) if risk_mods else 1.0

        # Adjust SC probability based on championship aggressiveness
        base_sc = 0.2
        sc_prob = base_sc * float(avg_risk)

        # Deep copy grid and add noise for race-to-race variance
        race_grid = copy.deepcopy(driver_grid)
        for drv in race_grid.values():
            pace = drv.last_lap_time or DEFAULT_PACE
            drv.last_lap_time = pace + random.gauss(0, 0.3)
            # Randomise starting grid slightly
            drv.position = max(
                1, drv.position + random.randint(-2, 2)
            )

        # Ensure positions are valid (no duplicates)
        sorted_grid = sorted(race_grid.values(), key=lambda d: d.position)
        for i, drv in enumerate(sorted_grid):
            drv.position = i + 1

        simulator = GridSimulator()
        return simulator.run_simulation(
            initial_state=race_grid,
            remaining_laps=race.total_laps,
            sc_probability=sc_prob,
        )

    # -------------------------------------------------------------------------
    # Points & DNF
    # -------------------------------------------------------------------------

    @staticmethod
    def _position_to_points(
        position: int,
        is_sprint: bool = False,
        fastest_lap_eligible: bool = False,
    ) -> float:
        """Convert finish position to championship points."""
        table = SPRINT_POINTS if is_sprint else RACE_POINTS
        pts = table.get(position, 0)
        if fastest_lap_eligible and not is_sprint and position <= 10:
            pts += 1
        return float(pts)

    @staticmethod
    def _apply_dnf(
        results: dict[int, int], grid_size: int
    ) -> dict[int, int]:
        """Apply random DNF probability. DNF drivers score 0 points."""
        dnf_drivers: set[int] = set()
        adjusted: dict[int, int] = {}

        for drv, pos in results.items():
            if random.random() < DNF_PROBABILITY:
                dnf_drivers.add(drv)
                adjusted[drv] = grid_size + 1
            else:
                adjusted[drv] = pos

        # Re-rank non-DNF drivers to close gaps
        non_dnf = [
            (drv, pos)
            for drv, pos in adjusted.items()
            if drv not in dnf_drivers
        ]
        non_dnf.sort(key=lambda x: x[1])
        for new_pos, (drv, _) in enumerate(non_dnf, 1):
            adjusted[drv] = new_pos

        return adjusted

    @staticmethod
    def _award_fastest_lap(results: dict[int, int]) -> int:
        """Pick a random top-10 finisher for fastest lap bonus."""
        top10 = [drv for drv, pos in results.items() if pos <= 10]
        if not top10:
            return -1
        return random.choice(top10)

    # -------------------------------------------------------------------------
    # Aggregation
    # -------------------------------------------------------------------------

    def _aggregate(
        self,
        all_season_points: list[dict[int, float]],
        standings: dict[int, dict[str, Any]],
    ) -> tuple[list[DriverStanding], list[ConstructorStanding]]:
        """Aggregate N simulations into championship standings."""
        n = len(all_season_points)
        if n == 0:
            return [], []

        # Collect all driver numbers
        all_drivers: set[int] = set()
        for sp in all_season_points:
            all_drivers.update(sp.keys())

        # Per-driver arrays
        driver_totals: dict[int, list[float]] = {
            drv: [] for drv in all_drivers
        }
        driver_positions: dict[int, list[int]] = {
            drv: [] for drv in all_drivers
        }

        for sp in all_season_points:
            # Compute championship positions for this simulation
            sorted_pts = sorted(
                [(drv, sp.get(drv, 0.0)) for drv in all_drivers],
                key=lambda x: x[1],
                reverse=True,
            )
            for rank, (drv, pts) in enumerate(sorted_pts, 1):
                driver_totals[drv].append(pts)
                driver_positions[drv].append(rank)

        # Build WDC standings
        wdc: list[DriverStanding] = []
        for drv in all_drivers:
            info = standings.get(drv, {})
            totals = np.array(driver_totals[drv])
            positions = np.array(driver_positions[drv])
            current_pts = info.get("points", 0.0)

            wdc.append(
                DriverStanding(
                    driver_number=drv,
                    name=info.get("name", str(drv)),
                    team=info.get("team", "Unknown"),
                    team_colour=info.get("team_colour", "FFFFFF"),
                    current_points=current_pts,
                    simulated_points_mean=round(
                        float(np.mean(totals)) - current_pts, 1
                    ),
                    simulated_points_std=round(float(np.std(totals)), 1),
                    total_points_mean=round(float(np.mean(totals)), 1),
                    total_points_p10=round(
                        float(np.percentile(totals, 10)), 1
                    ),
                    total_points_p90=round(
                        float(np.percentile(totals, 90)), 1
                    ),
                    predicted_position=round(float(np.mean(positions)), 1),
                    prob_champion=round(
                        float(np.sum(positions == 1)) / n, 3
                    ),
                    prob_top3=round(
                        float(np.sum(positions <= 3)) / n, 3
                    ),
                    prob_top10=round(
                        float(np.sum(positions <= 10)) / n, 3
                    ),
                )
            )

        wdc.sort(key=lambda d: d.total_points_mean, reverse=True)

        # Build WCC standings
        wcc = self._compute_wcc(wdc, all_season_points, standings)

        return wdc, wcc

    def _compute_wcc(
        self,
        wdc: list[DriverStanding],
        all_season_points: list[dict[int, float]],
        standings: dict[int, dict[str, Any]],
    ) -> list[ConstructorStanding]:
        """Compute World Constructors' Championship from driver data."""
        # Group drivers by team
        team_drivers: dict[str, list[int]] = {}
        team_colours: dict[str, str] = {}
        for d in wdc:
            team_drivers.setdefault(d.team, []).append(d.driver_number)
            team_colours[d.team] = d.team_colour

        n = len(all_season_points)
        wcc: list[ConstructorStanding] = []

        # Per-team totals across simulations
        team_totals: dict[str, list[float]] = {
            t: [] for t in team_drivers
        }
        for sp in all_season_points:
            for team, drivers in team_drivers.items():
                team_pts = sum(sp.get(drv, 0.0) for drv in drivers)
                team_totals[team].append(team_pts)

        for team, totals_list in team_totals.items():
            totals = np.array(totals_list)
            current_pts = sum(
                standings.get(drv, {}).get("points", 0.0)
                for drv in team_drivers[team]
            )

            # Compute position distribution
            all_team_pts = {
                t: np.array(team_totals[t]) for t in team_totals
            }
            champ_count = 0
            for i in range(n):
                this_pts = totals[i]
                is_first = all(
                    this_pts >= all_team_pts[t][i] for t in all_team_pts
                )
                if is_first:
                    champ_count += 1

            # Mean position
            positions = []
            for i in range(n):
                sorted_teams = sorted(
                    team_totals.keys(),
                    key=lambda t, idx=i: team_totals[t][idx],
                    reverse=True,
                )
                positions.append(sorted_teams.index(team) + 1)

            wcc.append(
                ConstructorStanding(
                    team=team,
                    team_colour=team_colours.get(team, "FFFFFF"),
                    driver_numbers=team_drivers[team],
                    current_points=current_pts,
                    total_points_mean=round(float(np.mean(totals)), 1),
                    total_points_p10=round(
                        float(np.percentile(totals, 10)), 1
                    ),
                    total_points_p90=round(
                        float(np.percentile(totals, 90)), 1
                    ),
                    predicted_position=round(
                        float(np.mean(positions)), 1
                    ),
                    prob_champion=round(champ_count / n, 3) if n > 0 else 0,
                )
            )

        wcc.sort(key=lambda c: c.total_points_mean, reverse=True)
        return wcc

    def _standings_to_results(
        self, standings: dict[int, dict[str, Any]]
    ) -> tuple[list[DriverStanding], list[ConstructorStanding]]:
        """Convert actual standings to result format (no simulation needed)."""
        sorted_drivers = sorted(
            standings.items(), key=lambda x: x[1]["points"], reverse=True
        )
        wdc = []
        for rank, (drv, info) in enumerate(sorted_drivers, 1):
            pts = info["points"]
            wdc.append(
                DriverStanding(
                    driver_number=drv,
                    name=info.get("name", str(drv)),
                    team=info.get("team", "Unknown"),
                    team_colour=info.get("team_colour", "FFFFFF"),
                    current_points=pts,
                    total_points_mean=pts,
                    total_points_p10=pts,
                    total_points_p90=pts,
                    predicted_position=float(rank),
                    prob_champion=1.0 if rank == 1 else 0.0,
                    prob_top3=1.0 if rank <= 3 else 0.0,
                    prob_top10=1.0 if rank <= 10 else 0.0,
                )
            )

        # WCC from actual
        team_drivers: dict[str, list[int]] = {}
        team_colours: dict[str, str] = {}
        for d in wdc:
            team_drivers.setdefault(d.team, []).append(d.driver_number)
            team_colours[d.team] = d.team_colour

        team_pts = {
            t: sum(
                standings.get(drv, {}).get("points", 0.0) for drv in drivers
            )
            for t, drivers in team_drivers.items()
        }
        sorted_teams = sorted(
            team_pts.items(), key=lambda x: x[1], reverse=True
        )
        wcc = []
        for rank, (team, pts) in enumerate(sorted_teams, 1):
            wcc.append(
                ConstructorStanding(
                    team=team,
                    team_colour=team_colours.get(team, "FFFFFF"),
                    driver_numbers=team_drivers[team],
                    current_points=pts,
                    total_points_mean=pts,
                    total_points_p10=pts,
                    total_points_p90=pts,
                    predicted_position=float(rank),
                    prob_champion=1.0 if rank == 1 else 0.0,
                )
            )

        return wdc, wcc
