from django.urls import path

import web.views as views

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("games/", views.GameListView.as_view(), name="game_list"),
    path("games/rss/", views.GamesFeed(), name="games_feed"),
    path("games/<int:pk>/", views.GameDetailView.as_view(), name="game_detail"),
    path("upload_game/", views.FailedGameUploadView.as_view(), name="upload_game"),
    path("players/", views.PlayerListView.as_view(), name="player_list"),
    path("players/<int:pk>/", views.PlayerDetailView.as_view(), name="player_detail"),
    path("ranking/", views.RankingView.as_view(), name="ranking"),
    path("settings/", views.UserSettingsView.as_view(), name="settings"),
    path("stats/", views.StatsView.as_view(), name="stats"),
    path("login/", views.MyLoginView.as_view(), name="login"),
    path("logout/", views.MyLogoutView.as_view(), name="logout"),
    path(
        "login/password_reset/",
        views.MyPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "login/password_reset/done/",
        views.MyPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "login/password_reset/<uidb64>/<token>/",
        views.MyPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "login/password_reset/complete/",
        views.MyPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
