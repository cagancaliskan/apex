"""
WebSocket Connection Manager.

Manages WebSocket connections for real-time state broadcasting to clients.

Features:
    - Connection lifecycle management (accept, register, disconnect)
    - Broadcast messaging to all connected clients
    - Automatic cleanup of disconnected clients
    - Thread-safe connection tracking

Example:
    >>> manager = ConnectionManager()
    >>> await manager.connect(websocket)
    >>> manager.register(websocket)
    >>> await manager.broadcast({"type": "state_update", "data": {...}})
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket

from rsw.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    WebSocket connection manager for real-time updates.

    Manages active WebSocket connections with automatic cleanup
    of disconnected clients during broadcast operations.

    Attributes:
        active_connections: List of currently connected WebSockets
    """

    __slots__ = ("active_connections",)

    def __init__(self) -> None:
        """Initialize the connection manager with empty connection list."""
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """
        Accept a new WebSocket connection.

        This only accepts the connection. Call register() after
        sending initial state to prevent race conditions.

        Args:
            websocket: WebSocket connection to accept
        """
        await websocket.accept()

    def register(self, websocket: WebSocket) -> None:
        """
        Register a connected WebSocket for broadcasts.

        Should be called after initial state has been sent
        to the client.

        Args:
            websocket: WebSocket to register for broadcasts
        """
        self.active_connections.append(websocket)
        logger.debug(
            "websocket_connected",
            total_connections=len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket from the connection list.

        Safe to call even if the WebSocket is not in the list.

        Args:
            websocket: WebSocket to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.debug(
                "websocket_disconnected",
                total_connections=len(self.active_connections),
            )

    async def broadcast(self, message: dict[str, Any]) -> None:
        """
        Broadcast a message to all connected clients.

        Automatically removes clients that fail to receive the message.

        Args:
            message: Dictionary to serialize and send as JSON
        """
        if not self.active_connections:
            return

        message_json = json.dumps(message, default=str)
        disconnected: list[WebSocket] = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def send_to(self, websocket: WebSocket, message: dict[str, Any]) -> bool:
        """
        Send a message to a specific client.

        Args:
            websocket: Target WebSocket connection
            message: Dictionary to serialize and send

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            message_json = json.dumps(message, default=str)
            await websocket.send_text(message_json)
            return True
        except Exception:
            self.disconnect(websocket)
            return False

    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
