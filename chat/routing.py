from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/chat/<int:game_id>/", consumers.ChatConsumer.as_asgi()),
    path("ws/remote/<uuid:token>/", consumers.GameRemoteConsumer.as_asgi()),
]
