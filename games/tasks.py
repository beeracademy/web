import datetime

from celery import shared_task
from django.utils import timezone

from .facebook import post_game_to_page, update_game_post
from .models import Game, recalculate_all_stats


@shared_task
def mark_dnf_games():
    DNF_THRESHOLD = datetime.timedelta(hours=12)

    for game in Game.objects.filter(end_datetime__isnull=True, dnf=False):
        if timezone.now() - game.get_last_activity_time() >= DNF_THRESHOLD:
            game.dnf = True
            game.save()


@shared_task
def recalculate_stats():
    recalculate_all_stats()


@shared_task
def post_game_to_facebook(game_id, game_url):
    game = Game.objects.get(id=game_id)
    post_game_to_page(game, game_url)


@shared_task
def update_facebook_post(game_id):
    game = Game.objects.get(id=game_id)
    update_game_post(game)
