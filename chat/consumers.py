import datetime
import sys
import uuid

from channels.generic.websocket import JsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from games.models import Game

from .models import ChatMessage


class ChatConsumer(JsonWebsocketConsumer):
    def save_message(self, data, now):
        game = Game.objects.get(id=int(self.game_id))
        return ChatMessage.objects.create(
            game=game,
            datetime=now,
            chat_id=self.chat_id,
            user=self.user,
            is_game=self.is_game,
        )

    def send_to_group(self, data):
        now = datetime.datetime.now()
        message = self.save_message(data, now)

        self.channel_layer.group_send(
            self.room_group_name,
            {
                **data,
                "type": "chat_event",
                "datetime": now.isoformat(),
                "chat_id": self.chat_id,
                "username": self.user.username,
                "user_id": self.user.id,
                "is_game": self.is_game,
            },
        )

    def connect(self):
        print("connect", file=__import__("sys").stderr)
        self.user = self.scope["user"]
        self.is_game = self.scope["query_string"] == b"game"
        self.chat_id = str(uuid.uuid4())

        if self.is_game:
            self.user = AnonymousUser()

        self.game_id = self.scope["url_route"]["kwargs"]["game_id"]
        self.room_name = self.scope["url_route"]["kwargs"]["game_id"]
        self.room_group_name = f"chat_{self.room_name}"

        self.channel_layer.group_add(self.room_group_name, self.channel_name)

        self.accept()

        self.send_json(
            {
                "event": "chat_id",
                "chat_id": self.chat_id,
            }
        )

        self.send_to_group(
            {
                "event": "connect",
            }
        )

    def disconnect(self, close_code):
        self.send_to_group(
            {
                "event": "disconnect",
            }
        )
        self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    def receive_json(self, content):
        message = content.get("message")
        if not message:
            return

        self.send_to_group(
            {
                "event": "message",
                "message": message,
            }
        )

    def chat_event(self, event):
        # Make a copy as we can't remove type from the received event or dispatching will fail
        event = dict(event)

        del event["type"]
        self.send_json(event)
