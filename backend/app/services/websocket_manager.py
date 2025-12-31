import asyncio
import uuid

from fastapi import WebSocket


class ConnectionManager:
    """Manage multiple WebSocket connections"""

    def __init__(self):
        self.active_connections: dict[uuid.UUID, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, device_id: uuid.UUID) -> None:
        """Websocket connect and register device"""
        await websocket.accept()
        async with self._lock:
            self.active_connections[device_id] = websocket

    async def disconnect(self, device_id: uuid.UUID) -> None:
        """Disconnect device"""
        if device_id in self.active_connections:
            async with self._lock:
                del self.active_connections[device_id]

    def is_connected(self, device_id: uuid.UUID) -> bool:
        """Check if device is connected"""
        return device_id in self.active_connections


class WebSocketManager:
    """Manage multiple active WebSocket connections"""

    def __init__(self):
        self.connection_manager = ConnectionManager()

    async def connect_device(self, websocket: WebSocket, device_id: uuid.UUID) -> None:
        """Connect Device"""
        await self.connection_manager.connect(websocket, device_id)

    async def disconnect_device(self, device_id: uuid.UUID) -> None:
        """Disconnect Device"""
        await self.connection_manager.disconnect(device_id)

    def is_device_connected(self, device_id: uuid.UUID) -> bool:
        """Verify if device is connected"""
        return self.connection_manager.is_connected(device_id)


# Global manager instance
websocket_manager = WebSocketManager()
