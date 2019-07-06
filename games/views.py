from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import User, Game, Card, Chug
from .serializers import UserSerializer, GameSerializer, CreateGameSerializer, EndGameSerializer, CardSerializer, ChugSerializer


class CustomAuthToken(ObtainAuthToken):
	def post(self, request, *args, **kwargs):
		try:
			response = super().post(request, *args, **kwargs)
			token = Token.objects.get(key=response.data['token'])
			if token.user.image:
				response.data['image'] = token.user.image.url
			return response
		except serializers.ValidationError as e:
			# If username doesn't exist return with code 404,
			# else code 400
			non_field_errors = e.detail.get('non_field_errors', [])
			if 'Unable to log in with provided credentials.' in non_field_errors:
				username = request.data['username']
				if not User.objects.filter(username=username).exists():
					e.status_code = 404
			raise


class CreateOrAuthenticated(IsAuthenticatedOrReadOnly):
	def has_permission(self, request, view):
		if request.method in ['OPTIONS','POST']:
			return True

		return super().has_permission(request, view)


class ShouldDrawNext(IsAuthenticatedOrReadOnly):
	def has_object_permission(self, request, view, game):
		if request.method == 'POST':
			return game.get_state() == Game.State.WAITING_FOR_DRAW and \
			       request.user == game.next_player_to_draw()

		return False


class ShouldRegisterChug(IsAuthenticatedOrReadOnly):
	def has_object_permission(self, request, view, game):
		if request.method == 'POST':
			return game.get_state() == Game.State.WAITING_FOR_CHUG and \
			       request.user == game.current_player_to_chug()

		return False


class PartOfGame(IsAuthenticatedOrReadOnly):
	def has_object_permission(self, request, view, game):
		if request.method == 'POST':
			return request.user in game.players.all()

		return False


class UserViewSet(viewsets.ModelViewSet):
	queryset = User.objects.all()
	serializer_class = UserSerializer
	permission_classes = (CreateOrAuthenticated,)


class GameViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Game.objects.all()
	serializer_class = GameSerializer
	permission_classes = (CreateOrAuthenticated,)


	def create(self, request):
		serializer = CreateGameSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		game = serializer.save()
		return Response(GameSerializer(game).data)


	@action(detail=True, methods=['post'], permission_classes=[ShouldDrawNext])
	def draw_card(self, request, pk=None):
		game = Game.objects.get(id=pk)
		self.check_object_permissions(request, game)

		card = game.draw_card()
		return Response(CardSerializer(card).data)


	@action(detail=True, methods=['post'], permission_classes=[ShouldRegisterChug])
	def register_chug(self, request, pk=None):
		game = Game.objects.get(id=pk)
		self.check_object_permissions(request, game)

		serializer = ChugSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		game.add_chug(serializer.data['duration_in_milliseconds'])
		return Response(serializer.data)


	@action(detail=True, methods=['post'], permission_classes=[PartOfGame])
	def end_game(self, request, pk=None):
		game = Game.objects.get(id=pk)
		self.check_object_permissions(request, game)

		serializer = EndGameSerializer(game, data=request.data)
		serializer.is_valid(raise_exception=True)
		serializer.save()

		return Response(serializer.data)


class CardViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Card.objects.all()
	serializer_class = CardSerializer


class ChugViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Chug.objects.all()
	serializer_class = ChugSerializer
