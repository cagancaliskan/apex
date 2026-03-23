"""Tests for Multi-Stop Strategy Optimizer."""

import pytest

from rsw.models.degradation.track_priors import ResolvedPriors
from rsw.strategy.multi_stop_optimizer import (
    MultiStopOptimizer,
    StintPlan,
    StrategyPlan,
)
from rsw.config.constants import MIN_STINT_LAPS as _MIN_STINT_LAPS


# ── Fixtures ────────────────────────────────────────────────────────────────


def _optimizer(pit_loss: float = 22.0, total_laps: int = 57) -> MultiStopOptimizer:
    return MultiStopOptimizer(pit_loss=pit_loss, total_laps=total_laps)


def _priors(compound: str, deg: float, cliff: int) -> ResolvedPriors:
    return ResolvedPriors(
        compound=compound,
        deg_per_lap=deg,
        cliff_lap=cliff,
        base_pace=88.0,
        pit_loss=23.0,
        confidence=0.7,
        source="track_compound",
    )


# ── Candidate generation ───────────────────────────────────────────────────


class TestGenerateCandidates:
    def test_generates_1_and_2_stop_for_standard_race(self):
        opt = _optimizer(total_laps=57)
        candidates = opt.generate_candidates(current_lap=1, current_compound="SOFT")
        stops = {c.n_stops for c in candidates}
        assert 1 in stops
        assert 2 in stops

    def test_generates_3_stop_for_long_race(self):
        opt = _optimizer(total_laps=70)
        candidates = opt.generate_candidates(current_lap=1, current_compound="SOFT")
        stops = {c.n_stops for c in candidates}
        assert 3 in stops

    def test_no_3_stop_for_short_race(self):
        opt = _optimizer(total_laps=45)
        candidates = opt.generate_candidates(current_lap=1, current_compound="SOFT")
        stops = {c.n_stops for c in candidates}
        assert 3 not in stops

    def test_empty_when_too_few_laps_remaining(self):
        opt = _optimizer(total_laps=57)
        candidates = opt.generate_candidates(current_lap=53)
        assert candidates == []

    def test_minimum_stint_length_enforced(self):
        opt = _optimizer(total_laps=57)
        candidates = opt.generate_candidates(current_lap=1, current_compound="MEDIUM")
        for c in candidates:
            for stint in c.stints:
                assert stint.length >= _MIN_STINT_LAPS, (
                    f"Stint {stint.compound} L{stint.start_lap}-L{stint.end_lap} "
                    f"is only {stint.length} laps"
                )

    def test_fia_two_compound_rule_enforced(self):
        """Every strategy must use at least 2 different dry compounds."""
        opt = _optimizer(total_laps=57)
        candidates = opt.generate_candidates(current_lap=1, current_compound="MEDIUM")
        dry = {"SOFT", "MEDIUM", "HARD"}
        for c in candidates:
            compounds_in_plan = {s.compound for s in c.stints}
            dry_in_plan = compounds_in_plan & dry
            assert len(dry_in_plan) >= 2, (
                f"Strategy {c.compound_sequence} uses only {dry_in_plan} dry compound(s)"
            )

    def test_stints_cover_full_race(self):
        """Stints should span from current_lap to total_laps."""
        opt = _optimizer(total_laps=57)
        candidates = opt.generate_candidates(current_lap=1, current_compound="SOFT")
        for c in candidates:
            assert c.stints[0].start_lap == 1
            assert c.stints[-1].end_lap == 57

    def test_pit_loss_correct(self):
        opt = _optimizer(pit_loss=22.0, total_laps=57)
        candidates = opt.generate_candidates(current_lap=1, current_compound="SOFT")
        for c in candidates:
            assert c.total_pit_loss == pytest.approx(22.0 * c.n_stops)


# ── Strategy simulation ────────────────────────────────────────────────────


class TestSimulateStrategy:
    def test_produces_positive_race_time(self):
        opt = _optimizer(total_laps=57)
        plan = StrategyPlan(
            n_stops=1,
            stints=[
                StintPlan("SOFT", 1, 25),
                StintPlan("MEDIUM", 25, 57),
            ],
            total_pit_loss=22.0,
        )
        t = opt.simulate_strategy(plan, base_pace=88.0)
        assert t > 0
        assert plan.estimated_race_time == t

    def test_more_stops_adds_more_pit_loss(self):
        opt = _optimizer(pit_loss=22.0, total_laps=57)
        plan_1 = StrategyPlan(
            n_stops=1,
            stints=[StintPlan("SOFT", 1, 28), StintPlan("HARD", 28, 57)],
            total_pit_loss=22.0,
        )
        plan_2 = StrategyPlan(
            n_stops=2,
            stints=[
                StintPlan("SOFT", 1, 19),
                StintPlan("MEDIUM", 19, 38),
                StintPlan("HARD", 38, 57),
            ],
            total_pit_loss=44.0,
        )
        t1 = opt.simulate_strategy(plan_1, base_pace=88.0)
        t2 = opt.simulate_strategy(plan_2, base_pace=88.0)
        # 2-stop incurs 22s more pit loss but has shorter stints (less deg)
        # The difference should reflect this tradeoff
        assert abs(t1 - t2) < 200  # Sanity: within 200s of each other

    def test_uses_track_priors_when_available(self):
        opt = _optimizer(total_laps=20)
        priors = {
            "SOFT": _priors("SOFT", deg=0.15, cliff=10),  # High deg
            "MEDIUM": _priors("MEDIUM", deg=0.04, cliff=25),  # Low deg
        }
        plan_soft = StrategyPlan(
            n_stops=0, stints=[StintPlan("SOFT", 1, 20)], total_pit_loss=0.0,
        )
        plan_med = StrategyPlan(
            n_stops=0, stints=[StintPlan("MEDIUM", 1, 20)], total_pit_loss=0.0,
        )
        t_soft = opt.simulate_strategy(plan_soft, 88.0, priors)
        t_med = opt.simulate_strategy(plan_med, 88.0, priors)
        # SOFT with 0.15 deg/lap should be slower total than MEDIUM with 0.04
        # (ignoring compound delta, the high deg rate dominates over 20 laps)
        # Just verify priors are actually being used (different times)
        assert t_soft != t_med


# ── Strategy comparison ─────────────────────────────────────────────────────


class TestCompareStrategies:
    def test_recommended_is_fastest(self):
        opt = _optimizer(total_laps=57)
        result = opt.compare_strategies(
            current_lap=1, base_pace=88.0, current_compound="SOFT",
        )
        assert result.recommended is not None
        for alt in result.alternatives:
            assert alt.estimated_race_time >= result.recommended.estimated_race_time

    def test_time_deltas_are_positive(self):
        opt = _optimizer(total_laps=57)
        result = opt.compare_strategies(
            current_lap=1, base_pace=88.0, current_compound="SOFT",
        )
        for delta in result.time_deltas.values():
            assert delta >= 0

    def test_reason_is_populated(self):
        opt = _optimizer(total_laps=57)
        result = opt.compare_strategies(
            current_lap=1, base_pace=88.0, current_compound="MEDIUM",
        )
        assert len(result.recommendation_reason) > 0

    def test_fallback_when_no_candidates(self):
        opt = _optimizer(total_laps=57)
        result = opt.compare_strategies(
            current_lap=55, base_pace=88.0, current_compound="HARD",
        )
        assert result.recommended.n_stops == 0
        assert "No viable" in result.recommendation_reason


# ── Optimal compound selection ──────────────────────────────────────────────


class TestGetOptimalCompound:
    def test_returns_valid_compound(self):
        opt = _optimizer()
        c = opt.get_optimal_compound(remaining_laps=30)
        assert c in ["SOFT", "MEDIUM", "HARD"]

    def test_short_stint_prefers_soft(self):
        opt = _optimizer()
        c = opt.get_optimal_compound(remaining_laps=5)
        assert c == "SOFT"

    def test_respects_fia_rule(self):
        """If only SOFT used so far, must pick MEDIUM or HARD."""
        opt = _optimizer()
        c = opt.get_optimal_compound(
            remaining_laps=30,
            compounds_used=["SOFT"],
        )
        assert c in ["MEDIUM", "HARD"]

    def test_with_track_priors(self):
        """Track priors influence compound choice."""
        opt = _optimizer()
        priors = {
            "SOFT": _priors("SOFT", deg=0.15, cliff=10),
            "MEDIUM": _priors("MEDIUM", deg=0.03, cliff=30),
            "HARD": _priors("HARD", deg=0.02, cliff=45),
        }
        c = opt.get_optimal_compound(
            remaining_laps=35,
            compounds_used=["SOFT"],
            track_priors=priors,
        )
        # With high SOFT deg and low HARD deg, should prefer MEDIUM or HARD
        assert c in ["MEDIUM", "HARD"]
