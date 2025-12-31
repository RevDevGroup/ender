import asyncio
import json
import uuid
from datetime import datetime, timezone

import aioredis
from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import settings


class WebSocketManager:
    """
    Manage WebSocket connections using Redis for state and Pub/Sub for messaging.
    """

    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)

    def _get_device_key(self, device_id: uuid.UUID) -> str:
        """Get the Redis key for storing a device's connection status."""
        return f"ws:device:{device_id}"

    def _get_device_channel(self, device_id: uuid.UUID) -> str:
        """Get the Redis Pub/Sub channel name for a specific device."""
        return f"ws:channel:{device_id}"

    async def connect(self, websocket: WebSocket, device_id: uuid.UUID) -> asyncio.Task:
        """
        Accept a new WebSocket connection, register it in Redis, and start
        a listener task for Pub/Sub messages.
        """
        await websocket.accept()
        device_key = self._get_device_key(device_id)

        # Set device as connected in Redis with a timeout
        await self.redis.hset(
            device_key,
            mapping={
                "connected": "1",
                "last_seen": datetime.now(timezone.utc).isoformat(),
            },
        )
        await self.redis.expire(device_key, settings.WEBSOCKET_HEARTBEAT_TIMEOUT)

        # Create a listener task for this specific device
        listener_task = asyncio.create_task(
            self._redis_listener(websocket, device_id)
        )
        return listener_task

    async def disconnect(self, device_id: uuid.UUID) -> None:
        """Mark the device as disconnected in Redis."""
        device_key = self._get_device_key(device_id)
        await self.redis.delete(device_key)

    async def refresh_heartbeat(self, device_id: uuid.UUID) -> None:
        """Refresh the device's heartbeat TTL in Redis."""
        device_key = self._get_device_key(device_id)
        if await self.redis.exists(device_key):
            await self.redis.hset(
                device_key, "last_seen", datetime.now(timezone.utc).isoformat()
            )
            await self.redis.expire(device_key, settings.WEBSOCKET_HEARTBEAT_TIMEOUT)

    async def is_connected(self, device_id: uuid.UUID) -> bool:
        """Check if a device is marked as connected in Redis."""
        device_key = self._get_device_key(device_id)
        return await self.redis.exists(device_key) > 0

    async def send_to_device(self, device_id: uuid.UUID, message: dict) -> None:
        """
        Publish a message to the device-specific Redis channel for delivery.
        """
        channel = self._get_device_channel(device_id)
        # Ensure the message is a JSON string before publishing
        await self.redis.publish(channel, json.dumps(message))

    async def _redis_listener(self, websocket: WebSocket, device_id: uuid.UUID) -> None:
        """
        Listen for messages on a Redis Pub/Sub channel and forward them
        to the given WebSocket.
        """
        channel = self._get_device_channel(device_id)
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                # Wait for a message
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=None)
                if message and message["type"] == "message":
                    # The data is a bytes string, so we need to decode it
                    data = json.loads(message["data"].decode("utf-8"))
                    await websocket.send_json(data)
        except WebSocketDisconnect:
            # Client disconnected, the main websocket loop will handle cleanup
            pass
        except Exception:
            # Other exceptions, e.g., Redis connection error
            # The main websocket loop should also handle this
            pass
        finally:
            await pubsub.unsubscribe(channel)


# Global manager instance, configured from settings
websocket_manager = WebSocketManager(settings.REDIS_URL)
