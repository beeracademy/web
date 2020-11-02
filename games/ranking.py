from .models import PlayerStat
from .utils import (
    add_thousand_seperators,
    format_chug_duration,
    format_sips_html,
    format_total_time,
)


def django_getattr(obj, key):
    keys = key.split("__")
    for k in keys:
        obj = getattr(obj, k)
    return obj


class Ranking:
    def __init__(
        self, name, ordering, game_key=None, formatter=add_thousand_seperators
    ):
        self.name = name
        self.ordering = ordering
        self.game_key = game_key
        self.formatter = formatter

    @property
    def key(self):
        return self.value_key.split("__")[0]

    @property
    def value_key(self):
        return self.ordering.lstrip("-")

    def get_value(self, o):
        return self.formatter(django_getattr(o, self.value_key))

    def get_game(self, o):
        if self.game_key:
            return django_getattr(o, self.game_key)
        return None

    def get_qs(self, season):
        return PlayerStat.objects.filter(
            **{
                "season_number": season.number,
                "total_games__gt": 0,
                f"{self.value_key}__isnull": False,
            }
        ).order_by(self.ordering)

    def get_rank(self, user, season):
        stats = user.stats_for_season(season)

        try:
            user_index = list(self.get_qs(season)).index(stats)
            return user_index + 1
        except ValueError:
            return None


RANKINGS = [
    Ranking("Total sips", "-total_sips"),
    Ranking("Best game", "-best_game_sips", "best_game", format_sips_html),
    Ranking("Worst game", "worst_game_sips", "worst_game", format_sips_html),
    Ranking("Total chugs", "-total_chugs"),
    Ranking(
        "Fastest chug",
        "fastest_chug__duration_ms",
        "fastest_chug__card__game",
        format_chug_duration,
    ),
    Ranking(
        "Total time played",
        "-total_time_played_seconds",
        formatter=format_total_time,
    ),
]


def get_ranking_from_key(key):
    for ranking in RANKINGS:
        if key == ranking.key:
            return ranking
