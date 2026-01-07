"""WebSocket handlers for real-time updates."""

import json
import asyncio
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)

        for conn in disconnected:
            self.active_connections.discard(conn)

    async def send_to(self, websocket: WebSocket, message: dict):
        """Send message to specific client."""
        try:
            await websocket.send_json(message)
        except Exception:
            self.active_connections.discard(websocket)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            if message.get("type") == "ping":
                await manager.send_to(websocket, {"type": "pong"})
            elif message.get("type") == "subscribe":
                # Client subscribing to updates
                await manager.send_to(
                    websocket,
                    {"type": "subscribed", "status": "ok"},
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


async def broadcast_processing_start(conversation_id: int, message_content: str):
    """Broadcast that message processing has started."""
    await manager.broadcast({
        "type": "processing_start",
        "conversation_id": conversation_id,
        "message": message_content[:100],  # Preview
    })


async def broadcast_extraction_complete(
    conversation_id: int,
    extraction: dict,
    confidence: str,
):
    """Broadcast extraction results."""
    await manager.broadcast({
        "type": "extraction_complete",
        "conversation_id": conversation_id,
        "extraction": extraction,
        "confidence": confidence,
    })


async def broadcast_order_created(
    conversation_id: int,
    order_id: int,
    routing_decision: str,
):
    """Broadcast order creation."""
    await manager.broadcast({
        "type": "order_created",
        "conversation_id": conversation_id,
        "order_id": order_id,
        "routing_decision": routing_decision,
    })


async def broadcast_confirmation_sent(
    conversation_id: int,
    confirmation: str,
):
    """Broadcast confirmation message."""
    await manager.broadcast({
        "type": "confirmation_sent",
        "conversation_id": conversation_id,
        "confirmation": confirmation,
    })
