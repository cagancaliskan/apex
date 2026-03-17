"""
Centralized constants for the Race Strategy Workbench.

Replaces hardcoded magic numbers scattered across the codebase.
All values here represent sensible defaults that can be overridden
by track-specific configuration or runtime calibration.
"""

# =============================================================================
# Pace & Timing
# =============================================================================

DEFAULT_BASE_PACE_SECONDS: float = 90.0
"""Fallback base lap time when no calibration data is available."""

FRAME_INTERVAL_SECONDS: float = 0.02
"""Animation frame interval (50 FPS)."""

# =============================================================================
# Pit Strategy
# =============================================================================

DEFAULT_PIT_LOSS_SECONDS: float = 22.0
"""Default time lost during a pit stop (pit lane transit + stationary)."""

DEFAULT_TOTAL_LAPS: int = 57
"""Default race length when actual data is unavailable."""

# =============================================================================
# Degradation Models
# =============================================================================

DEFAULT_FORGETTING_FACTOR: float = 0.95
"""RLS model forgetting factor for tyre degradation tracking."""

RLS_INITIAL_COVARIANCE: float = 1000.0
"""Initial covariance for Recursive Least Squares model."""

# =============================================================================
# API & Caching
# =============================================================================

DEFAULT_CACHE_TTL_SECONDS: int = 3600
"""Default cache time-to-live for API responses."""

DEFAULT_RATE_LIMIT_REQUESTS: int = 100
"""Default rate limit: max requests per window."""

# =============================================================================
# Physics
# =============================================================================

GAP_INTERPOLATION_FACTOR: float = 1.0
"""Seconds per position gap when time data is unavailable."""

LOW_CONFIDENCE_PHYSICS_ONLY: float = 0.3
"""Model confidence when using physics-only predictions (no live data)."""

MEDIUM_CONFIDENCE_DEFAULT: float = 0.5
"""Default model confidence for initial predictions."""
