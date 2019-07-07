from django.shortcuts import render
from django.db.models import F
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.core.paginator import Paginator
from games.models import Game


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
        context["object_list"] = paginator.get_page(page)
        return context


class GamesView(PaginatedListView):
    model = Game
    template_name = "game_list.html"

    def get_queryset(self):
        return Game.objects.all().order_by(F("end_datetime").desc(nulls_first=True))


class GameDetailView(DetailView):
    model = Game
    template_name = "game_detail.html"
