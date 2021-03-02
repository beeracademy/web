import datetime

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
            },
        )

    async def connect(self):
        self.user = self.scope["user"]
        self.is_game = self.scope["query_string"] == b"game"

        if self.is_game:
            self.user = AnonymousUser()

        self.room_name = self.scope["url_route"]["kwargs"]["game_id"]
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        await self.send_to_group(
            {
                "event": "connect",
                "username": self.user.username,
                "user_id": self.user.id,
                "is_game": self.is_game,
            }
        )

    async def disconnect(self, close_code):
        await self.send_to_group(
            {
                "event": "disconnect",
                "username": self.user.username,
                "user_id": self.user.id,
                "is_game": self.is_game,
            }
        )
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content):
        # Only allow logged in users to write to the chat,
        # but allow all to view it
        if not self.user.id and not self.is_game:
            return

        message = content.get("message")
        if not message:
            return

        await self.send_to_group(
            {
                "event": "message",
                "message": message,
                "username": self.user.username,
                "user_id": self.user.id,
                "is_game": self.is_game,
            }
        )

    async def chat_event(self, event):
        # Make a copy as we can't remove type from the received event or dispatching will fail
        event = dict(event)

        del event["type"]
        await self.send_json(event)
