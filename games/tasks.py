import datetime
from django.utils import timezone
from celery import shared_task
from .models import Game, PlayerStat


@shared_task
def mark_dnf_games():
    DNF_THRESHOLD = datetime.timedelta(hours=12)

    for game in Game.objects.filter(end_datetime_isnull=True, dnf=False):
        if timezone.now() - game.get_last_activity_time() >= DNF_THRESHOLD:
            game.dnf = True
            game.save()


@shared_task
def recalculate_all_stats():
    PlayerStat.recalculate_all()
