import datetime
import json
import logging
import uuid
from typing import ClassVar

import redis.asyncio as aioredis
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class ChatHistoryStore:
    """Thin async wrapper around Redis for persisting chat messages per room.

    All public methods catch Redis/connection errors and log a warning rather
    than raising — the chat works without history if Redis is unavailable.
    """

    def __init__(self, redis_url: str, ttl_seconds: int):
        self._redis_url = redis_url
        self._ttl = ttl_seconds
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = await aioredis.from_url(
                self._redis_url, decode_responses=True
            )
        return self._client

    def _key(self, room: str) -> str:
        return f"chat_history:{room}"

    async def add_message(self, room: str, message: dict) -> None:
        """Append a message to the room's history list and refresh the TTL."""
        try:
            client = await self._get_client()
            key = self._key(room)
            await client.rpush(key, json.dumps(message))
            await client.expire(key, self._ttl)
        except Exception:
            self._client = None  # reset so next call gets a fresh connection
            logger.warning(
                "chat history: failed to store message in Redis", exc_info=True
            )

    async def get_messages(self, room: str) -> list[dict]:
        """Return all stored messages for the room (oldest first).

        Returns an empty list if Redis is unavailable.
        """
        try:
            client = await self._get_client()
            raw = await client.lrange(self._key(room), 0, -1)
        except Exception:
            self._client = None  # reset so next call gets a fresh connection
            logger.warning(
                "chat history: failed to fetch messages from Redis", exc_info=True
            )
            return []

        messages = []
        for item in raw:
            try:
                messages.append(json.loads(item))
            except json.JSONDecodeError, ValueError:
                pass
        return messages


# Module-level singleton — shared across all consumer instances in the process.
_history_store: ChatHistoryStore | None = None


def get_history_store() -> ChatHistoryStore:
    global _history_store
    if _history_store is None:
        _history_store = ChatHistoryStore(
            redis_url=settings.REDIS_URL,
            ttl_seconds=settings.CHAT_HISTORY_TTL_SECONDS,
        )
    return _history_store


class ChatConsumer(AsyncJsonWebsocketConsumer):
    rooms: ClassVar[dict] = {}

    async def broadcast_presence(self):
        users = list(self.rooms.get(self.room_group_name, {}).values())
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_event",
                "event": "presence",
                "users": users,
            },
        )

    async def send_to_group(self, data):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                **data,
                "type": "chat_event",
                "datetime": datetime.datetime.now(tz=datetime.UTC).isoformat(),
                "chat_id": self.chat_id,
                "username": self.user.username,
                "user_id": self.user.id,
                "is_game": self.is_game,
            },
        )

    async def connect(self):
        self.user = self.scope["user"]
        self.is_game = self.scope["query_string"] == b"game"
        self.chat_id = str(uuid.uuid4())

        if self.is_game:
            self.user = AnonymousUser()

        self.room_name = self.scope["url_route"]["kwargs"]["game_id"]
        self.room_group_name = f"chat_{self.room_name}"

        if self.room_group_name not in self.rooms:
            self.rooms[self.room_group_name] = {}
        self.rooms[self.room_group_name][self.chat_id] = {
            "chat_id": self.chat_id,
            "username": self.user.username,
            "user_id": self.user.id,
            "is_game": self.is_game,
        }

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        await self.send_json(
            {
                "event": "chat_id",
                "chat_id": self.chat_id,
            }
        )

        # Send chat history to the newly connected client only.
        history = await get_history_store().get_messages(self.room_group_name)
        if history:
            await self.send_json(
                {
                    "event": "history",
                    "messages": history,
                }
            )

        await self.send_to_group(
            {
                "event": "connect",
            }
        )
        await self.broadcast_presence()

    async def disconnect(self, close_code):
        if self.room_group_name in self.rooms:
            self.rooms[self.room_group_name].pop(self.chat_id, None)
            if not self.rooms[self.room_group_name]:
                del self.rooms[self.room_group_name]

        await self.send_to_group(
            {
                "event": "disconnect",
            }
        )
        await self.broadcast_presence()
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content):
        message = content.get("message")
        if not message:
            return

        now = datetime.datetime.now(tz=datetime.UTC).isoformat()

        # Persist the message to Redis before broadcasting.
        stored = {
            "event": "message",
            "message": message,
            "datetime": now,
            "chat_id": self.chat_id,
            "username": self.user.username,
            "user_id": self.user.id,
            "is_game": self.is_game,
        }
        await get_history_store().add_message(self.room_group_name, stored)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                **stored,
                "type": "chat_event",
            },
        )

    async def chat_event(self, event):
        # Make a copy as we can't remove type from the received event or dispatching will fail
        event = dict(event)

        del event["type"]
        await self.send_json(event)


class GameRemoteConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["token"]
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "remote_message",
                "content": content,
            },
        )

    async def remote_message(self, event):
        await self.send_json(event["content"])
