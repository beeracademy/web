import datetime
from collections import Counter, defaultdict
from dataclasses import dataclass
from threading import Thread
from typing import Any, Callable, Optional

from django.db.models import Sum
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.urls import reverse
from scipy.stats import hypergeom

from academy.utils import is_running_real_server
from games.models import (
    Card,
    Chug,
    Game,
    GamePlayerStat,
    Season,
    all_time_season,
    filter_season_and_player_count,
)
from games.utils import get_milliseconds

from .heatmap import games_heatmap_data
from .utils import get_all_seasons, round_timedelta


@dataclass(frozen=True)
class Distribution:
    name: str
    prob_f: Callable[[int], float]


def sips_count_distribution(player_count: int) -> Distribution:
    # Exact probability
    def get_outcomes(values: list[int], draws: int) -> dict[int, int]:
        outcomes = defaultdict(int)
        outcomes[0, 0] = 1

        for v in values:
            noutcomes = outcomes.copy()
            for (total, used), c in outcomes.items():
                total += v
                used += 1
                if used <= draws:
                    noutcomes[total, used] += c

            outcomes = noutcomes

        return {total: c for (total, used), c in outcomes.items() if used == draws}

    values = [i for _ in range(player_count) for i in range(2, 15)]
    outcomes = get_outcomes(values, 13)
    total_outcomes = sum(outcomes.values())

    return Distribution(
        name=f"SumP({player_count})",
        prob_f=lambda x: outcomes.get(x, 0) / total_outcomes,
    )


def chug_count_distribution(player_count: int) -> Distribution:
    # Exact probability
    N = 13 * player_count
    K = player_count
    n = 13
    rv = hypergeom(N, K, n)
    pmf = rv.pmf  # type: ignore
    return Distribution(name="HyperGeometric({N}, {K}, {n})", prob_f=pmf)


def combined_distribution(
    season: Season,
    dist_f: Callable[[int], Distribution],
) -> Distribution:
    ds = []
    ws = []
    for player_count in range(2, 6 + 1):
        ds.append(dist_f(player_count))
        ws.append(
            GamePlayerStat.get_stats_with_player_count(season, player_count).count()
        )

    total_ws = sum(ws)

    return Distribution(
        name="\n"
        + " + \n".join(f"{w / total_ws:.2f} * {d.name}" for d, w in zip(ds, ws)),
        prob_f=lambda x: sum(d.prob_f(x) * w / total_ws for d, w in zip(ds, ws)),
    )


def generate_context_data(
    season: Season, player_count: Optional[int]
) -> dict[str, Any]:
    context = {}

    games = filter_season_and_player_count(Game.objects, season, player_count)

    total_sips = (
        Card.objects.filter(game__id__in=games).aggregate(total_sips=Sum("value"))[
            "total_sips"
        ]
        or 0
    )

    games_with_durations = Game.add_durations(games)

    total_duration = games_with_durations.aggregate(total_duration=Sum("duration"))[
        "total_duration"
    ] or datetime.timedelta(0)

    context["game_stats"] = {
        "total_games": games.count(),
        "total_dnf": games.filter(dnf=True).count(),
        "total_sips": total_sips,
        "total_beers": total_sips / 14,
        "total_duration": str(round_timedelta(total_duration)),
    }

    games_played = Counter()
    for g in games.all():
        if g.end_datetime:
            games_played[g.end_datetime.date()] += 1

    context["heatmap_data"] = games_heatmap_data(games, season)

    stat_types = {
        "sips_data": (
            GamePlayerStat.get_sips_distribution(season, player_count),
            sips_count_distribution,
        ),
        "chugs_data": (
            GamePlayerStat.get_chugs_distribution(season, player_count),
            chug_count_distribution,
        ),
    }

    for name, (stats, base_dist) in stat_types.items():
        xs = []
        ys = []
        probs = []
        dist_str = None
        if stats.exists():
            d = {s["value"]: s["value__count"] for s in stats}
            if player_count is None:
                dist = combined_distribution(season, base_dist)
            else:
                dist = base_dist(player_count)

            dist_str = dist.name

            for x in range(stats.first()["value"], stats.last()["value"] + 1):
                xs.append(x)
                ys.append(d.get(x, 0))

                if dist:
                    probs.append(dist.prob_f(x))

        context[name] = {
            "xs": xs,
            "ys": ys,
            "total_ys": sum(ys),
            "probs": probs,
            "probs_exact": True,
            "dist_str": dist_str,
        }

    BUCKETS = 60
    chugs = filter_season_and_player_count(
        Chug.objects, season, player_count, key="card__game"
    )
    duration_data = [
        {
            "name": "duration_data",
            "max_duration": 4,
            "max_duration_unit": "hours",
            "durations": lambda max_duration: (
                g["duration"]
                for g in games_with_durations.filter(
                    dnf=False, duration__lte=max_duration
                ).values("duration")
            ),
            "format": str,
        },
        {
            "name": "chug_duration_data",
            "max_duration": 15,
            "max_duration_unit": "seconds",
            "durations": lambda max_duration: (
                datetime.timedelta(milliseconds=c["duration_ms"])
                for c in chugs.filter(
                    duration_ms__lte=get_milliseconds(max_duration)
                ).values("duration_ms")
            ),
            "format": lambda td: f"{td.total_seconds():.2f}",
        },
    ]

    for d in duration_data:
        max_duration = datetime.timedelta(**{d["max_duration_unit"]: d["max_duration"]})
        bucket_span = max_duration / BUCKETS
        occurrences = Counter()
        for duration in d["durations"](max_duration):
            x = int(duration / bucket_span)
            occurrences[x] += 1

        context[d["name"]] = {
            "total_ys": sum(occurrences.values()),
            "bucket_span_seconds": bucket_span.total_seconds(),
            "max_duration": f"{d['max_duration']} {d['max_duration_unit']}",
            "xs": [d["format"]((i + 1) * bucket_span) for i in range(BUCKETS)],
            "ys": [occurrences[i] for i in range(BUCKETS)],
        }

    context["chug_table_header"] = ["Players\xa0\\\xa0Chugs", *range(6 + 1)]
    context["chug_table"] = []
    for pcount in range(2, 6 + 1):
        row = [pcount]
        context["chug_table"].append(row)
        dist = chug_count_distribution(pcount)
        for chugs in range(6 + 1):
            row.append(dist.prob_f(chugs) * 100 if chugs <= pcount else None)

    context["location_data"] = []
    for g in games.filter(
        location_latitude__isnull=False, location_accuracy__lte=100 * 1000
    ):
        game_url = reverse("game_detail", args=[g.id])
        context["location_data"].append(
            {
                "latitude": g.location_latitude,
                "longitude": g.location_longitude,
                "popup": f"<a href='{game_url}'>{g.date}<br>{g.players_str()}</a>",
            }
        )

    return context


CONTEXT_DATA_CACHE = {}


def get_context_data(season: Season, player_count: Optional[int]) -> dict[str, Any]:
    context = CONTEXT_DATA_CACHE.get((season, player_count))
    if context is None:
        context = populate_cache(season, player_count)
    return context


def populate_cache(season: Season, player_count: Optional[int]) -> dict[str, Any]:

    context = CONTEXT_DATA_CACHE[season, player_count] = generate_context_data(
        season, player_count
    )
    return context


def init_cache(
    seasons: Optional[list[Season]] = None,
    player_counts: Optional[list[Optional[int]]] = None,
) -> None:
    seasons = seasons or get_all_seasons()
    player_counts = player_counts or [None] + list(range(2, 6 + 1))

    def aux() -> None:
        print("Initializing stats cache...")
        for season in seasons:
            for player_count in player_counts:
                populate_cache(season, player_count)
        print("Initialized stats cache.")

    if not is_running_real_server():
        return

    thread = Thread(target=aux)
    thread.start()


def reinit_caches_containing_game(game: Game) -> None:
    init_cache(
        seasons=[all_time_season, game.get_season()],
        player_counts=[None, game.players.count()],
    )


@receiver(pre_delete, sender=Game)
def on_game_deleted(*, instance: Game, **_kwargs) -> None:
    reinit_caches_containing_game(instance)


@receiver(post_save, sender=Game)
def on_game_saved(*, instance: Game, **_kwargs) -> None:
    if instance.has_ended:
        reinit_caches_containing_game(instance)
