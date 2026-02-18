"""
WebSocket endpoint for live transcription streaming.
Client connects to /ws/live/{meeting_id} and receives transcript segments as JSON.
"""

import json
import logging
import asyncio
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# meeting_id → list of active WebSocket connections
_connections: dict[str, list[WebSocket]] = {}


async def ws_live_transcript(websocket: WebSocket, meeting_id: str):
    await websocket.accept()

    if meeting_id not in _connections:
        _connections[meeting_id] = []
    _connections[meeting_id].append(websocket)
    logger.info(f"WebSocket connected: meeting {meeting_id} ({len(_connections[meeting_id])} clients)")

    try:
        while True:
            # Keep connection alive; data is pushed via broadcast_transcript
            await asyncio.sleep(5)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        if meeting_id in _connections:
            _connections[meeting_id] = [
                ws for ws in _connections[meeting_id] if ws != websocket
            ]
        logger.info(f"WebSocket disconnected: meeting {meeting_id}")


async def broadcast_transcript(meeting_id: str, segment: dict):
    """Called when a new transcript segment is ready. Pushes to all connected clients."""
    connections = _connections.get(meeting_id, [])
    if not connections:
        return

    dead = []
    for ws in connections:
        try:
            await ws.send_json({"type": "transcript", "data": segment})
        except Exception:
            dead.append(ws)

    if dead:
        _connections[meeting_id] = [ws for ws in connections if ws not in dead]
