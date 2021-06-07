from django.db import models
from games.models import Game, User


class ChatMessage(models.Model):
    game = models.ForeignKey(Game, models.CASCADE)
    datetime = models.DateTimeField()
    chat_id = models.UUIDField()
    user = models.ForeignKey(User, models.CASCADE)
    is_game = models.BooleanField()
