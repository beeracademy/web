import datetime
import uuid

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def send_to_group(self, data):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                **data,
                "type": "chat_event",
                "datetime": datetime.datetime.now().isoformat(),
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

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        await self.send_json(
            {
                "event": "chat_id",
                "chat_id": self.chat_id,
            }
        )

        await self.send_to_group(
            {
                "event": "connect",
            }
        )

    async def disconnect(self, close_code):
        await self.send_to_group(
            {
                "event": "disconnect",
            }
        )
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content):
        message = content.get("message")
        if not message:
            return

        await self.send_to_group(
            {
                "event": "message",
                "message": message,
            }
        )

    async def chat_event(self, event):
        # Make a copy as we can't remove type from the received event or dispatching will fail
        event = dict(event)

        del event["type"]
        await self.send_json(event)
