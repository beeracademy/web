from django.urls import path
import web.views as views


urlpatterns = [
    path("", views.index),
    path("games/", views.GameListView.as_view()),
    path("games/<int:pk>/", views.GameDetailView.as_view()),
    path("players/", views.PlayerListView.as_view()),
    path("players/<int:pk>/", views.PlayerDetailView.as_view()),
    path("ranking/", views.RankingView.as_view()),
    path("login/", views.MyLoginView.as_view()),
    path("logout/", views.MyLogoutView.as_view()),
]
