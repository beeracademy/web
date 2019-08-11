from django.shortcuts import render
from django.db.models import F
from django.core.files import File
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import DetailView, ListView, UpdateView
from django.core.paginator import Paginator
from games.models import (
    User,
    Game,
    GamePlayer,
    Card,
    Season,
    all_time_season,
    filter_season,
    Chug,
)
from games.ranking import RANKINGS, get_ranking_from_key
from games.serializers import GameSerializer
from .utils import updated_query_url
from .forms import UserSettingsForm
import datetime
from urllib.parse import urlencode
from collections import Counter
import random
import re

RANKING_PAGE_LIMIT = 15


def get_ranking_url(ranking, user, season):
    rank = ranking.get_rank(user, season)
    if rank is None:
        return None

    page = (rank - 1) // RANKING_PAGE_LIMIT + 1
    return f"/ranking/?" + urlencode(
        {"season": season.number, "type": ranking.value_key, "page": page}
    )


def get_recent_players(n):
    recent_players = set()
    for game in Game.objects.order_by("-end_datetime"):
        for p in game.players.all():
            if p.image:
                recent_players.add(p)

        if len(recent_players) >= n:
            break

    recent_players = random.sample(list(recent_players), min(n, len(recent_players)))
    random.shuffle(recent_players)
    return recent_players


def get_bad_chuggers(n, sample_size):
    worst_time = {}
    for chug in Chug.objects.order_by("-card__drawn_datetime"):
        u = chug.card.get_user()
        if u.image:
            worst_time[u] = max(worst_time.get(u, 0), chug.duration_in_milliseconds)

        if len(worst_time) >= sample_size:
            break

    bad_chuggers = sorted(worst_time.keys(), key=lambda u: -worst_time[u])[:n]
    random.shuffle(bad_chuggers)
    return bad_chuggers


def index(request):
    BEERS_PER_PLAYER = sum(range(2, 15)) / Game.STANDARD_SIPS_PER_BEER
    total_players = GamePlayer.objects.count()

    context = {
        "total_beers": total_players * BEERS_PER_PLAYER,
        "total_games": Game.objects.all().count(),
        "recent_players": get_recent_players(4),
        "wall_of_shame_players": get_bad_chuggers(4, 20),
    }
    return render(request, "index.html", context)


def about(request):
    return render(request, "about.html")


class MyLoginView(LoginView):
    template_name = "login.html"


class MyPasswordResetView(PasswordResetView):
    template_name = "password_reset.html"


class MyPasswordResetDoneView(PasswordResetDoneView):
    template_name = "password_reset_done.html"


class MyPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "password_reset_confirm.html"


class MyPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "password_reset_complete.html"


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

        page_url = lambda page: updated_query_url(self.request, {"page": page})

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


class GameListView(PaginatedListView):
    model = Game
    template_name = "game_list.html"

    def get_queryset(self):
        season = get_season(self.request)
        qs = filter_season(Game.objects, season, should_include_live=True)

        query = self.request.GET.get("query", "")
        usernames = re.split(r"[\s,]", query)
        for username in usernames:
            if username != "":
                qs = qs.filter(players__username__icontains=username.strip())

        return qs.distinct().order_by(
            F("end_datetime").desc(nulls_first=True), "-start_datetime"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        season = get_season(self.request)
        context["season"] = season
        context["query"] = self.request.GET.get("query", "")
        return context


class GameDetailView(DetailView):
    model = Game
    template_name = "game_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game_data"] = GameSerializer(self.object).data
        context["player_data"] = [
            {"id": p.id, "name": p.username} for p in self.object.ordered_players()
        ]
        context["card_constants"] = {
            "value_names": dict(Card.VALUES),
            "suit_names": dict(Card.SUITS),
            "suit_symbols": Card.SUIT_SYMBOLS,
        }
        return context


class PlayerListView(PaginatedListView):
    model = User
    template_name = "player_list.html"

    def get_queryset(self):
        query = self.request.GET.get("query", "")
        return User.objects.filter(username__icontains=query)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("query", "")
        return context


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

        context["rankings"] = []
        for ranking in RANKINGS:
            context["rankings"].append(
                {
                    "name": ranking.name,
                    "rank": ranking.get_rank(self.object, season),
                    "url": get_ranking_url(ranking, self.object, season),
                }
            )

        games_played = Counter()
        for g in self.object.games.all():
            if g.end_datetime:
                games_played[g.end_datetime.date()] += 1

        HEATMAP_WEEKS = 53
        context["heatmap_data"] = {"labels": [""] * HEATMAP_WEEKS, "datasets": []}

        today = timezone.now().date()
        weekday = today.weekday()

        DAY_NAMES = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        DAY_NAMES = DAY_NAMES[weekday + 1 :] + DAY_NAMES[: weekday + 1]

        for d in DAY_NAMES:
            context["heatmap_data"]["datasets"].append({"label": d, "data": []})

        date = today - datetime.timedelta(days=HEATMAP_WEEKS * 7 - 1)
        for i in range(HEATMAP_WEEKS * 7):
            if i % 7 == 0 and date.day <= 7:
                week = i // 7
                context["heatmap_data"]["labels"][week] = date.strftime("%b")

            context["heatmap_data"]["datasets"][i % 7]["data"].append(
                games_played[date]
            )
            date += datetime.timedelta(days=1)

        return context


class UserSettingsView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = "user_settings.html"
    form_class = UserSettingsForm

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return f"/players/{self.get_object().id}/"

    def form_valid(self, form):
        messages.success(self.request, "Profile updated")

        if form.cleaned_data["new_password"]:
            messages.success(self.request, "Password changed")
            self.object.set_password(form.cleaned_data["new_password"])
            update_session_auth_hash(self.request, self.request.user)

        image_io = form.cleaned_data["image_io"]
        if image_io:
            self.object.image.save(None, File(image_io), save=True)
            image_io.close()

        if form.cleaned_data["image_deleted"]:
            self.object.image.delete(save=True)

        return super().form_valid(form)


class RankingView(PaginatedListView):
    template_name = "ranking.html"
    page_limit = RANKING_PAGE_LIMIT

    def get_ranking(self):
        ranking_type = self.request.GET.get("type")
        return get_ranking_from_key(ranking_type) or RANKINGS[0]

    def get_queryset(self):
        season = get_season(self.request)
        ranking = self.get_ranking()
        return ranking.get_qs(season)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        season = get_season(self.request)
        context["season"] = season

        ranking_urls = []
        for ranking in RANKINGS:
            ranking_urls.append(
                (
                    ranking.name,
                    updated_query_url(
                        self.request, {"type": ranking.key, "page": None}
                    ),
                )
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

        if self.request.user.is_authenticated:
            context["user_rank"] = ranking.get_rank(self.request.user, season)
            context["user_rank_url"] = get_ranking_url(
                ranking, self.request.user, season
            )

        return context
