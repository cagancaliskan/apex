"""
Replay engine for playing back cached sessions.

Supports variable speed playback, seeking, and event callbacks.
"""

import json
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Any
from enum import Enum


class PlaybackState(Enum):
    """Replay playback state."""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    FINISHED = "finished"


@dataclass
class ReplayState:
    """Current state of the replay."""
    session_key: int
    session_name: str
    track_name: str
    country: str
    
    current_lap: int = 0
    total_laps: int = 0
    playback_state: PlaybackState = PlaybackState.STOPPED
    playback_speed: float = 1.0
    
    # Data at current lap
    drivers: list[dict] = field(default_factory=list)
    laps_at_current: list[dict] = field(default_factory=list)
    stints_active: list[dict] = field(default_factory=list)
    pits_at_current: list[dict] = field(default_factory=list)
    messages_at_current: list[dict] = field(default_factory=list)


class ReplaySession:
    """
    Replay engine for cached session data.
    
    Usage:
        session = ReplaySession.load("data/sessions/9158.json")
        session.on_lap_complete = my_callback
        session.play()
        await session.wait_until_complete()
    """
    
    def __init__(self, data: dict):
        """Initialize with session data."""
        self.data = data
        self.session_key = data["session_key"]
        self.session_info = data.get("session_info", {})
        
        # Parse data
        self.drivers = data.get("drivers", [])
        self.laps = data.get("laps", [])
        self.stints = data.get("stints", [])
        self.pits = data.get("pits", [])
        self.race_control = data.get("race_control", [])
        
        # Calculate total laps
        self.total_laps = max((l["lap_number"] for l in self.laps), default=0)
        
        # Playback state
        self._current_lap = 0
        self._state = PlaybackState.STOPPED
        self._speed = 1.0
        self._task: asyncio.Task | None = None
        
        # Callbacks
        self.on_lap_complete: Callable[[int, ReplayState], None] | None = None
        self.on_state_change: Callable[[ReplayState], None] | None = None
    
    @classmethod
    def load(cls, path: str | Path) -> "ReplaySession":
        """Load session from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls(data)
    
    @classmethod
    def list_cached_sessions(cls, data_dir: str | Path = "data/sessions") -> list[dict]:
        """List all cached sessions."""
        data_path = Path(data_dir)
        if not data_path.exists():
            return []
        
        sessions = []
        for file in data_path.glob("*.json"):
            try:
                with open(file) as f:
                    data = json.load(f)
                    sessions.append({
                        "session_key": data.get("session_key"),
                        "session_name": data.get("session_info", {}).get("session_name"),
                        "country": data.get("session_info", {}).get("country_name"),
                        "circuit": data.get("session_info", {}).get("circuit_short_name"),
                        "file": str(file),
                    })
            except Exception:
                pass
        
        return sessions
    
    def get_state(self) -> ReplayState:
        """Get current replay state."""
        return ReplayState(
            session_key=self.session_key,
            session_name=self.session_info.get("session_name", "Unknown"),
            track_name=self.session_info.get("circuit_short_name", "Unknown"),
            country=self.session_info.get("country_name", "Unknown"),
            current_lap=self._current_lap,
            total_laps=self.total_laps,
            playback_state=self._state,
            playback_speed=self._speed,
            drivers=self.drivers,
            laps_at_current=self._get_laps_at_lap(self._current_lap),
            stints_active=self._get_stints_at_lap(self._current_lap),
            pits_at_current=self._get_pits_at_lap(self._current_lap),
            messages_at_current=self._get_messages_at_lap(self._current_lap),
        )
    
    def _get_laps_at_lap(self, lap: int) -> list[dict]:
        """Get all lap records for a specific lap number."""
        return [l for l in self.laps if l["lap_number"] == lap]
    
    def _get_stints_at_lap(self, lap: int) -> list[dict]:
        """Get active stints at a lap."""
        return [
            s for s in self.stints
            if s["lap_start"] <= lap and (s["lap_end"] is None or s["lap_end"] >= lap)
        ]
    
    def _get_pits_at_lap(self, lap: int) -> list[dict]:
        """Get pits that happened on a lap."""
        return [p for p in self.pits if p["lap_number"] == lap]
    
    def _get_messages_at_lap(self, lap: int) -> list[dict]:
        """Get race control messages up to a lap."""
        return [r for r in self.race_control if r.get("lap_number", 0) <= lap][-5:]
    
    def play(self) -> None:
        """Start or resume playback."""
        if self._state == PlaybackState.FINISHED:
            self._current_lap = 0
        
        self._state = PlaybackState.PLAYING
        
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._playback_loop())
        
        self._notify_state_change()
    
    def pause(self) -> None:
        """Pause playback."""
        self._state = PlaybackState.PAUSED
        self._notify_state_change()
    
    def stop(self) -> None:
        """Stop playback and reset."""
        self._state = PlaybackState.STOPPED
        self._current_lap = 0
        
        if self._task:
            self._task.cancel()
            self._task = None
        
        self._notify_state_change()
    
    def seek(self, lap: int) -> None:
        """Seek to a specific lap."""
        self._current_lap = max(0, min(lap, self.total_laps))
        self._notify_state_change()
    
    def set_speed(self, speed: float) -> None:
        """Set playback speed multiplier."""
        self._speed = max(0.05, min(10.0, speed))
        self._notify_state_change()
    
    async def _playback_loop(self) -> None:
        """Main playback loop."""
        while self._current_lap < self.total_laps:
            if self._state != PlaybackState.PLAYING:
                await asyncio.sleep(0.1)
                continue
            
            self._current_lap += 1
            
            # Notify lap completion
            if self.on_lap_complete:
                self.on_lap_complete(self._current_lap, self.get_state())
            
            # Wait based on speed (faster speed = shorter wait)
            delay = 1.0 / self._speed
            await asyncio.sleep(delay)
        
        self._state = PlaybackState.FINISHED
        self._notify_state_change()
    
    def _notify_state_change(self) -> None:
        """Notify state change callback."""
        if self.on_state_change:
            self.on_state_change(self.get_state())
    
    async def wait_until_complete(self) -> None:
        """Wait until replay completes."""
        if self._task:
            await self._task
