from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from .models import User, Game, Card, Chug, PlayerStat
from .serializers import UserSerializer, GameSerializer, CreateGameSerializer


class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            token = Token.objects.get(key=response.data["token"])
            user = token.user
            response.data["id"] = user.id
            response.data["image"] = user.image_url()
            return response
        except serializers.ValidationError as e:
            # If username doesn't exist return with code 404,
            # else code 400
            non_field_errors = e.detail.get("non_field_errors", [])
            if "Unable to log in with provided credentials." in non_field_errors:
                username = request.data["username"]
                if not User.objects.filter(username=username).exists():
                    e.status_code = 404
            raise


class CreateOrAuthenticated(IsAuthenticatedOrReadOnly):
    def has_permission(self, request, view):
        if request.method in ["OPTIONS", "POST"]:
            return True

        return super().has_permission(request, view)


class PartOfGame(IsAuthenticatedOrReadOnly):
    def has_object_permission(self, request, view, game):
        if request.method == "POST":
            return request.user in game.players.all()

        return False


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (CreateOrAuthenticated,)


def update_game(game, data):
    def update_field(key):
        if key in data:
            setattr(game, key, data[key])

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
        chug_data = last_card_data.get("chug", {}).get("duration_in_milliseconds")
        if chug_data and not hasattr(last_card, "chug"):
            Chug.objects.create(card=last_card, duration_in_milliseconds=chug_data)

    for i, card_data in enumerate(new_cards[previous_cards:]):
        card = Card.objects.create(
            game=game,
            value=card_data["value"],
            suit=card_data["suit"],
            drawn_datetime=card_data["drawn_datetime"],
            index=previous_cards + i,
        )

        chug_data = card_data.get("chug", {}).get("duration_in_milliseconds")
        if chug_data:
            Chug.objects.create(card=card, duration_in_milliseconds=chug_data)

    game.save()


class OneResultSetPagination(PageNumberPagination):
    page_size = 1
    max_page_size = 1


class GameViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    permission_classes = (CreateOrAuthenticated,)
    pagination_class = OneResultSetPagination

    def create(self, request):
        serializer = CreateGameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        game = serializer.save()
        return Response(self.serializer_class(game).data)

    @action(detail=True, methods=["post"], permission_classes=[PartOfGame])
    def update_state(self, request, pk=None):
        game = Game.objects.get(id=pk)
        self.check_object_permissions(request, game)

        serializer = GameSerializer(game, data=request.data)
        serializer.is_valid(raise_exception=True)

        update_game(game, serializer.validated_data)

        if game.has_ended and game.official:
            PlayerStat.update_on_game_finished(game)

        return Response({})
