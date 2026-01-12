"""
Shared utilities and helpers.

DRY: Common functionality extracted to single location.
"""

from datetime import datetime
from typing import Any, TypeVar

T = TypeVar("T")


# ============================================================================
# Response Formatting (DRY: Single place for API responses)
# ============================================================================


def format_success(data: Any, message: str | None = None) -> dict:
    """Format successful API response."""
    response = {"success": True, "data": data}
    if message:
        response["message"] = message
    return response


def format_error(code: str, message: str, details: dict | None = None) -> dict:
    """Format error API response."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }


def format_paginated(
    items: list[Any],
    total: int,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Format paginated API response."""
    return {
        "success": True,
        "data": items,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


# ============================================================================
# Time Formatting (DRY: Consistent time formatting)
# ============================================================================


def format_lap_time(seconds: float | None) -> str:
    """Format lap time as M:SS.sss"""
    if seconds is None:
        return "--:--.---"

    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:06.3f}"


def format_gap(gap: float | None) -> str:
    """Format gap between cars."""
    if gap is None:
        return "-"
    if gap == 0:
        return "LEADER"
    if gap > 60:
        laps = int(gap // 60)
        return f"+{laps} LAP{'S' if laps > 1 else ''}"
    return f"+{gap:.3f}"


def format_iso_datetime(dt: datetime | None) -> str | None:
    """Format datetime as ISO string."""
    return dt.isoformat() if dt else None


# ============================================================================
# Validation Helpers (DRY: Reusable validation)
# ============================================================================


def validate_range(
    value: float,
    min_val: float,
    max_val: float,
    name: str,
) -> None:
    """
    Validate that value is within range.

    Raises:
        ValueError: If value is out of range
    """
    if not min_val <= value <= max_val:
        raise ValueError(f"{name} must be between {min_val} and {max_val}, got {value}")


def validate_positive(value: float, name: str) -> None:
    """
    Validate that value is positive.

    Raises:
        ValueError: If value is not positive
    """
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def validate_not_empty(value: str | list | dict, name: str) -> None:
    """
    Validate that value is not empty.

    Raises:
        ValueError: If value is empty
    """
    if not value:
        raise ValueError(f"{name} cannot be empty")


# ============================================================================
# Collection Helpers (DRY: Common collection operations)
# ============================================================================


def find_by_key(items: list[T], key: str, value: Any) -> T | None:
    """Find first item in list where item[key] == value."""
    return next((item for item in items if getattr(item, key, None) == value), None)


def group_by(items: list[T], key: str) -> dict[Any, list[T]]:
    """Group items by a key attribute."""
    result: dict[Any, list[T]] = {}
    for item in items:
        k = getattr(item, key, None)
        if k not in result:
            result[k] = []
        result[k].append(item)
    return result


def safe_get(data: dict, *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary value."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data


# ============================================================================
# Math Helpers (DRY: Common calculations)
# ============================================================================


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))


def moving_average(values: list[float], window: int) -> list[float]:
    """Calculate moving average."""
    if len(values) < window:
        return values

    result = []
    for i in range(len(values) - window + 1):
        avg = sum(values[i : i + window]) / window
        result.append(avg)
    return result
