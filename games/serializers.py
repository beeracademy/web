from rest_framework import serializers
#from rest_framework import generics
from rest_framework.authtoken.models import Token
from .models import User, Game, Card, Chug


class UserSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ['id', 'username', 'is_superuser', 'image', 'password']
		extra_kwargs = {
			'password': {'write_only': True}
		}


	def create(self, validated_data):
		user = User(username=validated_data['username'])
		user.set_password(validated_data['password'])
		user.save()
		return user


class GameSerializer(serializers.ModelSerializer):
	class Meta:
		model = Game
		fields = '__all__'


class CreateGameSerializer(serializers.Serializer):
	tokens = serializers.ListField(
		child=serializers.CharField(),
		min_length=2,
		max_length=6,
	)


	def validate_tokens(self, value):
		users = []
		for key in value:
			try:
				token = Token.objects.get(key=key)
				user = token.user
				if user in users:
					raise serializers.ValidationError(f'Same user logged in multiple times: {user.username}')

				users.append(user)
			except Token.DoesNotExist:
				raise serializers.ValidationError(f'User with token not found: {key}')

		return users


	def create(self, validated_data):
		game = Game.objects.create()
		for user in validated_data['tokens']:
			game.players.add(user)

		game.save()
		return game


class EndGameSerializer(serializers.ModelSerializer):
	end_datetime = serializers.DateTimeField()

	class Meta:
		model = Game
		fields = '__all__'
		read_only_fields = ['players', 'start_datetime', 'sips_per_beer', 'official']


	def validate(self, data):
		game = self.instance
		state = game.get_state()
		if state == Game.State.WAITING_FOR_END:
			return data

		if state == Game.State.ENDED:
			raise serializers.ValidationError('Game already ended.')

		card_count = game.cards.count()
		expected_card_count = game.get_total_card_count()

		chug_count = len((game.ordered_chugs()))
		expected_chug_count = game.players.count()

		raise serializers.ValidationError(f'Game is in a wrong state to end: {card_count}/{expected_card_count} cards drawn, {chug_count}/{expected_chug_count} aces chugged.')


class CardSerializer(serializers.ModelSerializer):
	class Meta:
		model = Card
		fields = '__all__'
		read_only_fields = ['value', 'suit', 'drawn_datetime']


class ChugSerializer(serializers.ModelSerializer):
	class Meta:
		model = Chug
		fields = '__all__'
		read_only_fields = ['card']


	def validate_duration_in_milliseconds(self, value):
		if value < 0:
			raise serializers.ValidationError('Duration must be positive.')

		return value
