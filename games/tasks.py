import datetime

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.templatetags.static import static
from django.utils import timezone
from webpush import send_group_notification

from academy.utils import get_absolute_url

from .facebook import post_game_to_page, update_game_post
from .models import Game, recalculate_all_stats


@shared_task
def mark_dnf_games():
    DNF_THRESHOLD = datetime.timedelta(hours=12)

    for game in Game.objects.filter(end_datetime__isnull=True, dnf=False):
        if game.all_cards_done():
            continue

        if timezone.now() - game.get_last_activity_time() >= DNF_THRESHOLD:
            game.dnf = True
            game.save()


@shared_task
def delete_empty_games():
    THRESHOLD = datetime.timedelta(hours=12)

    for game in Game.objects.filter(cards=None):
        if timezone.now() - game.get_last_activity_time() >= THRESHOLD:
            game.delete()


@shared_task
def recalculate_stats():
    recalculate_all_stats()


@shared_task
def post_game_to_facebook(game_id):
    game = Game.objects.get(id=game_id)
    post_game_to_page(game)


@shared_task
@transaction.atomic()
def update_facebook_post(game_id):
    # Make sure the django thread has finished updating the game
    game = Game.objects.select_for_update().get(id=game_id)
    update_game_post(game)


@shared_task
def send_webpush_notification(game_id):
    game = Game.objects.get(id=game_id)
    payload = {
        "head": "New Academy game started",
        "body": f"A game between {game.pretty_players_str()} just started!",
        "icon": get_absolute_url(static("favicon.ico")),
        "url": game.get_absolute_url(),
    }
    try:
        send_group_notification(
            group_name=settings.WEBPUSH_GROUP,
            payload=payload,
            ttl=24 * 60 * 60,
        )
    except:
        pass
