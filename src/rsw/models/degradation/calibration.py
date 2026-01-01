"""
Calibration and warm-start parameters for degradation models.

These priors are based on historical F1 data and can be overridden
per-track or per-session.
"""

from dataclasses import dataclass


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
        COMPOUND_PRIORS["MEDIUM"]  # Default to medium if unknown
    )
    
    # If base pace not provided, we'll rely on first observations
    # Use 90s as a placeholder (will be updated by first laps)
    if base_pace is None:
        base_pace = 90.0
    
    deg_slope = prior.deg_per_lap * track_multiplier
    
    return base_pace, deg_slope


def get_cliff_risk_threshold(compound: str) -> float:
    """Get the degradation slope threshold for cliff risk."""
    prior = COMPOUND_PRIORS.get(
        compound.upper(),
        COMPOUND_PRIORS["MEDIUM"]
    )
    return prior.cliff_risk_threshold


def get_expected_cliff_lap(compound: str) -> int:
    """Get expected lap where cliff might occur."""
    prior = COMPOUND_PRIORS.get(
        compound.upper(),
        COMPOUND_PRIORS["MEDIUM"]
    )
    return prior.cliff_lap
