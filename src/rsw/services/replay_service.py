"""
Replay Service - handles session replay functionality.

Single Responsibility: Only manages replay playback.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any

from rsw.interfaces import IService
from rsw.logging_config import get_logger
from rsw.exceptions import CachedSessionNotFoundError, NoActiveReplayError
from rsw.backtest.replay import ReplaySession, ReplayState, PlaybackState

logger = get_logger(__name__)


class ReplayService(IService):
    """
    Service for managing replay playback.
    
    Follows:
    - SRP: Only handles replay operations
    - Encapsulation: Hides ReplaySession internals
    """
    
    def __init__(self, sessions_dir: Path | str = "data/sessions") -> None:
        """
        Initialize replay service.
        
        Args:
            sessions_dir: Directory containing cached sessions
        """
        self.sessions_dir = Path(sessions_dir)
        self._active_session: ReplaySession | None = None
        self._on_lap_callback: Callable[[int, ReplayState], None] | None = None
    
    async def initialize(self) -> None:
        """Initialize the service."""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        logger.info("replay_service_initialized", sessions_dir=str(self.sessions_dir))
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        if self._active_session:
            self._active_session.stop()
        logger.info("replay_service_shutdown")
    
    def list_available_sessions(self) -> list[dict]:
        """
        List all cached sessions available for replay.
        
        Returns:
            List of session metadata dictionaries
        """
        return ReplaySession.list_cached_sessions(self.sessions_dir)
    
    def load_session(self, session_key: int) -> ReplaySession:
        """
        Load a cached session for replay.
        
        Args:
            session_key: Session identifier
            
        Returns:
            Loaded ReplaySession
            
        Raises:
            CachedSessionNotFoundError: If session file doesn't exist
        """
        session_file = self.sessions_dir / f"{session_key}.json"
        
        if not session_file.exists():
            raise CachedSessionNotFoundError(session_key, str(session_file))
        
        session = ReplaySession.load(session_file)
        self._active_session = session
        
        # Set up callback if registered
        if self._on_lap_callback:
            session.on_lap_complete = self._on_lap_callback
        
        logger.info("session_loaded", session_key=session_key, total_laps=session.total_laps)
        return session
    
    def start_replay(self, speed: float = 1.0) -> None:
        """
        Start or resume replay.
        
        Args:
            speed: Playback speed multiplier
            
        Raises:
            NoActiveReplayError: If no session is loaded
        """
        self._ensure_active_session()
        assert self._active_session is not None
        self._active_session.set_speed(speed)
        self._active_session.play()
        
        logger.info("replay_started", speed=speed)
    
    def pause_replay(self) -> None:
        """Pause replay."""
        self._ensure_active_session()
        assert self._active_session is not None
        self._active_session.pause()
        logger.info("replay_paused")
    
    def stop_replay(self) -> None:
        """Stop replay and reset."""
        self._ensure_active_session()
        assert self._active_session is not None
        self._active_session.stop()
        logger.info("replay_stopped")
    
    def seek_to_lap(self, lap: int) -> None:
        """
        Seek to a specific lap.
        
        Args:
            lap: Lap number to seek to
        """
        self._ensure_active_session()
        assert self._active_session is not None
        self._active_session.seek(lap)
        logger.debug("replay_seek", lap=lap)
    
    def set_speed(self, speed: float) -> None:
        """
        Set playback speed.
        
        Args:
            speed: Speed multiplier (0.1 to 10.0)
        """
        self._ensure_active_session()
        assert self._active_session is not None
        self._active_session.set_speed(speed)
    
    def get_state(self) -> dict:
        """
        Get current replay state.
        
        Returns:
            Current state as dictionary
        """
        self._ensure_active_session()
        assert self._active_session is not None
        state = self._active_session.get_state()
        
        return {
            "session_key": state.session_key,
            "session_name": state.session_name,
            "track_name": state.track_name,
            "current_lap": state.current_lap,
            "total_laps": state.total_laps,
            "playback_state": state.playback_state.value,
            "speed": state.playback_speed,
        }
    
    def on_lap_complete(self, callback: Callable[[int, ReplayState], None]) -> None:
        """
        Register a callback for lap completion events.
        
        Args:
            callback: Function to call on each lap
        """
        self._on_lap_callback = callback
        if self._active_session:
            self._active_session.on_lap_complete = callback
    
    def _ensure_active_session(self) -> None:
        """Ensure there's an active session loaded."""
        if not self._active_session:
            raise NoActiveReplayError()
        assert self._active_session is not None
