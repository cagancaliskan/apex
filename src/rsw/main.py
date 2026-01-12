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
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from rsw.api.routes.health import router as health_router
from rsw.api.routes.sessions import init_session_routes
from rsw.api.routes.sessions import router as sessions_router
from rsw.api.routes.simulation import init_simulation_routes
from rsw.api.routes.simulation import router as simulation_router
from rsw.api.websocket_manager import ConnectionManager
from rsw.config import load_app_config, load_tracks_config
from rsw.ingest import OpenF1Client
from rsw.logging_config import get_logger
from rsw.middleware.rate_limit import RateLimitMiddleware
from rsw.models.degradation import ModelManager
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
        self.active_session_key: int | None = None
        self.active_replay: Any = None
        self.speed_multiplier: float = 1.0
        self.simulation_service: SimulationService | None = None
        self.all_driver_telemetry: dict[str, Any] = {}


# Global instances
app_state = AppState()
connection_manager = ConnectionManager()


# =============================================================================
# Application Lifecycle
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.

    Handles startup initialization and graceful shutdown.
    """
    logger.info("application_starting", version="1.1.0")

    # Initialize simulation service
    app_state.simulation_service = SimulationService(app_state, connection_manager)

    # Initialize route modules with app state
    init_simulation_routes(app_state)
    init_session_routes(app_state)

    logger.info("application_ready")

    yield

    # Shutdown
    logger.info("application_stopping")
    if app_state.simulation_service:
        await app_state.simulation_service.stop()
    logger.info("application_stopped")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Race Strategy Workbench API",
    version="1.1.0",
    description="Real-time F1 race simulation and strategy analysis",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
CORS_ORIGINS = os.getenv("RSW_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(
    ","
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Rate Limiting (disabled in development by default)
if os.getenv("RSW_RATE_LIMIT_ENABLED", "false").lower() == "true":
    app.add_middleware(RateLimitMiddleware)


# =============================================================================
# Include Routers
# =============================================================================

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(simulation_router, prefix="/api", tags=["simulation"])
app.include_router(sessions_router, prefix="/api", tags=["sessions"])


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
    return app_state.store.to_dict()


# =============================================================================
# Replay Endpoints
# =============================================================================


@app.post("/api/replay/control", tags=["replay"])
async def replay_control(action: str) -> dict[str, Any]:
    """
    Control replay playback.

    Args:
        action: One of 'play', 'pause', 'stop'
    """
    if app_state.active_replay is None:
        raise HTTPException(status_code=400, detail="No active replay session")

    actions = {"play", "pause", "stop"}
    if action not in actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of: {actions}")

    getattr(app_state.active_replay, action)()
    return {"status": "ok", "action": action}


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
    app_state.active_replay = replay
    replay.play()

    return {"status": "started", "session_key": session_key}


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
    await connection_manager.connect(websocket)

    try:
        # Send initial state
        safe_data = sanitize_for_json(app_state.store.to_dict())
        await websocket.send_text(
            json.dumps(
                {
                    "type": "state_update",
                    "data": safe_data,
                },
                default=str,
            )
        )

        # Register for broadcasts
        connection_manager.register(websocket)

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
        connection_manager.disconnect(websocket)


async def _handle_ws_message(websocket: WebSocket, message: dict[str, Any]) -> None:
    """Handle incoming WebSocket messages."""
    msg_type = message.get("type")

    if msg_type == "ping":
        await websocket.send_text(json.dumps({"type": "pong"}))

    elif msg_type == "start_session":
        year = message.get("year", 2023)
        round_num = message.get("round_num", 1)

        if app_state.simulation_service:
            await app_state.simulation_service.start(year, round_num)
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
        if app_state.simulation_service:
            await app_state.simulation_service.stop()
        await websocket.send_text(json.dumps({"type": "session_stopped"}))

    elif msg_type == "set_speed":
        speed = message.get("speed", 1.0)
        app_state.speed_multiplier = speed
        await websocket.send_text(json.dumps({"type": "speed_set", "speed": speed}))


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
