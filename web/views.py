from django.shortcuts import render
from django.db.models import F
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import DetailView, ListView
from django.core.paginator import Paginator
from games.models import User, Game, Season, all_time_season
from functools import partial
from .utils import updated_query_url


def index(request):
    return render(request, "index.html")


class MyLoginView(LoginView):
    template_name = "login.html"


class MyLogoutView(LogoutView):
    pass


class PaginatedListView(ListView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = Paginator(context["object_list"], 20)
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
        return Game.objects.all().order_by(F("end_datetime").desc(nulls_first=True))


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        season = get_season(self.request)
        context["season"] = season
        context["stats"] = self.object.stats_for_season(season)
        return context


class RankingView(PaginatedListView):
    template_name = "ranking.html"

    def get_queryset(self):
        return [{
            "user": User.objects.first(),
            "rank": 7,
            "value": 1234,
        }] * 100

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["season"] = get_season(self.request)

        ranking_names = [
            "Total sips",
            "Best game",
            "Worst game",
            "Total chugs",
            "Fastest chug time",
        ]

        ranking_urls = []
        for name in ranking_names:
            ranking_urls.append((name, updated_query_url(self.request, "type", name)))

        context["ranking_tabs"] = ranking_urls

        ranking_type = self.request.GET.get("type")
        if not ranking_type in ranking_names:
            ranking_type = ranking_names[0]

        context["ranking"] = {"name": ranking_type}

        return context
