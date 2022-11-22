from django.conf import settings
from facebook import GraphAPI, GraphAPIError

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
        message += game.game_state_description()

    return message


def post_game_to_page(game):
    r = put_object(
        getattr(settings, "FACEBOOK_PAGE_ID", None),
        "feed",
        message=get_post_message(game),
        link=game.get_absolute_url(),
    )
    if not r:
        return

    game.facebook_post_id = r["id"]
    game.save()


def update_game_post(game):
    if not game.facebook_post_id:
        return

    put_object(game.facebook_post_id, "", message=get_post_message(game))
