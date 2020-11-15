from django.db import transaction
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from PIL import Image
from rest_framework import serializers, viewsets
from rest_framework.authentication import BaseAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import (
    Card,
    Chug,
    Game,
    GamePlayer,
    GameToken,
    PlayerStat,
    Season,
    User,
    update_stats_on_game_finished,
)
from .ranking import RANKINGS
from .serializers import (
    CreateGameSerializer,
    GameSerializer,
    GameSerializerWithPlayerStats,
    PlayerStatSerializer,
    UserSerializer,
)
from .tasks import post_game_to_facebook, update_facebook_post


class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            token = Token.objects.get(key=response.data["token"])
            user = token.user
            response.data["id"] = user.id
            response.data["image"] = request.build_absolute_uri(user.image_url())
            return response
        except serializers.ValidationError as e:
            # If username doesn't exist return with code 404,
            # else code 400
            non_field_errors = e.detail.get("non_field_errors", [])
            if "Unable to log in with provided credentials." in non_field_errors:
                username = request.data["username"]
                if not User.objects.filter(username__iexact=username).exists():
                    e.status_code = 404
            raise


class CreateOrAuthenticated(IsAuthenticatedOrReadOnly):
    def has_permission(self, request, view):
        if request.method in ["OPTIONS", "POST"]:
            return True

        return super().has_permission(request, view)


class GameUpdateAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != "GameToken":
            return None

        token_key = parts[1]
        try:
            token = GameToken.objects.get(key=token_key)
            return (None, token.game)
        except GameToken.DoesNotExist:
            raise AuthenticationFailed("No game with that token")


class GameUpdatePermission(BasePermission):
    def has_object_permission(self, request, view, game):
        return request.auth == game


1 + 1


class PartOfGamePermission(BasePermission):
    def has_object_permission(self, request, view, game):
        return request.user in game.players.all()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (CreateOrAuthenticated,)


def update_game(game, data):
    def update_field(key):
        if key in data:
            setattr(game, key, data[key])

    chug_fields = {"chug_start_start_delta_ms", "chug_duration_ms"}

    def update_chug(card, card_data):
        if card.value == 14:
            Chug.objects.update_or_create(
                id=getattr(getattr(card, "chug", None), "id", None),
                defaults={
                    "card": card,
                    **{
                        k[len("chug_") :]: v
                        for k, v in card_data.items()
                        if k in chug_fields
                    },
                },
            )

    game_already_ended = game.has_ended

    if game.players.count() == 0:
        for i, p_id in enumerate(data["player_ids"]):
            GamePlayer.objects.create(
                game=game, user=User.objects.get(id=p_id), position=i
            )

    update_field("start_datetime")
    update_field("end_datetime")
    update_field("official")
    update_field("description")

    cards = game.ordered_cards()
    new_cards = data["cards"]

    last_card = cards.last()
    previous_cards = cards.count()
    if previous_cards > 0:
        last_card_data = new_cards[previous_cards - 1]
        update_chug(last_card, last_card_data)

    for i, card_data in enumerate(new_cards[previous_cards:]):
        card = Card.objects.create(
            game=game,
            value=card_data["value"],
            suit=card_data["suit"],
            start_delta_ms=card_data["start_delta_ms"],
            index=previous_cards + i,
        )

        update_chug(card, card_data)

    dnf_gps = game.gameplayer_set.filter(user_id__in=data["dnf_player_ids"])
    dnf_gps.update(dnf=True)
    game.gameplayer_set.exclude(id__in=dnf_gps).update(dnf=False)

    game.dnf = data["dnf"]

    for k, v in data.items():
        if k.startswith("location_"):
            setattr(game, k, v)

    game.save()

    if game.has_ended and not game_already_ended:
        update_facebook_post.delay(game.id)
        update_stats_on_game_finished(game)


class OneResultSetPagination(PageNumberPagination):
    page_size = 1
    max_page_size = 1


class GameViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    permission_classes = (CreateOrAuthenticated,)
    pagination_class = OneResultSetPagination
    lookup_value_regex = "\\d+"

    def retrieve(self, request, pk=None):
        game = self.get_object()
        return Response(GameSerializerWithPlayerStats(game).data)

    def create(self, request):
        serializer = CreateGameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        game = serializer.save()

        post_game_to_facebook.delay(
            game.id, request.build_absolute_uri(game.get_absolute_url())
        )

        token = GameToken.objects.create(game=game)
        return Response({**self.serializer_class(game).data, "token": token.key})

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[PartOfGamePermission],
    )
    def resume(self, request, pk=None):
        game = self.get_object()

        if game.has_ended:
            return HttpResponseBadRequest("Game has ended")

        game_token = GameToken.objects.get(game=game)
        return Response({**self.serializer_class(game).data, "token": game_token.key})

    @transaction.atomic()
    @action(
        detail=True,
        methods=["post"],
        authentication_classes=[GameUpdateAuthentication],
        permission_classes=[GameUpdatePermission],
    )
    def update_state(self, request, pk=None):
        game = self.get_object()

        # Lock game object
        # Note: Doesn't do anything when using SQLite
        Game.objects.select_for_update().get(id=pk)

        self.check_object_permissions(request, game)
        serializer = GameSerializer(game, data=request.data)
        serializer.is_valid(raise_exception=True)
        update_game(game, serializer.validated_data)
        return Response({})

    @action(
        detail=True,
        methods=["post"],
        authentication_classes=[GameUpdateAuthentication],
        permission_classes=[GameUpdatePermission],
        parser_classes=[MultiPartParser],
    )
    def update_image(self, request, pk=None):
        game = self.get_object()

        f = request.data.get("image")
        if not f:
            return HttpResponseBadRequest("image file is missing")

        try:
            image = Image.open(f)
            image.verify()
        except Exception as e:
            print(e)
            return HttpResponseBadRequest("image is not valid")

        game.image.save(None, f)

        return Response({})

    @action(
        detail=True,
        methods=["post"],
        authentication_classes=[GameUpdateAuthentication],
        permission_classes=[GameUpdatePermission],
    )
    def delete_image(self, request, pk=None):
        game = self.get_object()

        game.image.delete()

        return Response({})

    @action(detail=False, methods=["get"], permission_classes=[])
    def live_games(self, request):
        return Response(
            Game.objects.filter(end_datetime__isnull=True, dnf=False).values("id")
        )


class RankedFacecardsView(viewsets.ViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def list(self, request):
        season = Season.current_season()

        facecards = {}
        for ranking, (suit, _) in zip(RANKINGS, Card.SUITS):
            qs = ranking.get_qs(season)

            for ps, value in zip(
                qs.exclude(user__image="")[: len(Card.FACE_CARD_VALUES)],
                Card.FACE_CARD_VALUES,
            ):
                user = ps.user
                facecards[f"{suit}-{value}"] = {
                    "user_id": user.id,
                    "user_username": user.username,
                    "user_image": user.image_url(),
                    "ranking_name": ranking.name,
                    "ranking_value": ranking.get_value(ps),
                }

        return Response(facecards)


class PlayerStatViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    lookup_value_regex = "\\d+"

    def retrieve(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        stats = PlayerStat.objects.filter(user=user)
        serializer = PlayerStatSerializer(stats, many=True)
        return Response(serializer.data)


class InfoViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def list(self, request):
        return Response(
            {
                "datetime": timezone.now(),
            }
        )
