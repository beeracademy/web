from django.conf import settings
from facebook import GraphAPI, GraphAPIError

from .utils import format_sips

GRAPH = GraphAPI(getattr(settings, "FACEBOOK_ACCESS_TOKEN", None))


def put_object(parent_object, connection_name, **data):
    if settings.TESTING:
        return

    if settings.DEBUG:
        print(f"Facebook request to {parent_object}/{connection_name}")
        print("\n------------------------------")
        print(data)
        print("------------------------------\n")
        return

    try:
        return GRAPH.put_object(parent_object, connection_name, **data)
    except GraphAPIError as e:
        print("Failed to facebook request:", e)


def get_post_message(game):
    message = f"A game between {game.pretty_players_str()} just started!"
    if game.has_ended:
        message += "\n\n"
        if game.dnf:
            message += f"Game DNF after {game.duration_str()}."
        else:
            message += f"Game finished after {game.duration_str()}."
            message += "\n\nTotal sips:"
            for stats in game.get_player_stats():
                message += f"\n- {stats['username']}: "
                if stats["dnf"]:
                    message += "DNF"
                else:
                    message += f"{format_sips(stats['total_sips'])}"

    return message


def post_game_to_page(game, game_url):
    r = put_object(
        getattr(settings, "FACEBOOK_PAGE_ID", None),
        "feed",
        message=get_post_message(game),
        link=game_url,
    )
    if not r:
        return

    game.facebook_post_id = r["id"]
    game.save()


def update_game_post(game):
    if not game.facebook_post_id:
        return

    put_object(game.facebook_post_id, "", message=get_post_message(game))
