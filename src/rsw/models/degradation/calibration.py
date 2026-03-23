"""
Calibration and warm-start parameters for degradation models.

These priors are based on historical F1 data and can be overridden
per-track or per-session.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rsw.config.constants import DEFAULT_BASE_PACE_SECONDS, TRACK_PRIORS_CONFIDENCE_THRESHOLD

if TYPE_CHECKING:
    from rsw.models.degradation.track_priors import ResolvedPriors


@dataclass
class CompoundPrior:
    """Prior parameters for a tyre compound."""

    compound: str
    deg_per_lap: float  # Expected degradation in seconds per lap
    deg_std: float  # Standard deviation of degradation
    cliff_lap: int  # Expected lap where cliff might occur
    cliff_risk_threshold: float  # Deg slope indicating high cliff risk


# Default compound priors (average across tracks)
COMPOUND_PRIORS = {
    "SOFT": CompoundPrior(
        compound="SOFT",
        deg_per_lap=0.08,  # ~0.08s/lap degradation
        deg_std=0.03,
        cliff_lap=20,
        cliff_risk_threshold=0.12,
    ),
    "MEDIUM": CompoundPrior(
        compound="MEDIUM",
        deg_per_lap=0.05,  # ~0.05s/lap degradation
        deg_std=0.02,
        cliff_lap=35,
        cliff_risk_threshold=0.10,
    ),
    "HARD": CompoundPrior(
        compound="HARD",
        deg_per_lap=0.03,  # ~0.03s/lap degradation
        deg_std=0.015,
        cliff_lap=50,
        cliff_risk_threshold=0.08,
    ),
    "INTERMEDIATE": CompoundPrior(
        compound="INTERMEDIATE",
        deg_per_lap=0.10,
        deg_std=0.05,
        cliff_lap=25,
        cliff_risk_threshold=0.15,
    ),
    "WET": CompoundPrior(
        compound="WET",
        deg_per_lap=0.12,
        deg_std=0.06,
        cliff_lap=20,
        cliff_risk_threshold=0.18,
    ),
}


def get_warm_start_params(
    compound: str,
    base_pace: float | None = None,
    track_multiplier: float = 1.0,
) -> tuple[float, float]:
    """
    Get warm start parameters for a compound.

    Args:
        compound: Tyre compound name
        base_pace: Optional base lap time (if known from practice)
        track_multiplier: Track-specific degradation multiplier

    Returns:
        Tuple of (base_pace, deg_slope)
    """
    prior = COMPOUND_PRIORS.get(
        compound.upper(),
        COMPOUND_PRIORS["MEDIUM"],  # Default to medium if unknown
    )

    # If base pace not provided, we'll rely on first observations
    if base_pace is None:
        base_pace = DEFAULT_BASE_PACE_SECONDS

    deg_slope = prior.deg_per_lap * track_multiplier

    return base_pace, deg_slope


def get_cliff_risk_threshold(compound: str) -> float:
    """Get the degradation slope threshold for cliff risk."""
    prior = COMPOUND_PRIORS.get(compound.upper(), COMPOUND_PRIORS["MEDIUM"])
    return prior.cliff_risk_threshold


def get_expected_cliff_lap(compound: str) -> int:
    """Get expected lap where cliff might occur."""
    prior = COMPOUND_PRIORS.get(compound.upper(), COMPOUND_PRIORS["MEDIUM"])
    return prior.cliff_lap


def get_track_aware_warm_start(
    compound: str,
    track_priors: "ResolvedPriors | None" = None,
    base_pace: float | None = None,
) -> tuple[float, float]:
    """
    Get warm start params using track-learned priors when available.

    Falls back to generic compound defaults when priors are absent or
    low-confidence (< 0.3).

    Args:
        compound: Tyre compound name
        track_priors: Resolved track/season priors (may be None)
        base_pace: Optional known base pace override

    Returns:
        Tuple of (base_pace, deg_slope)
    """
    if track_priors is not None and track_priors.confidence > TRACK_PRIORS_CONFIDENCE_THRESHOLD:
        bp = base_pace if base_pace is not None else track_priors.base_pace
        return bp, track_priors.deg_per_lap
    return get_warm_start_params(compound, base_pace)
