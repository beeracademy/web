import datetime

from games.models import Season, all_time_season
from games.ranking import RANKINGS, get_ranking_from_key


def round_timedelta(td):
    return datetime.timedelta(days=td.days, seconds=td.seconds)


def updated_query_url(request, updates):
    query = request.GET.copy()
    for k, v in updates.items():
        if v is None:
            if k in query:
                del query[k]
        else:
            query[k] = v

    url = request.path
    q = query.urlencode()
    if q:
        url += "?" + q

    return url


class ChooserData:
    key = None
    reset_keys = []
    # The first value should be the default
    values = []

    def __init__(self, request):
        self.request = request

    def to_str(self, value):
        return str(value)

    def to_query_str(self, value):
        raise NotImplementedError

    def from_str(self, value):
        raise NotImplementedError

    @property
    def current(self):
        return self.from_str(self.request.GET.get(self.key, ""))

    @property
    def current_str(self):
        return self.to_str(self.current)

    @property
    def urls(self):
        return [
            (
                self.to_str(v),
                updated_query_url(
                    self.request,
                    {
                        self.key: None if v == self.values[0] else self.to_query_str(v),
                        **{k: None for k in self.reset_keys},
                    },
                ),
            )
            for v in self.values
        ]


class SeasonChooser(ChooserData):
    key = "season"
    reset_keys = ["page"]
    current_season = Season.current_season()
    values = [all_time_season] + list(map(Season, range(current_season.number, 0, -1)))

    def from_str(self, s):
        if Season.is_valid_season_number(s):
            return Season(int(s))
        else:
            return all_time_season

    def to_query_str(self, value):
        return value.number


class RankingChooser(ChooserData):
    key = "type"
    reset_keys = ["page"]
    values = RANKINGS

    def from_str(self, s):
        return get_ranking_from_key(s) or RANKINGS[0]

    def to_str(self, value):
        return value.name

    def to_query_str(self, value):
        return value.key


class PlayerCountChooser(ChooserData):
    key = "player_count"
    values = [None] + list(range(2, 6 + 1))

    def from_str(self, s):
        try:
            v = int(s)
            if 2 <= v <= 6:
                return v
        except ValueError:
            pass

        return None

    def to_str(self, value):
        if value == None:
            return "All games"

        return f"{value} player games"

    def to_query_str(self, value):
        if value == None:
            return None

        return value
