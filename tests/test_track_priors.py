"""Tests for track-learned prior resolution layer."""

import pytest

from rsw.models.degradation.calibration import COMPOUND_PRIORS, get_track_aware_warm_start
from rsw.models.degradation.track_priors import (
    DEFAULT_PIT_LOSS,
    ResolvedPriors,
    resolve_all_compounds,
    resolve_cliff_age,
    resolve_compound_priors,
    resolve_pit_loss,
)
from rsw.models.physics.track_characteristics import (
    CompoundDegradation,
    DriverCompoundProfile,
    DriverProfile,
    TrackCharacteristics,
)


# ── Fixtures ────────────────────────────────────────────────────────────────


def _make_track_chars(
    pit_loss: float = 23.5,
    pit_count: int = 20,
    compounds: dict[str, tuple[float, int, int]] | None = None,
    drivers: dict[int, dict[str, tuple[float, float, int]]] | None = None,
) -> TrackCharacteristics:
    """Helper to build TrackCharacteristics with compound/driver data."""
    tc = TrackCharacteristics(
        circuit_name="Test Circuit",
        circuit_key="test",
        actual_pit_loss_mean=pit_loss,
        actual_pit_loss_std=1.2,
        pit_stop_count=pit_count,
    )
    if compounds:
        for name, (deg, cliff, samples) in compounds.items():
            tc.compound_degradation[name] = CompoundDegradation(
                compound=name, avg_deg_per_lap=deg, cliff_lap=cliff, sample_count=samples,
            )
    if drivers:
        for drv_num, comp_data in drivers.items():
            profile = DriverProfile(driver_number=drv_num, overall_base_pace=88.0)
            for comp, (deg, pace, samples) in comp_data.items():
                profile.compound_profiles[comp] = DriverCompoundProfile(
                    compound=comp, avg_deg_per_lap=deg, avg_base_pace=pace, sample_count=samples,
                )
            tc.driver_profiles[drv_num] = profile
    return tc


class _MockSeasonLearner:
    """Minimal mock for SeasonLearner.get_driver_priors()."""

    def __init__(self, data: dict[tuple[int, int, str], tuple[float | None, float | None]]):
        self._data = data

    def get_driver_priors(self, year: int, driver_number: int, compound: str):
        return self._data.get((year, driver_number, compound), (None, None))


# ── resolve_compound_priors ─────────────────────────────────────────────────


class TestResolveCompoundPriors:
    def test_static_default_when_no_data(self):
        """No track/season data → static calibration defaults."""
        p = resolve_compound_priors("SOFT")
        assert p.source == "static_default"
        assert p.deg_per_lap == COMPOUND_PRIORS["SOFT"].deg_per_lap
        assert p.cliff_lap == COMPOUND_PRIORS["SOFT"].cliff_lap
        assert p.base_pace == 90.0
        assert p.pit_loss == DEFAULT_PIT_LOSS
        assert p.confidence == 0.2

    def test_track_compound_used_when_available(self):
        """Track compound data present → use track_compound source."""
        tc = _make_track_chars(compounds={"SOFT": (0.10, 14, 6)})
        p = resolve_compound_priors("SOFT", track_chars=tc)
        assert p.source == "track_compound"
        assert p.deg_per_lap == 0.10
        assert p.cliff_lap == 14
        assert p.confidence == pytest.approx(0.6)

    def test_track_compound_skipped_when_low_samples(self):
        """Track compound with <2 samples falls through to default."""
        tc = _make_track_chars(compounds={"SOFT": (0.10, 14, 1)})
        p = resolve_compound_priors("SOFT", track_chars=tc)
        assert p.source == "static_default"

    def test_track_driver_takes_priority(self):
        """Track + driver-specific data beats track + compound."""
        tc = _make_track_chars(
            compounds={"MEDIUM": (0.06, 28, 10)},
            drivers={44: {"MEDIUM": (0.045, 87.5, 4)}},
        )
        p = resolve_compound_priors("MEDIUM", track_chars=tc, driver_number=44)
        assert p.source == "track_driver"
        assert p.deg_per_lap == 0.045
        assert p.base_pace == 87.5

    def test_track_driver_falls_to_compound_when_wrong_driver(self):
        """Driver not in profiles → track_compound."""
        tc = _make_track_chars(
            compounds={"HARD": (0.035, 35, 5)},
            drivers={44: {"HARD": (0.03, 87.0, 3)}},
        )
        p = resolve_compound_priors("HARD", track_chars=tc, driver_number=1)
        assert p.source == "track_compound"

    def test_season_learner_used_when_no_track_data(self):
        """No track data, season learner present → season source."""
        sl = _MockSeasonLearner({(2024, 44, "SOFT"): (86.0, 0.09)})
        p = resolve_compound_priors("SOFT", season_learner=sl, driver_number=44, year=2024)
        assert p.source == "season"
        assert p.deg_per_lap == 0.09
        assert p.base_pace == 86.0
        assert p.confidence == 0.4

    def test_season_learner_none_result_falls_to_default(self):
        """Season learner returns (None, None) → static default."""
        sl = _MockSeasonLearner({})
        p = resolve_compound_priors("SOFT", season_learner=sl, driver_number=44, year=2024)
        assert p.source == "static_default"

    def test_case_insensitive_compound(self):
        """Compound lookup is case-insensitive."""
        tc = _make_track_chars(compounds={"SOFT": (0.10, 14, 6)})
        p = resolve_compound_priors("soft", track_chars=tc)
        assert p.compound == "SOFT"
        assert p.source == "track_compound"

    def test_unknown_compound_uses_medium_defaults(self):
        """Unknown compound falls back to MEDIUM defaults."""
        p = resolve_compound_priors("HYPERSOFT")
        assert p.deg_per_lap == COMPOUND_PRIORS["MEDIUM"].deg_per_lap


# ── resolve_pit_loss ────────────────────────────────────────────────────────


class TestResolvePitLoss:
    def test_default_when_no_data(self):
        assert resolve_pit_loss(None) == DEFAULT_PIT_LOSS

    def test_default_when_low_samples(self):
        tc = _make_track_chars(pit_loss=25.0, pit_count=3)
        assert resolve_pit_loss(tc) == DEFAULT_PIT_LOSS

    def test_learned_when_sufficient_samples(self):
        tc = _make_track_chars(pit_loss=23.5, pit_count=20)
        assert resolve_pit_loss(tc) == 23.5

    def test_threshold_boundary(self):
        """Exactly 5 samples → use learned value."""
        tc = _make_track_chars(pit_loss=21.0, pit_count=5)
        assert resolve_pit_loss(tc) == 21.0


# ── resolve_cliff_age ───────────────────────────────────────────────────────


class TestResolveCliffAge:
    def test_default_soft(self):
        assert resolve_cliff_age("SOFT") == 12

    def test_default_hard(self):
        assert resolve_cliff_age("HARD") == 30

    def test_track_learned_cliff(self):
        tc = _make_track_chars(compounds={"SOFT": (0.10, 18, 5)})
        assert resolve_cliff_age("SOFT", tc) == 18

    def test_track_low_samples_uses_default(self):
        tc = _make_track_chars(compounds={"SOFT": (0.10, 18, 1)})
        assert resolve_cliff_age("SOFT", tc) == 12


# ── resolve_all_compounds ──────────────────────────────────────────────────


class TestResolveAllCompounds:
    def test_returns_all_five_compounds(self):
        result = resolve_all_compounds()
        assert set(result.keys()) == {"SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"}
        for priors in result.values():
            assert priors.source == "static_default"

    def test_mixed_sources(self):
        tc = _make_track_chars(compounds={"SOFT": (0.10, 14, 6)})
        result = resolve_all_compounds(track_chars=tc)
        assert result["SOFT"].source == "track_compound"
        assert result["MEDIUM"].source == "static_default"


# ── get_track_aware_warm_start (calibration.py addition) ────────────────────


class TestGetTrackAwareWarmStart:
    def test_with_high_confidence_priors(self):
        priors = ResolvedPriors(
            compound="SOFT", deg_per_lap=0.10, cliff_lap=14,
            base_pace=86.0, pit_loss=23.0, confidence=0.6, source="track_compound",
        )
        bp, deg = get_track_aware_warm_start("SOFT", track_priors=priors)
        assert bp == 86.0
        assert deg == 0.10

    def test_with_low_confidence_falls_back(self):
        priors = ResolvedPriors(
            compound="SOFT", deg_per_lap=0.10, cliff_lap=14,
            base_pace=86.0, pit_loss=23.0, confidence=0.2, source="static_default",
        )
        bp, deg = get_track_aware_warm_start("SOFT", track_priors=priors)
        # Should fall back to static defaults
        assert deg == COMPOUND_PRIORS["SOFT"].deg_per_lap

    def test_base_pace_override(self):
        priors = ResolvedPriors(
            compound="SOFT", deg_per_lap=0.10, cliff_lap=14,
            base_pace=86.0, pit_loss=23.0, confidence=0.6, source="track_compound",
        )
        bp, deg = get_track_aware_warm_start("SOFT", track_priors=priors, base_pace=84.0)
        assert bp == 84.0
        assert deg == 0.10

    def test_none_priors_falls_back(self):
        bp, deg = get_track_aware_warm_start("SOFT")
        assert deg == COMPOUND_PRIORS["SOFT"].deg_per_lap
