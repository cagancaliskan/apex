"""
Main FastAPI server for the Race Strategy Workbench.

This server provides:
- REST API for session selection and data retrieval
- WebSocket endpoint for real-time state updates
- Background polling loop for fetching updates from OpenF1
"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from rsw.config import load_app_config, load_tracks_config
from rsw.ingest import OpenF1Client
from rsw.state import RaceStateStore, RaceState
from rsw.models.degradation import ModelManager
from rsw.api.routes.health import router as health_router


# ============================================================================
# Application State
# ============================================================================

class AppState:
    """Application-wide state container."""
    
    def __init__(self):
        self.config = load_app_config()
        self.tracks = load_tracks_config()
        self.store = RaceStateStore()
        self.client = OpenF1Client()
        self.model_manager = ModelManager(forgetting_factor=0.95)  # Phase 2: ML models
        self.active_session_key: int | None = None
        self.polling_task: asyncio.Task | None = None
        self.websocket_clients: list[WebSocket] = []
        self.is_polling = False


app_state = AppState()


# ============================================================================
# WebSocket Connection Manager
# ============================================================================

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message, default=str)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


# ============================================================================
# Polling Loop
# ============================================================================

async def polling_loop(session_key: int, interval: float = 3.0) -> None:
    """
    Background task that simulates live race updates.
    
    For historical data, this pre-fetches ALL data once, then
    replays it lap-by-lap to simulate a live race experience.
    """
    print(f"Starting polling loop for session {session_key}")
    app_state.is_polling = True
    
    try:
        # First, fetch session info
        session = await app_state.client.get_session(session_key)
        if not session:
            print(f"Session {session_key} not found")
            return
        
        # Get track config
        track_id = session.circuit_short_name.lower().replace("-", "_").replace(" ", "_")
        track_config = app_state.tracks.get(track_id)
        
        # Initialize state with session info
        initial_state = RaceState(
            session_key=session_key,
            meeting_key=session.meeting_key,
            session_name=session.session_name,
            session_type=session.session_type,
            track_id=track_id,
            track_name=session.circuit_short_name,
            country=session.country_name,
            total_laps=track_config.laps if track_config else 0,
        )
        await app_state.store.reset(initial_state)
        
        # ================================================================
        # PRE-FETCH ALL DATA FOR THE SESSION (one-time load)
        # ================================================================
        print("Pre-fetching all session data...")
        
        drivers = await app_state.client.get_drivers(session_key)
        all_laps = await app_state.client.get_laps(session_key)
        all_positions = await app_state.client.get_positions(session_key)
        all_intervals = await app_state.client.get_intervals(session_key)
        all_stints = await app_state.client.get_stints(session_key)
        all_pits = await app_state.client.get_pits(session_key)
        all_race_control = await app_state.client.get_race_control(session_key)
        
        print(f"Loaded: {len(all_laps)} laps, {len(drivers)} drivers, {len(all_stints)} stints")
        
        if not all_laps:
            print("No lap data found")
            return
        
        max_lap = max(lap.lap_number for lap in all_laps)
        print(f"Race has {max_lap} laps - starting simulation...")
        
        # Apply driver info first (static data)
        from rsw.ingest.base import UpdateBatch
        driver_batch = UpdateBatch(
            session_key=session_key,
            timestamp=datetime.now(timezone.utc),
            drivers=drivers,
        )
        await app_state.store.apply(driver_batch)
        
        # Broadcast initial state with drivers
        await manager.broadcast({
            "type": "state_update",
            "data": app_state.store.to_dict(),
        })
        
        # ================================================================
        # REPLAY LAP BY LAP
        # ================================================================
        for current_lap in range(1, max_lap + 1):
            if not app_state.is_polling:
                break
            
            # Filter data for laps UP TO and including current_lap
            laps_up_to_now = [l for l in all_laps if l.lap_number <= current_lap]
            
            # For positions/intervals, we simulate by taking latest available
            # but we'll update state progressively
            
            # Get laps specifically for this lap (for the update)
            laps_this_lap = [l for l in all_laps if l.lap_number == current_lap]
            
            # Get stints active at this lap
            stints_this_lap = [
                s for s in all_stints 
                if s.lap_start <= current_lap and (s.lap_end is None or s.lap_end >= current_lap)
            ]
            
            # Get pits that happened on this lap
            pits_this_lap = [p for p in all_pits if p.lap_number == current_lap]
            
            # Get race control messages up to this lap
            rc_this_lap = [r for r in all_race_control if r.lap_number and r.lap_number <= current_lap]
            
            # Build update batch for this lap
            lap_batch = UpdateBatch(
                session_key=session_key,
                timestamp=datetime.now(timezone.utc),
                current_lap=current_lap,
                laps=laps_this_lap,
                stints=stints_this_lap,
                pits=pits_this_lap,
                race_control=rc_this_lap[-5:] if rc_this_lap else None,  # Last 5 messages
            )
            
            # Apply update
            await app_state.store.apply(lap_batch)
            
            # Calculate positions based on lap times (simple simulation)
            # In reality, positions come from the API, but for replay we derive them
            state = app_state.store.get()
            sorted_drivers = sorted(
                state.drivers.values(),
                key=lambda d: (
                    -d.current_lap,  # More laps = better
                    d.best_lap_time if d.best_lap_time else float('inf')  # Faster = better
                )
            )
            
            # Update positions
            driver_updates = {}
            for pos, driver in enumerate(sorted_drivers, 1):
                updated = driver.model_copy(update={
                    "position": pos,
                    "gap_to_leader": (pos - 1) * 1.5 if pos > 1 else 0,  # Simulated gap
                    "gap_to_ahead": 1.5 if pos > 1 else None,
                })
                driver_updates[driver.driver_number] = updated
            
            # ================================================================
            # UPDATE DEGRADATION MODELS (Phase 2)
            # ================================================================
            for lap in laps_this_lap:
                driver_num = lap.driver_number
                driver = driver_updates.get(driver_num)
                if driver and lap.lap_duration and lap.lap_duration > 0:
                    # Get stint info for this driver
                    stint = next(
                        (s for s in stints_this_lap if s.driver_number == driver_num),
                        None
                    )
                    stint_num = stint.stint_number if stint else driver.stint_number
                    compound = stint.compound if stint else driver.compound or "MEDIUM"
                    lap_in_stint = driver.lap_in_stint if driver.lap_in_stint > 0 else 1
                    
                    # Check if this is a valid lap for model training
                    is_valid = (
                        not driver.is_pit_out_lap
                        and not state.safety_car
                        and not state.virtual_safety_car
                    )
                    
                    # Update model
                    app_state.model_manager.update_driver(
                        driver_number=driver_num,
                        lap_in_stint=lap_in_stint,
                        lap_time=lap.lap_duration,
                        stint_number=stint_num,
                        compound=compound,
                        is_valid=is_valid,
                    )
            
            # Apply model predictions to driver state
            predictions = app_state.model_manager.get_all_predictions(k=5)
            for driver_num, pred in predictions.items():
                if driver_num in driver_updates:
                    driver_updates[driver_num] = driver_updates[driver_num].model_copy(
                        update={
                            "deg_slope": round(pred.deg_slope, 4),
                            "cliff_risk": round(pred.cliff_risk, 2),
                            "predicted_pace": [round(p, 3) for p in pred.predicted_next_k],
                            "model_confidence": round(pred.model_confidence, 2),
                        }
                    )
            
            # ================================================================
            # STRATEGY CALCULATIONS (Phase 3)
            # ================================================================
            from rsw.strategy.decision import evaluate_strategy
            
            # Get pit loss from track config
            pit_loss = track_config.pit_loss_seconds if track_config else 22.0
            
            for driver_num, driver in driver_updates.items():
                if driver.current_lap > 0:
                    # Get competitor info for undercut/overcut detection
                    ahead_deg = 0.05
                    behind_deg = 0.05
                    
                    # Find drivers ahead and behind
                    for other in driver_updates.values():
                        if other.position == driver.position - 1:
                            ahead_deg = other.deg_slope
                        elif other.position == driver.position + 1:
                            behind_deg = other.deg_slope
                    
                    rec = evaluate_strategy(
                        driver_number=driver_num,
                        current_lap=current_lap,
                        total_laps=max_lap,
                        current_position=driver.position,
                        deg_slope=driver.deg_slope,
                        cliff_risk=driver.cliff_risk,
                        current_pace=driver.last_lap_time or 90.0,
                        tyre_age=driver.tyre_age,
                        compound=driver.compound or "MEDIUM",
                        pit_loss=pit_loss,
                        gap_to_ahead=driver.gap_to_ahead,
                        gap_to_behind=None,
                        ahead_deg=ahead_deg,
                        behind_deg=behind_deg,
                        safety_car=state.safety_car,
                    )
                    
                    # Update driver with strategy info
                    driver_updates[driver_num] = driver_updates[driver_num].model_copy(
                        update={
                            "pit_window_min": rec.pit_window.min_lap if rec.pit_window else 0,
                            "pit_window_max": rec.pit_window.max_lap if rec.pit_window else 0,
                            "pit_window_ideal": rec.pit_window.ideal_lap if rec.pit_window else 0,
                            "pit_recommendation": rec.recommendation.value,
                            "pit_confidence": round(rec.confidence, 2),
                            "pit_reason": rec.reason,
                            "undercut_threat": rec.undercut_threat,
                            "overcut_opportunity": rec.overcut_opportunity,
                        }
                    )
            
            new_state = state.model_copy(update={
                "drivers": driver_updates,
                "current_lap": current_lap,
            })
            await app_state.store.reset(new_state)
            
            # Broadcast update
            await manager.broadcast({
                "type": "state_update",
                "data": app_state.store.to_dict(),
            })
            
            print(f"Lap {current_lap}/{max_lap} - {len(laps_this_lap)} driver laps")
            
            # Wait before next lap
            await asyncio.sleep(interval)
        
        print("Race simulation complete!")
    
    except asyncio.CancelledError:
        print("Polling loop cancelled")
    except Exception as e:
        print(f"Polling loop error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        app_state.is_polling = False
        print("Polling loop stopped")


# ============================================================================
# FastAPI App
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("🏎️  Race Strategy Workbench starting...")
    yield
    # Shutdown
    print("🏁 Race Strategy Workbench shutting down...")
    if app_state.polling_task:
        app_state.polling_task.cancel()
    await app_state.client.close()


app = FastAPI(
    title="Race Strategy Workbench",
    description="Real-time F1 race analytics and pit strategy optimization",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register health check routes
app.include_router(health_router, tags=["health"])


# ============================================================================
# REST Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Race Strategy Workbench API", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/sessions")
async def get_sessions(year: int | None = None, country: str | None = None):
    """Get available sessions."""
    sessions = await app_state.client.get_sessions(year=year, country=country)
    return [
        {
            "session_key": s.session_key,
            "session_name": s.session_name,
            "session_type": s.session_type,
            "circuit": s.circuit_short_name,
            "country": s.country_name,
            "date": s.date_start.isoformat(),
            "year": s.year,
        }
        for s in sessions
    ]


@app.get("/api/sessions/{session_key}")
async def get_session(session_key: int):
    """Get a specific session."""
    session = await app_state.client.get_session(session_key)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_key": session.session_key,
        "session_name": session.session_name,
        "session_type": session.session_type,
        "circuit": session.circuit_short_name,
        "country": session.country_name,
        "date_start": session.date_start.isoformat(),
        "date_end": session.date_end.isoformat() if session.date_end else None,
        "year": session.year,
    }


@app.post("/api/sessions/{session_key}/start")
async def start_session(session_key: int, interval: float = 3.0):
    """Start polling for a session."""
    # Stop any existing polling
    if app_state.polling_task and not app_state.polling_task.done():
        app_state.polling_task.cancel()
        try:
            await app_state.polling_task
        except asyncio.CancelledError:
            pass
    
    # Start new polling task
    app_state.active_session_key = session_key
    app_state.polling_task = asyncio.create_task(
        polling_loop(session_key, interval=interval)
    )
    
    return {"status": "started", "session_key": session_key}


@app.post("/api/sessions/stop")
async def stop_session():
    """Stop polling for the current session."""
    app_state.is_polling = False
    if app_state.polling_task:
        app_state.polling_task.cancel()
        try:
            await app_state.polling_task
        except asyncio.CancelledError:
            pass
        app_state.polling_task = None
    
    return {"status": "stopped"}


@app.get("/api/state")
async def get_state():
    """Get current race state."""
    return app_state.store.to_dict()


@app.get("/api/tracks")
async def get_tracks():
    """Get track configurations."""
    return {
        track_id: {
            "name": track.name,
            "country": track.country,
            "pit_loss": track.pit_loss_seconds,
            "sc_probability": track.sc_base_rate,
            "laps": track.laps,
        }
        for track_id, track in app_state.tracks.items()
    }


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time state updates."""
    await manager.connect(websocket)
    
    try:
        # Send current state immediately
        await websocket.send_text(json.dumps({
            "type": "state_update",
            "data": app_state.store.to_dict(),
        }, default=str))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle client messages
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                
                elif message.get("type") == "start_session":
                    session_key = message.get("session_key")
                    interval = message.get("interval", 3.0)
                    if session_key:
                        # Start polling (reuse the REST endpoint logic)
                        if app_state.polling_task and not app_state.polling_task.done():
                            app_state.polling_task.cancel()
                            try:
                                await app_state.polling_task
                            except asyncio.CancelledError:
                                pass
                        
                        app_state.active_session_key = session_key
                        app_state.polling_task = asyncio.create_task(
                            polling_loop(session_key, interval=interval)
                        )
                        await websocket.send_text(json.dumps({
                            "type": "session_started",
                            "session_key": session_key,
                        }))
                
                elif message.get("type") == "stop_session":
                    app_state.is_polling = False
                    if app_state.polling_task:
                        app_state.polling_task.cancel()
                    await websocket.send_text(json.dumps({"type": "session_stopped"}))
            
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                pass
    
    finally:
        manager.disconnect(websocket)


# ============================================================================
# Replay Endpoints (Phase 4)
# ============================================================================

@app.get("/api/replay/sessions")
async def list_replay_sessions():
    """List cached sessions available for replay."""
    from rsw.backtest.replay import ReplaySession
    from pathlib import Path
    
    data_dir = Path(__file__).parent.parent.parent / "data" / "sessions"
    sessions = ReplaySession.list_cached_sessions(data_dir)
    
    return {"sessions": sessions}


@app.post("/api/replay/{session_key}/start")
async def start_replay(session_key: int, speed: float = 1.0):
    """Start replay from cached session."""
    from rsw.backtest.replay import ReplaySession
    from pathlib import Path
    
    data_dir = Path(__file__).parent.parent.parent / "data" / "sessions"
    session_file = data_dir / f"{session_key}.json"
    
    if not session_file.exists():
        raise HTTPException(404, f"Session {session_key} not found in cache")
    
    # Load session and start replay
    replay = ReplaySession.load(session_file)
    replay.set_speed(speed)
    
    # Store replay in app state
    app_state.active_replay = replay
    
    # Set up callback to broadcast state
    async def broadcast_lap(lap: int, state):
        await manager.broadcast({
            "type": "replay_update",
            "lap": lap,
            "data": {
                "session_key": state.session_key,
                "session_name": state.session_name,
                "track_name": state.track_name,
                "country": state.country,
                "current_lap": state.current_lap,
                "total_laps": state.total_laps,
                "playback_state": state.playback_state.value,
                "speed": state.playback_speed,
            }
        })
    
    replay.play()
    
    return {
        "status": "started",
        "session_key": session_key,
        "total_laps": replay.total_laps,
    }


@app.post("/api/replay/control")
async def control_replay(action: str, value: float = None):
    """Control replay playback."""
    replay = getattr(app_state, 'active_replay', None)
    if not replay:
        raise HTTPException(400, "No active replay")
    
    if action == "play":
        replay.play()
    elif action == "pause":
        replay.pause()
    elif action == "stop":
        replay.stop()
    elif action == "seek" and value is not None:
        replay.seek(int(value))
    elif action == "speed" and value is not None:
        replay.set_speed(value)
    else:
        raise HTTPException(400, f"Unknown action: {action}")
    
    state = replay.get_state()
    return {
        "status": state.playback_state.value,
        "current_lap": state.current_lap,
        "speed": state.playback_speed,
    }


# ============================================================================
# Run Server
# ============================================================================

def main():
    """Run the server."""
    import uvicorn
    
    config = load_app_config()
    uvicorn.run(
        "rsw.main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug,
    )


if __name__ == "__main__":
    main()
