import datetime
import random
import re
from collections import Counter
from collections.abc import Iterable
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.contrib.syndication.views import Feed
from django.core.files import File
from django.core.mail import mail_admins
from django.core.paginator import Paginator
from django.db.models import Case, Count, DateTimeField, F, IntegerField, Value, When
from django.shortcuts import render
from django.templatetags.static import static
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from games.achievements import ACHIEVEMENTS
from games.models import Card, Game, GamePlayer, OneTimePassword, User, filter_season
from games.ranking import RANKINGS, get_ranking_from_key
from games.serializers import GameSerializerWithPlayerStats, UserSerializer
from web import stats

from .forms import FailedGameUploadForm, UserSettingsForm
from .heatmap import games_heatmap_data
from .models import FailedGameUpload
from .utils import (
    GameOrder,
    PlayerCountChooser,
    RankingChooser,
    SeasonChooser,
    get_admin_object_url,
    updated_query_url,
)

RANKING_PAGE_LIMIT = 15


def get_ranking_url(ranking, user, season):
    rank = ranking.get_rank(user, season)
    if rank is None:
        return None

    page = (rank - 1) // RANKING_PAGE_LIMIT + 1
    return f"/ranking/?" + urlencode(
        {"season": season.number, "type": ranking.key, "page": page}
    )


def sample_max(population, k):
    return random.sample(population, min(k, len(population)))


def get_recent_players(n, min_sample_size=20):
    qs = GamePlayer.objects.filter(game__dnf=False).order_by(
        F("game__end_datetime").desc(nulls_last=True)
    )
    gps = sample_max(set(qs[:min_sample_size]), n)
    return [
        (gp.user, f"For playing game on {gp.game.date} with {gp.game.players_str()}")
        for gp in gps
    ]


def get_recent_dnf_players(n, min_sample_size=10):
    qs = GamePlayer.objects.filter(dnf=True, game__dnf=False).order_by(
        F("game__end_datetime").desc(nulls_last=True)
    )
    dnf_gps = sample_max(list(qs[:min_sample_size]), n)
    return [
        (gp.user, f"For dnf'ing game on {gp.game.date} with {gp.game.players_str()}")
        for gp in dnf_gps
    ]


def index(request):
    BEERS_PER_PLAYER = sum(range(2, 15)) / Game.STANDARD_SIPS_PER_BEER
    total_players = GamePlayer.objects.count()

    context = {
        "total_beers": total_players * BEERS_PER_PLAYER,
        "total_games": Game.objects.all().count(),
        "recent_players": get_recent_players(4),
        "wall_of_shame_players": get_recent_dnf_players(4),
        "live_games": Game.objects.filter(
            end_datetime__isnull=True, dnf=False
        ).order_by("-start_datetime")[:5],
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

        def page_url(page):
            if page == 1:
                page = None

            return updated_query_url(self.request, {"page": page})

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

    def get(self, request):
        self.order = GameOrder(request)
        return super().get(request)

    def get_queryset(self):
        season = SeasonChooser(self.request).current
        qs = filter_season(Game.objects, season, should_include_live=True)

        query = self.request.GET.get("query", "")
        parts = re.split(r"[\s,]", query)
        for part in parts:
            part = part.strip()
            if part != "":
                if part[0] == "#":
                    # Filter by hashtag in description
                    qs = qs.filter(description__icontains=part)
                else:
                    # Filter by username
                    qs = qs.filter(players__username__icontains=part)

        qs = qs.distinct()

        if self.order.current_column == "end_datetime":
            # First show live games (but not dnf games),
            # then show all other games sorted by
            # end_datetime if it is not null,
            # otherwise use start_datetime instead
            qs = qs.order_by(
                Case(
                    When(end_datetime__isnull=True, dnf=False, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                ),
                Case(
                    When(end_datetime__isnull=True, then="start_datetime"),
                    default="end_datetime",
                    output_field=DateTimeField(),
                ).desc(),
                "id",
            )
            if self.order.reverse:
                qs = qs.reverse()
        elif self.order.current_column == "duration":
            qs = Game.add_durations(qs)

            # Always show games with unknown duration last
            if self.order.reverse:
                qs = qs.order_by(F("duration").desc(nulls_last=True), "id")
            else:
                qs = qs.order_by(F("duration").asc(nulls_last=True), "id")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("query", "")
        context["order"] = self.order
        return context


class GameDetailView(DetailView):
    model = Game
    template_name = "game_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game_data"] = GameSerializerWithPlayerStats(self.object).data
        context["ordered_gameplayers"] = [
            {"dnf": gp.dnf, "user": UserSerializer(gp.user).data}
            for gp in self.object.ordered_gameplayers()
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
        return (
            User.objects.filter(username__icontains=query)
            .annotate(total_games=Count("gameplayer"))
            .order_by("-total_games", "id")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("query", "")
        return context


class PlayerDetailView(DetailView):
    model = User
    template_name = "player_detail.html"
    # Without this, django will set context["user"] to the viewed user,
    # overriding the current user
    context_object_name = "_unused"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        season = SeasonChooser(self.request).current
        context["stats"] = self.object.stats_for_season(season)

        context["achievements"] = []
        for achievement in ACHIEVEMENTS:
            context["achievements"].append(
                {
                    "achieved": achievement.has_achieved(self.object),
                    "name": achievement.name,
                    "description": achievement.description,
                    "icon_url": static(f"achievements/{achievement.icon}.svg"),
                }
            )

        context["rankings"] = []
        for ranking in RANKINGS:
            context["rankings"].append(
                {
                    "name": ranking.name,
                    "rank": ranking.get_rank(self.object, season),
                    "url": get_ranking_url(ranking, self.object, season),
                }
            )

        context["heatmap_data"] = games_heatmap_data(self.object.games.all(), season)

        if self.object == self.request.user or self.request.user.is_staff:
            otp, _ = OneTimePassword.objects.get_or_create(user=self.object)
            context["otp_data"] = otp.password

        played_with_count = Counter()
        for game in self.object.games.all():
            for player in game.players.all():
                if player != self.object:
                    played_with_count[player.username] += 1

        context["played_with_data"] = sorted(
            ({"x": k, "y": v} for k, v in played_with_count.items()),
            key=lambda x: -x["y"],
        )[:30]

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
            self.object.set_password(form.cleaned_data["new_password"])
            self.object.save()
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

    def get(self, request):
        self.season = SeasonChooser(request).current
        return super().get(request)

    def get_queryset(self):
        ranking_type = self.request.GET.get("type")
        ranking = get_ranking_from_key(ranking_type) or RANKINGS[0]
        return ranking.get_qs(self.season)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ranking_chooser = RankingChooser(self.request)
        context["ranking_chooser"] = ranking_chooser
        ranking = ranking_chooser.current

        object_list = context["object_list"]
        start_index = object_list.start_index()
        for i, o in enumerate(object_list):
            o.rank = start_index + i
            o.value = ranking.get_value(o)
            o.game = ranking.get_game(o)

        if self.request.user.is_authenticated:
            context["user_rank"] = ranking.get_rank(self.request.user, self.season)
            context["user_rank_url"] = get_ranking_url(
                ranking, self.request.user, self.season
            )

        return context


class StatsView(TemplateView):
    template_name = "stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        season = SeasonChooser(self.request).current

        chooser = PlayerCountChooser(self.request)
        context["player_count_chooser"] = chooser
        player_count = chooser.current

        context |= stats.get_context_data(season, player_count)

        return context


class FailedGameUploadView(CreateView):
    model = FailedGameUpload
    template_name = "failed_game_upload.html"
    form_class = FailedGameUploadForm
    success_url = "/"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.user.is_authenticated:
            form.instance.user = self.request.user
            form.instance.save()
        mail_admins(
            "[academy.beer] Game log uploaded",
            f"""A game has been uploaded to
{get_admin_object_url(form.instance)}
by {self.request.user}.

Notes:
{form.instance.notes}""",
        )
        messages.success(self.request, "Game log successfully uploaded.")
        return response


class GamesFeed(Feed):
    title = "Academy games"
    link = "/games/"
    decription = "Feed for every game of Academy started."

    def items(self) -> Iterable[Game]:
        return Game.objects.all()[:50]

    def item_title(self, item: Game) -> str:
        return str(item)

    def item_description(self, item) -> str:
        return item.game_state_description().replace("\n", "<br>")

    def item_pubdate(self, item: Game) -> datetime.datetime:
        return item.start_datetime

    def item_updateddate(self, item: Game) -> datetime.datetime:
        return item.get_last_activity_time()
