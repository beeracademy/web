from django.urls import path
import web.views as views


urlpatterns = [
    path("", views.index),
    path("about/", views.about),
    path("games/", views.GameListView.as_view()),
    path("games/<int:pk>/", views.GameDetailView.as_view()),
    path("players/", views.PlayerListView.as_view()),
    path("players/<int:pk>/", views.PlayerDetailView.as_view()),
    path("ranking/", views.RankingView.as_view()),
    path("settings/", views.UserSettingsView.as_view()),
    path("login/", views.MyLoginView.as_view()),
    path("logout/", views.MyLogoutView.as_view()),
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
