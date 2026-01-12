"""
Session Service - handles session lifecycle.

Single Responsibility: Manages session-related business logic only.
"""

from dataclasses import dataclass
from typing import Any

from rsw.exceptions import SessionNotFoundError
from rsw.interfaces import IDataProvider, IService, IStateStore
from rsw.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SessionService(IService):
    """
    Service for managing race sessions.

    Follows:
    - SRP: Only handles session operations
    - DIP: Depends on abstractions (IDataProvider, IStateStore)
    """

    data_provider: IDataProvider
    state_store: IStateStore

    async def initialize(self) -> None:
        """Initialize the service."""
        logger.info("session_service_initialized")

    async def shutdown(self) -> None:
        """Cleanup resources."""
        await self.data_provider.close()
        logger.info("session_service_shutdown")

    async def get_available_sessions(self, year: int) -> list[dict]:
        """
        Get available sessions for a year.

        Args:
            year: The year to query

        Returns:
            List of session dictionaries
        """
        logger.debug("fetching_sessions", year=year)
        sessions = await self.data_provider.get_sessions(year)

        return [self._format_session(s) for s in sessions]

    async def get_session_details(self, session_key: int) -> dict:
        """
        Get detailed session information.

        Args:
            session_key: Session identifier

        Returns:
            Session details

        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        sessions = await self.data_provider.get_sessions(year=2023)  # TODO: extract year
        session = next((s for s in sessions if s.session_key == session_key), None)

        if not session:
            raise SessionNotFoundError(session_key)

        return self._format_session(session)

    async def start_tracking(self, session_key: int) -> None:
        """
        Start tracking a session.

        Args:
            session_key: Session to track
        """
        logger.info("tracking_started", session_key=session_key)
        # Initialize state store with session

    async def stop_tracking(self) -> None:
        """Stop tracking the current session."""
        logger.info("tracking_stopped")

    def _format_session(self, session: Any) -> dict:
        """
        Format session for API response.

        DRY: Single place for session formatting.
        """
        return {
            "session_key": session.session_key,
            "session_name": session.session_name,
            "session_type": session.session_type,
            "circuit": session.circuit_short_name,
            "country": session.country_name,
            "date_start": session.date_start.isoformat() if session.date_start else None,
            "year": session.year,
        }
