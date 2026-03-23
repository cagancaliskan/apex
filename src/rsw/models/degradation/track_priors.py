"""
Track-learned prior resolution layer.

Resolves degradation priors through a fallback chain:
  track+driver > track+compound > season+driver > static defaults

This bridges the gap between TrackLearner/SeasonLearner outputs
and the consumers (calibration warm-start, pit_window, decision engine).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from rsw.config.constants import (
    CLIFF_AGES,
    DEFAULT_BASE_PACE_SECONDS,
    DEFAULT_PIT_LOSS_SECONDS,
    TRACK_PRIORS_MIN_SAMPLES,
)
from rsw.models.physics.track_characteristics import TrackCharacteristics

from .calibration import COMPOUND_PRIORS

DEFAULT_PIT_LOSS: float = DEFAULT_PIT_LOSS_SECONDS
_MIN_PIT_SAMPLES: int = TRACK_PRIORS_MIN_SAMPLES


@dataclass
class ResolvedPriors:
    """Resolved priors for a compound at a specific track/driver context."""

    compound: str
    deg_per_lap: float  # Learned or calibration default
    cliff_lap: int  # Learned or _CLIFF_AGES default
    base_pace: float  # Learned or 90.0
    pit_loss: float  # Track-specific or 22.0
    confidence: float  # 0-1, based on sample counts
    source: str  # "track_driver" | "track_compound" | "season" | "static_default"


def resolve_compound_priors(
    compound: str,
    track_chars: TrackCharacteristics | None = None,
    season_learner: Any | None = None,
    driver_number: int | None = None,
    year: int = 2024,
) -> ResolvedPriors:
    """
    Resolve degradation priors through the fallback chain.

    Priority:
      1. Track + driver-specific (highest confidence)
      2. Track + compound average
      3. Season + driver (cross-circuit)
      4. Static calibration defaults (lowest confidence)

    Args:
        compound: Tyre compound name
        track_chars: Learned track characteristics (may be None)
        season_learner: SeasonLearner instance (may be None)
        driver_number: Driver number for driver-specific lookup
        year: Season year for season learner

    Returns:
        ResolvedPriors with the best available data
    """
    compound_upper = compound.upper()
    pit_loss = resolve_pit_loss(track_chars)

    # --- Priority 1: Track + driver-specific ---
    if (
        track_chars is not None
        and driver_number is not None
        and driver_number in track_chars.driver_profiles
    ):
        profile = track_chars.driver_profiles[driver_number]
        if compound_upper in profile.compound_profiles:
            cp = profile.compound_profiles[compound_upper]
            if cp.sample_count >= 2:
                cliff_lap = _track_cliff_lap(compound_upper, track_chars)
                confidence = min(1.0, cp.sample_count / 10.0)
                return ResolvedPriors(
                    compound=compound_upper,
                    deg_per_lap=cp.avg_deg_per_lap,
                    cliff_lap=cliff_lap,
                    base_pace=cp.avg_base_pace,
                    pit_loss=pit_loss,
                    confidence=confidence,
                    source="track_driver",
                )

    # --- Priority 2: Track + compound average ---
    if track_chars is not None and compound_upper in track_chars.compound_degradation:
        cd = track_chars.compound_degradation[compound_upper]
        if cd.sample_count >= 2:
            base_pace = _track_base_pace(driver_number, track_chars)
            confidence = min(1.0, cd.sample_count / 10.0)
            return ResolvedPriors(
                compound=compound_upper,
                deg_per_lap=cd.avg_deg_per_lap,
                cliff_lap=cd.cliff_lap,
                base_pace=base_pace,
                pit_loss=pit_loss,
                confidence=confidence,
                source="track_compound",
            )

    # --- Priority 3: Season + driver (cross-circuit) ---
    if season_learner is not None and driver_number is not None:
        # SeasonLearner.get_driver_priors(year, driver_number, compound)
        try:
            bp, deg = season_learner.get_driver_priors(year, driver_number, compound_upper)
            if bp is not None and deg is not None:
                cliff_lap = _default_cliff_lap(compound_upper)
                return ResolvedPriors(
                    compound=compound_upper,
                    deg_per_lap=deg,
                    cliff_lap=cliff_lap,
                    base_pace=bp,
                    pit_loss=pit_loss,
                    confidence=0.4,
                    source="season",
                )
        except (AttributeError, TypeError):
            pass

    # --- Priority 4: Static calibration defaults ---
    prior = COMPOUND_PRIORS.get(compound_upper, COMPOUND_PRIORS["MEDIUM"])
    return ResolvedPriors(
        compound=compound_upper,
        deg_per_lap=prior.deg_per_lap,
        cliff_lap=prior.cliff_lap,
        base_pace=DEFAULT_BASE_PACE_SECONDS,
        pit_loss=pit_loss,
        confidence=0.2,
        source="static_default",
    )


def resolve_pit_loss(track_chars: TrackCharacteristics | None) -> float:
    """
    Get track-specific pit loss or default.

    Only uses learned value when sample count is sufficient.
    """
    if (
        track_chars is not None
        and track_chars.pit_stop_count >= _MIN_PIT_SAMPLES
    ):
        return track_chars.actual_pit_loss_mean
    return DEFAULT_PIT_LOSS


def resolve_cliff_age(
    compound: str,
    track_chars: TrackCharacteristics | None = None,
) -> int:
    """Get cliff age (in tyre laps) for a compound, preferring track-learned data."""
    compound_upper = compound.upper()
    if track_chars is not None and compound_upper in track_chars.compound_degradation:
        cd = track_chars.compound_degradation[compound_upper]
        if cd.sample_count >= 2:
            return cd.cliff_lap
    return _default_cliff_lap(compound_upper)


def resolve_all_compounds(
    track_chars: TrackCharacteristics | None = None,
    season_learner: Any | None = None,
    driver_number: int | None = None,
    year: int = 2024,
) -> dict[str, ResolvedPriors]:
    """Resolve priors for all standard compounds."""
    compounds = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]
    return {
        c: resolve_compound_priors(c, track_chars, season_learner, driver_number, year)
        for c in compounds
    }


# --- Private helpers ---


def _track_cliff_lap(compound: str, track_chars: TrackCharacteristics) -> int:
    """Get cliff lap from track data or default."""
    if compound in track_chars.compound_degradation:
        return track_chars.compound_degradation[compound].cliff_lap
    return _default_cliff_lap(compound)


def _track_base_pace(
    driver_number: int | None,
    track_chars: TrackCharacteristics,
) -> float:
    """Get base pace from driver profile or track average."""
    if driver_number is not None and driver_number in track_chars.driver_profiles:
        return track_chars.driver_profiles[driver_number].overall_base_pace
    return DEFAULT_BASE_PACE_SECONDS


def _default_cliff_lap(compound: str) -> int:
    """Static default cliff lap for a compound."""
    return CLIFF_AGES.get(compound, CLIFF_AGES["MEDIUM"])
