"""academy URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import debug_toolbar
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from rest_framework import routers

from games.views import (
    CustomAuthToken,
    GameViewSet,
    InfoViewSet,
    PlayerStatViewSet,
    RankedFacecardsView,
    UserViewSet,
)

router = routers.DefaultRouter()
router.register("users", UserViewSet)
router.register("games", GameViewSet)
router.register("ranked_cards", RankedFacecardsView, basename="ranked_cards")
router.register("stats", PlayerStatViewSet, basename="stats")
router.register("info", InfoViewSet, basename="info")


urlpatterns = [
    path("", include("web.urls")),
    path("api/", include(router.urls)),
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api-token-auth/", CustomAuthToken.as_view()),
    path("__debug__/", include(debug_toolbar.urls)),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
