"""
In-memory state store with subscription support.

The store holds the canonical race state and notifies subscribers
when it changes, enabling real-time updates to the UI.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Callable
from collections.abc import Awaitable

from ..ingest.base import UpdateBatch
from .schemas import RaceState, DriverState, StateSnapshot
from .reducers import apply_update_batch


# Type for state change callbacks
StateCallback = Callable[[RaceState], Awaitable[None]]


class RaceStateStore:
    """
    In-memory store for race state with reactive updates.
    
    Features:
    - Thread-safe state access
    - Subscription system for real-time updates
    - Snapshot support for persistence
    - History tracking (optional)
    """
    
    def __init__(
        self,
        initial_state: RaceState | None = None,
        track_history: bool = False,
        max_history: int = 100,
    ):
        """
        Initialize the store.
        
        Args:
            initial_state: Optional initial state (creates empty state if None)
            track_history: Whether to track state history
            max_history: Maximum number of historical states to keep
        """
        self._state = initial_state or RaceState(session_key=0)
        self._subscribers: list[StateCallback] = []
        self._lock = asyncio.Lock()
        self._track_history = track_history
        self._max_history = max_history
        self._history: list[RaceState] = []
        self._update_count = 0
    
    @property
    def state(self) -> RaceState:
        """Get current state (read-only property)."""
        return self._state
    
    def get(self) -> RaceState:
        """Get current state."""
        return self._state
    
    async def apply(self, batch: UpdateBatch) -> RaceState:
        """
        Apply an update batch to the state.
        
        This is the main way to update state. It:
        1. Applies the batch using reducers
        2. Saves to history if enabled
        3. Notifies all subscribers
        
        Returns the new state.
        """
        async with self._lock:
            # Save current state to history if tracking
            if self._track_history:
                self._history.append(self._state)
                if len(self._history) > self._max_history:
                    self._history = self._history[-self._max_history:]
            
            # Apply the update
            self._state = apply_update_batch(self._state, batch)
            self._update_count += 1
        
        # Notify subscribers (outside lock to avoid deadlock)
        await self._notify_subscribers()
        
        return self._state
    
    async def reset(self, new_state: RaceState | None = None) -> RaceState:
        """Reset to a new state or empty state."""
        async with self._lock:
            self._state = new_state or RaceState(session_key=0)
            self._history = []
            self._update_count = 0
        
        await self._notify_subscribers()
        return self._state
    
    def subscribe(self, callback: StateCallback) -> Callable[[], None]:
        """
        Subscribe to state changes.
        
        Returns an unsubscribe function.
        """
        self._subscribers.append(callback)
        
        def unsubscribe() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
        
        return unsubscribe
    
    async def _notify_subscribers(self) -> None:
        """Notify all subscribers of state change."""
        for callback in self._subscribers:
            try:
                await callback(self._state)
            except Exception as e:
                print(f"Error notifying subscriber: {e}")
    
    def snapshot(self, snapshot_id: str | None = None) -> StateSnapshot:
        """Create a snapshot of current state."""
        return StateSnapshot(
            state=self._state,
            snapshot_id=snapshot_id or f"snapshot_{self._update_count}",
            created_at=datetime.utcnow(),
        )
    
    def get_history(self) -> list[RaceState]:
        """Get state history (if tracking enabled)."""
        return list(self._history)
    
    def to_json(self) -> str:
        """Serialize current state to JSON."""
        return self._state.model_dump_json()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert current state to a dictionary for JSON APIs."""
        state = self._state
        
        return {
            "session_key": state.session_key,
            "session_name": state.session_name,
            "track_name": state.track_name,
            "country": state.country,
            "current_lap": state.current_lap,
            "total_laps": state.total_laps,
            "timestamp": state.timestamp.isoformat(),
            "flags": state.flags,
            "safety_car": state.safety_car,
            "virtual_safety_car": state.virtual_safety_car,
            "red_flag": state.red_flag,
            "drivers": [
                {
                    "driver_number": d.driver_number,
                    "name_acronym": d.name_acronym,
                    "full_name": d.full_name,
                    "team_name": d.team_name,
                    "team_colour": d.team_colour,
                    "position": d.position,
                    "gap_to_leader": d.gap_to_leader,
                    "gap_to_ahead": d.gap_to_ahead,
                    "current_lap": d.current_lap,
                    "last_lap_time": d.last_lap_time,
                    "best_lap_time": d.best_lap_time,
                    "stint_number": d.stint_number,
                    "compound": d.compound,
                    "lap_in_stint": d.lap_in_stint,
                    "tyre_age": d.tyre_age,
                    "in_pit": d.in_pit,
                    "retired": d.retired,
                    # Phase 2: ML predictions
                    "deg_slope": d.deg_slope,
                    "cliff_risk": d.cliff_risk,
                    "predicted_pace": d.predicted_pace,
                    "model_confidence": d.model_confidence,
                    # Phase 3: Strategy
                    "pit_window_min": d.pit_window_min,
                    "pit_window_max": d.pit_window_max,
                    "pit_window_ideal": d.pit_window_ideal,
                    "pit_recommendation": d.pit_recommendation,
                    "pit_confidence": d.pit_confidence,
                    "pit_reason": d.pit_reason,
                    "undercut_threat": d.undercut_threat,
                    "overcut_opportunity": d.overcut_opportunity,
                }
                for d in state.get_drivers_sorted()
            ],
            "recent_pits": state.recent_pits,
            "recent_messages": state.recent_messages,
        }


# Global store instance (for convenience)
_global_store: RaceStateStore | None = None


def get_store() -> RaceStateStore:
    """Get the global store instance, creating if needed."""
    global _global_store
    if _global_store is None:
        _global_store = RaceStateStore()
    return _global_store


def set_store(store: RaceStateStore) -> None:
    """Set the global store instance."""
    global _global_store
    _global_store = store
