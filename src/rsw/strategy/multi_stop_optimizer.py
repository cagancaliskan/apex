"""
Multi-Stop Strategy Optimizer.

Physics-based N-stop strategy comparison using TyreModel, FuelModel,
and TrackModel to simulate full stint-by-stint race time for each
candidate strategy. Replaces the hardcoded compound selection in
decision.py with data-driven optimization.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from rsw.config.constants import (
    CONFIDENCE_GAP_DIVISOR,
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    DEFAULT_BASE_PACE_SECONDS,
    DEFAULT_PIT_LOSS_SECONDS,
    DEFAULT_TOTAL_LAPS,
    LONG_RACE_THREE_STOP_THRESHOLD,
    MIN_STINT_LAPS,
    ONE_STOP_PIT_FRACTIONS,
    TWO_STOP_PIT_FRACTIONS,
)
from rsw.models.degradation.track_priors import ResolvedPriors
from rsw.models.physics.fuel_model import FuelModel
from rsw.models.physics.track_model import TrackModel
from rsw.models.physics.tyre_model import COMPOUND_PARAMS, TyreModel

# FIA regulation: must use at least 2 different dry compounds
_DRY_COMPOUNDS = ["SOFT", "MEDIUM", "HARD"]
_WET_COMPOUNDS = ["INTERMEDIATE", "WET"]


@dataclass
class StintPlan:
    """Plan for a single stint within a strategy."""

    compound: str
    start_lap: int
    end_lap: int

    @property
    def length(self) -> int:
        return self.end_lap - self.start_lap


@dataclass
class StrategyPlan:
    """Complete multi-stop strategy plan."""

    n_stops: int
    stints: list[StintPlan]
    total_pit_loss: float
    estimated_race_time: float = 0.0
    compound_sequence: str = ""
    confidence: float = 0.0

    def __post_init__(self):
        if not self.compound_sequence and self.stints:
            self.compound_sequence = "-".join(
                s.compound[0] for s in self.stints
            )


@dataclass
class StrategyComparison:
    """Result of comparing multiple strategies."""

    recommended: StrategyPlan
    alternatives: list[StrategyPlan] = field(default_factory=list)
    time_deltas: dict[str, float] = field(default_factory=dict)
    recommendation_reason: str = ""


class MultiStopOptimizer:
    """
    Physics-based multi-stop strategy optimizer.

    Generates candidate 1/2/3-stop strategies, simulates each using
    TyreModel + FuelModel + TrackModel, and ranks by total race time.
    """

    def __init__(
        self,
        pit_loss: float = DEFAULT_PIT_LOSS_SECONDS,
        total_laps: int = DEFAULT_TOTAL_LAPS,
    ):
        self.pit_loss = pit_loss
        self.total_laps = total_laps
        self.fuel_model = FuelModel()
        self.track_model = TrackModel()

    def generate_candidates(
        self,
        current_lap: int = 1,
        current_compound: str = "MEDIUM",
        compounds_used: list[str] | None = None,
    ) -> list[StrategyPlan]:
        """
        Generate all viable strategy candidates from the current race position.

        Enforces FIA rule: at least 2 different dry compounds must be used.
        Minimum stint length: 8 laps.
        """
        if compounds_used is None:
            compounds_used = []

        remaining = self.total_laps - current_lap
        if remaining < MIN_STINT_LAPS:
            return []

        candidates: list[StrategyPlan] = []
        candidates.extend(self._generate_1_stop(current_lap, current_compound, compounds_used))
        candidates.extend(self._generate_2_stop(current_lap, current_compound, compounds_used))
        if self.total_laps > LONG_RACE_THREE_STOP_THRESHOLD and remaining > 3 * MIN_STINT_LAPS:
            candidates.extend(self._generate_3_stop(current_lap, current_compound, compounds_used))

        return candidates

    def simulate_strategy(
        self,
        strategy: StrategyPlan,
        base_pace: float,
        track_priors: dict[str, ResolvedPriors] | None = None,
    ) -> float:
        """
        Simulate total race time for a strategy using physics models.

        For each stint, computes per-lap time = base_pace + tyre_penalty
        + fuel_penalty - track_evolution. Adds pit_loss at each stop.

        Args:
            strategy: The strategy plan to simulate
            base_pace: Session baseline lap time
            track_priors: Optional track-learned priors for learned deg rates

        Returns:
            Estimated total race time (seconds) from first stint start to finish.
        """
        total_time = 0.0

        for i, stint in enumerate(strategy.stints):
            # Use track-learned deg rate if available and better than physics model
            compound = stint.compound
            use_learned_deg = (
                track_priors is not None
                and compound in track_priors
                and track_priors[compound].source != "static_default"
            )

            tyre = TyreModel(compound)
            compound_delta = tyre.get_compound_pace_delta()

            for lap_offset in range(stint.length):
                race_lap = stint.start_lap + lap_offset

                # Tyre penalty: use learned deg or physics model
                if use_learned_deg:
                    learned_deg = track_priors[compound].deg_per_lap
                    tyre_penalty = learned_deg * lap_offset
                else:
                    tyre_penalty = tyre.get_tyre_penalty(lap_offset)

                # Fuel penalty (lighter car = faster)
                fuel_penalty = self.fuel_model.get_fuel_penalty(race_lap)

                # Track evolution (rubber buildup = faster)
                track_gain = self.track_model.get_lap_evolution(race_lap)

                lap_time = base_pace + compound_delta + tyre_penalty + fuel_penalty - track_gain
                total_time += lap_time

            # Add pit loss (except after last stint)
            if i < len(strategy.stints) - 1:
                total_time += self.pit_loss

        strategy.estimated_race_time = total_time
        return total_time

    def compare_strategies(
        self,
        current_lap: int,
        base_pace: float,
        current_compound: str = "MEDIUM",
        compounds_used: list[str] | None = None,
        track_priors: dict[str, ResolvedPriors] | None = None,
    ) -> StrategyComparison:
        """
        Compare all viable strategies and return the recommendation.

        Args:
            current_lap: Current race lap
            base_pace: Session baseline lap time
            current_compound: Current tyre compound
            compounds_used: Compounds already used in the race
            track_priors: Optional track-learned priors

        Returns:
            StrategyComparison with ranked strategies and time deltas
        """
        candidates = self.generate_candidates(current_lap, current_compound, compounds_used)
        if not candidates:
            # No viable strategies — stay out
            fallback = StrategyPlan(
                n_stops=0,
                stints=[StintPlan(current_compound, current_lap, self.total_laps)],
                total_pit_loss=0.0,
            )
            self.simulate_strategy(fallback, base_pace, track_priors)
            return StrategyComparison(
                recommended=fallback,
                recommendation_reason="No viable pit strategies remaining",
            )

        # Simulate all candidates
        for candidate in candidates:
            self.simulate_strategy(candidate, base_pace, track_priors)

        # Sort by total time
        candidates.sort(key=lambda s: s.estimated_race_time)

        best = candidates[0]
        best.confidence = _compute_confidence(candidates)

        # Build time deltas relative to best
        time_deltas = {}
        for c in candidates[1:]:
            key = f"{c.n_stops}-stop ({c.compound_sequence})"
            time_deltas[key] = round(c.estimated_race_time - best.estimated_race_time, 2)

        reason = _build_reason(best, candidates)

        return StrategyComparison(
            recommended=best,
            alternatives=candidates[1:],
            time_deltas=time_deltas,
            recommendation_reason=reason,
        )

    def get_optimal_compound(
        self,
        remaining_laps: int,
        stint_number: int = 2,
        compounds_used: list[str] | None = None,
        track_priors: dict[str, ResolvedPriors] | None = None,
    ) -> str:
        """
        Select the optimal compound for the next stint.

        Uses physics simulation to pick the compound that minimizes
        remaining race time. Falls back to heuristic if simulation
        produces no candidates.

        Args:
            remaining_laps: Laps remaining in the race
            stint_number: Which stint this will be (1-indexed)
            compounds_used: Compounds already used
            track_priors: Optional track-learned priors

        Returns:
            Best compound name (e.g. "MEDIUM")
        """
        if compounds_used is None:
            compounds_used = []

        if remaining_laps < MIN_STINT_LAPS:
            return "SOFT"

        # Determine which compounds are valid for next stint
        # Must ensure FIA 2-compound rule is satisfied
        available = _DRY_COMPOUNDS[:]
        used_dry = [c for c in compounds_used if c in _DRY_COMPOUNDS]
        needs_new_compound = len(set(used_dry)) < 2 and len(used_dry) > 0

        if needs_new_compound:
            # Must pick a compound not yet used
            available = [c for c in _DRY_COMPOUNDS if c not in used_dry]
            if not available:
                available = _DRY_COMPOUNDS[:]

        # Simulate each compound for the remaining laps
        best_compound = available[0]
        best_time = float("inf")
        base_pace = DEFAULT_BASE_PACE_SECONDS  # Will be dominated by relative differences

        for compound in available:
            stint = StintPlan(compound, 0, remaining_laps)
            plan = StrategyPlan(n_stops=0, stints=[stint], total_pit_loss=0.0)
            t = self.simulate_strategy(plan, base_pace, track_priors)
            if t < best_time:
                best_time = t
                best_compound = compound

        return best_compound

    # ── Private: Strategy generation ────────────────────────────────────────

    def _generate_1_stop(
        self,
        current_lap: int,
        current_compound: str,
        compounds_used: list[str],
    ) -> list[StrategyPlan]:
        """Generate 1-stop strategies from current position."""
        remaining = self.total_laps - current_lap
        candidates: list[StrategyPlan] = []

        # Possible second compounds (must differ from first for FIA rule)
        all_used = set(compounds_used + [current_compound])
        second_options = _DRY_COMPOUNDS[:]

        # If only one dry compound used so far, the second MUST be different
        dry_used = all_used & set(_DRY_COMPOUNDS)
        if len(dry_used) < 2:
            second_options = [c for c in _DRY_COMPOUNDS if c not in dry_used]
            if not second_options:
                second_options = _DRY_COMPOUNDS[:]

        # Try pit laps at intervals through the remaining distance
        for pit_frac in ONE_STOP_PIT_FRACTIONS:
            pit_offset = int(remaining * pit_frac)
            pit_lap = current_lap + pit_offset

            stint1_len = pit_lap - current_lap
            stint2_len = self.total_laps - pit_lap

            if stint1_len < MIN_STINT_LAPS or stint2_len < MIN_STINT_LAPS:
                continue

            for second_compound in second_options:
                stints = [
                    StintPlan(current_compound, current_lap, pit_lap),
                    StintPlan(second_compound, pit_lap, self.total_laps),
                ]
                candidates.append(StrategyPlan(
                    n_stops=1,
                    stints=stints,
                    total_pit_loss=self.pit_loss,
                ))

        return candidates

    def _generate_2_stop(
        self,
        current_lap: int,
        current_compound: str,
        compounds_used: list[str],
    ) -> list[StrategyPlan]:
        """Generate 2-stop strategies."""
        remaining = self.total_laps - current_lap
        if remaining < 3 * MIN_STINT_LAPS:
            return []

        candidates: list[StrategyPlan] = []

        # Generate compound permutations ensuring FIA 2-compound rule
        all_used_dry = set(c for c in compounds_used if c in _DRY_COMPOUNDS)
        all_used_dry.add(current_compound) if current_compound in _DRY_COMPOUNDS else None

        for c2, c3 in itertools.product(_DRY_COMPOUNDS, repeat=2):
            all_compounds = all_used_dry | {c2, c3}
            if current_compound in _DRY_COMPOUNDS:
                all_compounds.add(current_compound)
            if len(all_compounds & set(_DRY_COMPOUNDS)) < 2:
                continue

            # Try pit laps at 1/3 and 2/3 of remaining
            for frac1, frac2 in TWO_STOP_PIT_FRACTIONS:
                pit1 = current_lap + int(remaining * frac1)
                pit2 = current_lap + int(remaining * frac2)

                s1_len = pit1 - current_lap
                s2_len = pit2 - pit1
                s3_len = self.total_laps - pit2

                if any(s < MIN_STINT_LAPS for s in [s1_len, s2_len, s3_len]):
                    continue

                stints = [
                    StintPlan(current_compound, current_lap, pit1),
                    StintPlan(c2, pit1, pit2),
                    StintPlan(c3, pit2, self.total_laps),
                ]
                candidates.append(StrategyPlan(
                    n_stops=2,
                    stints=stints,
                    total_pit_loss=self.pit_loss * 2,
                ))

        return candidates

    def _generate_3_stop(
        self,
        current_lap: int,
        current_compound: str,
        compounds_used: list[str],
    ) -> list[StrategyPlan]:
        """Generate 3-stop strategies (only for long races)."""
        remaining = self.total_laps - current_lap
        if remaining < 4 * MIN_STINT_LAPS:
            return []

        candidates: list[StrategyPlan] = []
        interval = remaining // 4

        for c2, c3, c4 in itertools.product(_DRY_COMPOUNDS, repeat=3):
            all_dry = {current_compound, c2, c3, c4} & set(_DRY_COMPOUNDS)
            if len(all_dry) < 2:
                continue

            pit1 = current_lap + interval
            pit2 = current_lap + 2 * interval
            pit3 = current_lap + 3 * interval

            s_lens = [pit1 - current_lap, pit2 - pit1, pit3 - pit2, self.total_laps - pit3]
            if any(s < MIN_STINT_LAPS for s in s_lens):
                continue

            stints = [
                StintPlan(current_compound, current_lap, pit1),
                StintPlan(c2, pit1, pit2),
                StintPlan(c3, pit2, pit3),
                StintPlan(c4, pit3, self.total_laps),
            ]
            candidates.append(StrategyPlan(
                n_stops=3,
                stints=stints,
                total_pit_loss=self.pit_loss * 3,
            ))

        return candidates


# ── Private helpers ─────────────────────────────────────────────────────────


def _compute_confidence(candidates: list[StrategyPlan]) -> float:
    """Confidence = how much better the best is vs second-best."""
    if len(candidates) < 2:
        return 0.8

    gap = candidates[1].estimated_race_time - candidates[0].estimated_race_time
    # CONFIDENCE_GAP_DIVISOR s gap = high confidence, <1s = low confidence
    return min(CONFIDENCE_MAX, max(CONFIDENCE_MIN, CONFIDENCE_MIN + gap / CONFIDENCE_GAP_DIVISOR))


def _build_reason(best: StrategyPlan, candidates: list[StrategyPlan]) -> str:
    """Build human-readable recommendation reason."""
    if len(candidates) < 2:
        return f"{best.n_stops}-stop ({best.compound_sequence}) is the only viable strategy"

    second = candidates[1]
    gap = round(second.estimated_race_time - best.estimated_race_time, 1)
    return (
        f"{best.n_stops}-stop ({best.compound_sequence}) is {gap}s faster "
        f"than {second.n_stops}-stop ({second.compound_sequence})"
    )
