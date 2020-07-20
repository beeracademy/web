from django.db import models
from django.utils import timezone


class FailedGameUpload(models.Model):
    game_log = models.TextField()
    notes = models.TextField(blank=True)
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.created}"
