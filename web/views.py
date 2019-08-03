from django.shortcuts import render
from django.db.models import F
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import DetailView, ListView
from django.core.paginator import Paginator
from games.models import User, Game, Season, PlayerStat, all_time_season, filter_season
from functools import partial
from .utils import updated_query_url


def index(request):
    return render(request, "index.html")


class MyLoginView(LoginView):
    template_name = "login.html"


class MyLogoutView(LogoutView):
    pass


class PaginatedListView(ListView):
    page_limit = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = Paginator(context["object_list"], self.page_limit)
        page = self.request.GET.get("page")
        object_list = paginator.get_page(page)
        context["object_list"] = object_list

        page_url = partial(updated_query_url, self.request, "page")

        # We want to preserve other query parameters, when changing pages
        context["paginator_first_url"] = page_url(1)
        context["paginator_last_url"] = page_url(paginator.num_pages)

        if object_list.has_previous():
            context["paginator_previous_url"] = page_url(
                object_list.previous_page_number()
            )

        if object_list.has_next():
            context["paginator_next_url"] = page_url(object_list.next_page_number())

        return context


class GamesView(PaginatedListView):
    model = Game
    template_name = "game_list.html"

    def get_queryset(self):
        season = get_season(self.request)
        return filter_season(Game.objects, season).order_by(
            F("end_datetime").desc(nulls_first=True)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        season = get_season(self.request)
        context["season"] = season
        return context


class GameDetailView(DetailView):
    model = Game
    template_name = "game_detail.html"


class PlayersView(PaginatedListView):
    model = User
    template_name = "player_list.html"


def get_season(request):
    season_number = request.GET.get("season")
    if Season.is_valid_season_number(season_number):
        return Season(int(season_number))
    else:
        return all_time_season


class PlayerDetailView(DetailView):
    model = User
    template_name = "player_detail.html"
    # Without this, django will set context["user"] to the viewed user,
    # overriding the current user
    context_object_name = "_unused"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        season = get_season(self.request)
        context["season"] = season
        context["stats"] = self.object.stats_for_season(season)
        return context


def django_getattr(obj, key):
    keys = key.split("__")
    for k in keys:
        obj = getattr(obj, k)
    return obj


class Ranking:
    def __init__(self, name, ordering, game_key=None):
        self.name = name
        self.ordering = ordering
        self.game_key = game_key

    @property
    def value_key(self):
        return self.ordering.lstrip("-")

    def get_value(self, o):
        return django_getattr(o, self.value_key)

    def get_game(self, o):
        if self.game_key:
            return django_getattr(o, self.game_key)
        return None


class RankingView(PaginatedListView):
    template_name = "ranking.html"
    page_limit = 15
    rankings = [
        Ranking("Total sips", "-total_sips"),
        Ranking("Best game", "-best_game_sips", "best_game"),
        Ranking("Worst game", "worst_game_sips", "worst_game"),
        Ranking("Total chugs", "-total_chugs"),
        Ranking(
            "Fastest chug time",
            "fastest_chug__duration_in_milliseconds",
            "fastest_chug__card__game",
        ),
    ]

    def get_ranking(self):
        ranking_type = self.request.GET.get("type")
        for ranking in self.rankings:
            if ranking_type == ranking.name:
                return ranking

        return self.rankings[0]

    def get_queryset(self):
        season = get_season(self.request)
        ranking = self.get_ranking()
        return PlayerStat.objects.filter(
            **{
                "season_number": season.number,
                "total_games__gt": 0,
                f"{ranking.value_key}__isnull": False,
            }
        ).order_by(ranking.ordering)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["season"] = get_season(self.request)

        ranking_urls = []
        for ranking in self.rankings:
            ranking_urls.append(
                (ranking.name, updated_query_url(self.request, "type", ranking.name))
            )

        context["ranking_tabs"] = ranking_urls

        ranking = self.get_ranking()
        context["ranking"] = {"name": ranking.name}

        object_list = context["object_list"]
        start_index = object_list.start_index()
        for i, o in enumerate(object_list):
            o.rank = start_index + i
            o.value = ranking.get_value(o)
            o.game = ranking.get_game(o)

        return context
