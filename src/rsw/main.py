"""
Race Strategy Workbench - Main FastAPI Application.

This module provides the FastAPI application entry point with:
- REST API endpoints for session and simulation control
- WebSocket endpoint for real-time state updates
- Middleware configuration for CORS and rate limiting

Architecture:
    - Modular route organization (api/routes/)
    - Dependency injection via AppState
    - Structured logging throughout

Example:
    uvicorn rsw.main:app --reload
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from rsw.api.routes.health import router as health_router
from rsw.api.routes.sessions import init_session_routes
from rsw.api.routes.sessions import router as sessions_router
from rsw.api.routes.simulation import init_simulation_routes
from rsw.api.routes.simulation import router as simulation_router
from rsw.api.routes.weather import router as weather_router
from rsw.api.routes.explain_route import init_explain_routes
from rsw.api.routes.explain_route import router as explain_router
from rsw.api.routes.live import init_live_routes
from rsw.api.routes.live import router as live_router
from rsw.api.routes.championship import init_championship_routes
from rsw.api.routes.championship import router as championship_router
from rsw.api.websocket_manager import ConnectionManager
from rsw.config import load_app_config, load_tracks_config
from rsw.ingest import OpenF1Client
from rsw.ingest.weather_client import WeatherClient
from rsw.logging_config import get_logger
from rsw.middleware.rate_limit import RateLimitMiddleware
from rsw.models.degradation import ModelManager
from rsw.services.live_race_service import LiveRaceService
from rsw.services.simulation_service import SimulationService, sanitize_for_json
from rsw.state import RaceStateStore

logger = get_logger(__name__)


# =============================================================================
# Application State
# =============================================================================


class AppState:
    """
    Application-wide state container.

    Holds shared resources including configuration, data clients,
    and the simulation service.

    Attributes:
        store: Race state store for current session
        client: OpenF1 API client
        simulation_service: Race simulation engine
        speed_multiplier: Current playback speed
    """

    def __init__(self) -> None:
        self.config = load_app_config()
        self.tracks = load_tracks_config()
        self.store = RaceStateStore()
        self.client = OpenF1Client()
        self.model_manager = ModelManager(forgetting_factor=0.95)
        self.weather_client = WeatherClient()
        self.active_session_key: int | None = None
        self.active_replay: Any = None
        self.speed_multiplier: float = 1.0
        self.simulation_service: SimulationService | None = None
        self.live_service: LiveRaceService | None = None
        self.all_driver_telemetry: dict[str, Any] = {}


# =============================================================================
# Application Lifecycle
# =============================================================================


# Fallback instances for test environments where lifespan hasn't run
_fallback_app_state: AppState | None = None
_fallback_connection_manager: ConnectionManager | None = None


def _get_app_state() -> AppState:
    """Get the application state from the FastAPI app. Use during request handling."""
    global _fallback_app_state
    try:
        return app.state.rsw
    except AttributeError:
        # Lifespan hasn't run (e.g. in tests) — use fallback
        if _fallback_app_state is None:
            _fallback_app_state = AppState()
        return _fallback_app_state


def _get_connection_manager() -> ConnectionManager:
    """Get the connection manager from the FastAPI app."""
    global _fallback_connection_manager
    try:
        return app.state.connection_manager
    except AttributeError:
        if _fallback_connection_manager is None:
            _fallback_connection_manager = ConnectionManager()
        return _fallback_connection_manager


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Application lifecycle manager.

    Handles startup initialization and graceful shutdown.
    """
    logger.info("application_starting", version="2.1.0")

    # Initialize shared state within lifespan (not at module level)
    app_state = AppState()
    conn_manager = ConnectionManager()

    application.state.rsw = app_state
    application.state.connection_manager = conn_manager

    # Initialize simulation service
    app_state.simulation_service = SimulationService(app_state, conn_manager)

    # Initialize live race service
    app_state.live_service = LiveRaceService(
        app_state, conn_manager, app_state.client, app_state.weather_client
    )

    # Initialize route modules with app state
    init_simulation_routes(app_state)
    init_session_routes(app_state)
    init_explain_routes(app_state)
    init_live_routes(app_state)
    init_championship_routes(app_state)

    logger.info("application_ready")

    yield

    # Shutdown
    logger.info("application_stopping")
    if app_state.live_service:
        await app_state.live_service.stop()
    if app_state.simulation_service:
        await app_state.simulation_service.stop()
    logger.info("application_stopped")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Race Strategy Workbench API",
    version="2.1.0",
    description="Real-time F1 race simulation and strategy analysis",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
_raw_cors = os.getenv("RSW_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
_environment = os.getenv("RSW_ENVIRONMENT", "development")

# Validate CORS origins: reject wildcards in production
CORS_ORIGINS = []
for origin in _raw_cors:
    origin = origin.strip()
    if _environment == "production" and origin == "*":
        logger.warning("cors_wildcard_rejected", detail="Wildcard CORS origin rejected in production")
        continue
    if origin:
        CORS_ORIGINS.append(origin)

if not CORS_ORIGINS:
    CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Correlation ID middleware for request tracing
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Adds a unique request ID to every request for log correlation."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        structlog.contextvars.clear_contextvars()
        return response


app.add_middleware(CorrelationIdMiddleware)

# Rate Limiting (disabled in development by default)
if os.getenv("RSW_RATE_LIMIT_ENABLED", "false").lower() == "true":
    app.add_middleware(RateLimitMiddleware)


# =============================================================================
# Include Routers
# =============================================================================

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(simulation_router, prefix="/api", tags=["simulation"])
app.include_router(sessions_router, prefix="/api", tags=["sessions"])
app.include_router(weather_router, prefix="/api", tags=["weather"])
app.include_router(explain_router, prefix="/api", tags=["explainability"])
app.include_router(live_router, prefix="/api", tags=["live"])
app.include_router(championship_router, prefix="/api", tags=["championship"])


# =============================================================================
# Core Endpoints
# =============================================================================


@app.get("/", tags=["info"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "service": "Race Strategy Workbench API",
        "version": "1.1.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Health check endpoint for monitoring."""
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    """Liveness probe for container orchestration."""
    return {"status": "alive"}


@app.get("/version", tags=["info"])
async def version() -> dict[str, Any]:
    """Version and environment information."""
    return {
        "version": "1.1.0",
        "environment": os.getenv("RSW_ENVIRONMENT", "development"),
        "python": "3.11+",
    }


# =============================================================================
# State Endpoints
# =============================================================================


@app.get("/api/state", tags=["state"])
async def get_current_state() -> dict[str, Any]:
    """Get current race state snapshot."""
    return _get_app_state().store.to_dict()


# =============================================================================
# Replay Endpoints
# =============================================================================


@app.post("/api/replay/control", tags=["replay"])
async def replay_control(action: str, value: float | None = None) -> dict[str, Any]:
    """
    Control replay playback.

    Args:
        action: One of 'play', 'pause', 'stop', 'seek'
        value: Optional value for seek action (target lap or timestamp)
    """
    state = _get_app_state()
    if state.active_replay is None:
        raise HTTPException(status_code=400, detail="No active replay session")

    actions = {"play", "pause", "stop", "seek"}
    if action not in actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of: {actions}")

    if action == "seek":
        if value is None:
            raise HTTPException(status_code=400, detail="seek action requires a value parameter")
        if hasattr(state.active_replay, "seek"):
            state.active_replay.seek(value)
        else:
            raise HTTPException(status_code=501, detail="Replay session does not support seeking")
    else:
        getattr(state.active_replay, action)()

    return {"status": "ok", "action": action, "value": value}


@app.get("/api/replay/sessions", tags=["replay"])
async def list_replay_sessions() -> dict[str, list[dict[str, Any]]]:
    """List cached sessions available for replay."""
    from pathlib import Path

    from rsw.backtest.replay import ReplaySession

    data_dir = Path(__file__).parent.parent.parent / "data" / "sessions"
    sessions = ReplaySession.list_cached_sessions(data_dir)
    return {"sessions": sessions}


@app.post("/api/replay/{session_key}/start", tags=["replay"])
async def start_replay(session_key: int, speed: float = 1.0) -> dict[str, Any]:
    """Start replay from cached session."""
    from pathlib import Path

    from rsw.backtest.replay import ReplaySession

    data_dir = Path(__file__).parent.parent.parent / "data" / "sessions"
    session_file = data_dir / f"{session_key}.json"

    if not session_file.exists():
        raise HTTPException(404, f"Session {session_key} not found in cache")

    replay = ReplaySession.load(session_file)
    replay.set_speed(speed)
    _get_app_state().active_replay = replay
    replay.play()

    # Include replay metadata for frontend
    metadata: dict[str, Any] = {
        "status": "started",
        "session_key": session_key,
        "speed": speed,
    }
    if hasattr(replay, "total_laps"):
        metadata["total_laps"] = replay.total_laps
    if hasattr(replay, "drivers"):
        metadata["driver_count"] = len(replay.drivers)
    if hasattr(replay, "track_name"):
        metadata["track_name"] = replay.track_name
    if hasattr(replay, "session_name"):
        metadata["session_name"] = replay.session_name

    return metadata


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time state updates.

    Protocol:
        - Server sends 'state_update' messages with race state
        - Client can send 'ping' for keepalive
        - Client can send 'start_session' to begin simulation
    """
    # Optional token-based authentication for WebSocket
    ws_auth_required = os.getenv("RSW_WS_AUTH_REQUIRED", "false").lower() == "true"
    if ws_auth_required:
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=4001, reason="Authentication required")
            return
        try:
            from rsw.middleware.auth import decode_token
            decode_token(token)
        except Exception as e:
            logger.debug("ws_auth_failed", error=str(e))
            await websocket.close(code=4003, reason="Invalid token")
            return

    conn_mgr = _get_connection_manager()
    state = _get_app_state()
    await conn_mgr.connect(websocket)

    # Register immediately after connect so disconnect() in finally always cleans up
    conn_mgr.register(websocket)

    try:
        # Send initial state
        safe_data = sanitize_for_json(state.store.to_dict())
        await websocket.send_text(
            json.dumps(
                {
                    "type": "state_update",
                    "data": safe_data,
                },
                default=str,
            )
        )

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await _handle_ws_message(websocket, message)
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning("ws_invalid_json")
            except Exception as e:
                logger.exception("ws_error", error=str(e))
    finally:
        conn_mgr.disconnect(websocket)


async def _handle_ws_message(websocket: WebSocket, message: dict[str, Any]) -> None:
    """Handle incoming WebSocket messages."""
    state = _get_app_state()
    msg_type = message.get("type")

    if msg_type == "ping":
        await websocket.send_text(json.dumps({"type": "pong"}))

    elif msg_type == "start_session":
        year = message.get("year", 2023)
        round_num = message.get("round_num", 1)

        if state.simulation_service:
            await state.simulation_service.start(year, round_num)
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "session_started",
                        "year": year,
                        "round": round_num,
                    }
                )
            )

    elif msg_type == "stop_session":
        if state.simulation_service:
            await state.simulation_service.stop()
        await websocket.send_text(json.dumps({"type": "session_stopped"}))

    elif msg_type == "set_speed":
        speed = message.get("speed", 1.0)
        state.speed_multiplier = speed
        await websocket.send_text(json.dumps({"type": "speed_set", "speed": speed}))

    elif msg_type == "start_live":
        session_key = message.get("session_key")
        if state.live_service:
            # Mutual exclusion: stop simulation if running
            if state.simulation_service and state.simulation_service.is_running:
                await state.simulation_service.stop()
            if session_key:
                await state.live_service.start(session_key)
            else:
                sessions = await state.live_service.get_active_sessions()
                if sessions:
                    race_sessions = [s for s in sessions if s["session_type"] == "Race"]
                    target = race_sessions[-1] if race_sessions else sessions[-1]
                    await state.live_service.start(target["session_key"])
            await websocket.send_text(json.dumps({"type": "live_started"}))

    elif msg_type == "stop_live":
        if state.live_service:
            await state.live_service.stop()
        await websocket.send_text(json.dumps({"type": "live_stopped"}))


# =============================================================================
# Entry Point
# =============================================================================


def main() -> None:
    """Run the development server."""
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
