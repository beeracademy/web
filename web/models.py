from django.db import models
from django.utils import timezone

from games.models import User


class FailedGameUpload(models.Model):
    game_log = models.TextField()
    notes = models.TextField(blank=True)
    created = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user}: {self.created}"
