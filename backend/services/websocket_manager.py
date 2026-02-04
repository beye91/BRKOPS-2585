# =============================================================================
# BRKOPS-2585 WebSocket Manager
# Real-time event broadcasting
# =============================================================================

import asyncio
from typing import Dict, List, Set
import json

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


class WebSocketManager:
    """Manage WebSocket connections and event broadcasting."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.job_subscriptions: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.debug("WebSocket connected", total_connections=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Remove from all job subscriptions
        for job_id, subscribers in list(self.job_subscriptions.items()):
            if websocket in subscribers:
                subscribers.discard(websocket)
                if not subscribers:
                    del self.job_subscriptions[job_id]

        logger.debug("WebSocket disconnected", total_connections=len(self.active_connections))

    async def subscribe_to_job(self, websocket: WebSocket, job_id: str):
        """Subscribe a WebSocket to updates for a specific job."""
        async with self._lock:
            if job_id not in self.job_subscriptions:
                self.job_subscriptions[job_id] = set()
            self.job_subscriptions[job_id].add(websocket)
        logger.debug("WebSocket subscribed to job", job_id=job_id)

    async def unsubscribe_from_job(self, websocket: WebSocket, job_id: str):
        """Unsubscribe a WebSocket from job updates."""
        async with self._lock:
            if job_id in self.job_subscriptions:
                self.job_subscriptions[job_id].discard(websocket)
                if not self.job_subscriptions[job_id]:
                    del self.job_subscriptions[job_id]

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning("Failed to send to WebSocket", error=str(e))
                disconnected.append(connection)

        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_to_job(self, job_id: str, message: dict):
        """Broadcast a message to all clients subscribed to a specific job."""
        if job_id not in self.job_subscriptions:
            return

        disconnected = []
        for connection in self.job_subscriptions[job_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning("Failed to send to WebSocket", error=str(e))
                disconnected.append(connection)

        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    async def send_stage_update(
        self,
        job_id: str,
        stage: str,
        status: str,
        data: dict = None,
        message: str = None,
    ):
        """Send a pipeline stage update."""
        event = {
            "type": "operation.stage_changed",
            "job_id": job_id,
            "stage": stage,
            "status": status,
            "data": data,
            "message": message,
        }

        # Broadcast to all and specifically to job subscribers
        await self.broadcast(event)

    async def send_log_entry(
        self,
        job_id: str,
        level: str,
        message: str,
        source: str = None,
    ):
        """Send a log entry to connected clients."""
        event = {
            "type": "log.entry",
            "job_id": job_id,
            "level": level,
            "message": message,
            "source": source,
            "timestamp": asyncio.get_event_loop().time(),
        }

        await self.broadcast_to_job(job_id, event)

    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)


# Global WebSocket manager instance
manager = WebSocketManager()
