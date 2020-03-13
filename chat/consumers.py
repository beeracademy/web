import datetime

from channels.generic.websocket import AsyncJsonWebsocketConsumer


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

        self.room_name = self.scope["url_route"]["kwargs"]["game_id"]
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        await self.send_to_group(
            {"event": "connect", "username": self.user.username,}
        )

    async def disconnect(self, close_code):
        await self.send_to_group(
            {"event": "disconnect", "username": self.user.username,}
        )
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content):
        # Only allow logged in users to write to the chat,
        # but allow all to view it
        if not self.user.id:
            return

        message = content["message"]
        if not message:
            return

        await self.send_to_group(
            {"event": "message", "message": message, "username": self.user.username,}
        )

    async def chat_event(self, event):
        # Make a copy as we can't remove type from the received event or dispatching will fail
        event = dict(event)

        del event["type"]
        await self.send_json(event)
