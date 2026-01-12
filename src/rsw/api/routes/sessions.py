"""
Sessions API Routes.

Endpoints for browsing and managing F1 session data.

Endpoints:
    GET /sessions - List available sessions
    GET /sessions/{session_key} - Get session details
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Query

from rsw.logging_config import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


# Module-level reference to app state
_app_state: Any = None


def init_session_routes(app_state: Any) -> None:
    """
    Initialize session routes with application state.

    Args:
        app_state: Application state container with client
    """
    global _app_state
    _app_state = app_state


@router.get("")
async def list_sessions(
    year: int | None = Query(None, ge=2018, le=2030, description="Filter by season year"),
    country: str | None = Query(None, description="Filter by country name"),
) -> list[dict[str, Any]]:
    """
    List available F1 sessions.

    Args:
        year: Optional year filter (2018-2030)
        country: Optional country filter

    Returns:
        List of session objects with metadata
    """
    if _app_state is None:
        return []

    sessions = await _app_state.client.get_sessions(year=year, country=country)

    # Calculate round numbers for championship events
    round_map = _calculate_round_numbers(sessions)

    return [
        {
            "session_key": s.session_key,
            "session_name": s.session_name,
            "session_type": s.session_type,
            "circuit": s.circuit_short_name,
            "country": s.country_name,
            "date": s.date_start.isoformat(),
            "year": s.year,
            "round_number": round_map.get(s.meeting_key, 0),
        }
        for s in sessions
    ]


def _calculate_round_numbers(sessions: list[Any]) -> dict[int, int]:
    """
    Calculate round numbers based on race meetings.

    Excludes testing sessions and cancelled events.

    Args:
        sessions: List of session objects

    Returns:
        Dict mapping meeting_key to round_number
    """
    # Group by meeting
    meetings: dict[int, list[Any]] = {}
    for s in sessions:
        if s.meeting_key not in meetings:
            meetings[s.meeting_key] = []
        meetings[s.meeting_key].append(s)

    # Identify valid race meetings
    race_meetings: list[tuple[int, Any]] = []

    # Cancelled meeting keys (e.g., Imola 2023 cancelled due to floods)
    CANCELLED_MEETINGS = {1209}

    for m_key, m_sessions in meetings.items():
        has_race = any(s.session_type == "Race" or "Race" in s.session_name for s in m_sessions)
        is_testing = any("Testing" in s.session_name for s in m_sessions)
        is_cancelled = m_key in CANCELLED_MEETINGS

        if has_race and not is_testing and not is_cancelled:
            start_date = min(s.date_start for s in m_sessions)
            race_meetings.append((m_key, start_date))

    # Sort by date and assign round numbers
    race_meetings.sort(key=lambda x: x[1])

    return {key: i + 1 for i, (key, _) in enumerate(race_meetings)}
