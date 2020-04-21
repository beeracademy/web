import datetime

from .models import PlayerStat


def add_thousand_seperators(value):
    return f"{value:,}"


def format_duration(ms):
    td = datetime.timedelta(milliseconds=ms)
    s = str(td)
    if not "." in s:
        s += "."

    a, b = s.split(".")
    return a.split(":", 1)[1] + "." + b.rstrip("0").ljust(3, "0")


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
    Ranking("Best game", "-best_game_sips", "best_game"),
    Ranking("Worst game", "worst_game_sips", "worst_game"),
    Ranking("Total chugs", "-total_chugs"),
    Ranking(
        "Fastest chug",
        "fastest_chug__duration_in_milliseconds",
        "fastest_chug__card__game",
        format_duration,
    ),
]


def get_ranking_from_key(key):
    for ranking in RANKINGS:
        if key == ranking.key:
            return ranking
