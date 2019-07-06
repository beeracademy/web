from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
import bcrypt
import secrets
import datetime
from enum import Enum, auto


class CaseInsensitiveUserManager(UserManager):
	def get_by_natural_key(self, username):
		return self.get(**{f'{self.model.USERNAME_FIELD}__iexact': username})


def get_user_image_path(self, filename):
	return f'user_images/{self.id}.jpg'


class User(AbstractUser):
	objects = CaseInsensitiveUserManager()

	email = models.EmailField(blank=True)
	image = models.ImageField(upload_to=get_user_image_path, blank=True, null=True)
	old_password_hash = models.CharField(max_length=60, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)


	def set_password(self, raw_password):
		self.old_password_hash = ''
		super().set_password(raw_password)


	def check_password(self, raw_password):
		if self.old_password_hash:
			if bcrypt.checkpw(bytes(raw_password, 'utf-8'), bytes(self.old_password_hash, 'ascii')):
				self.set_password(raw_password)
				self.save()
				return True
			else:
				return False

		return super().check_password(raw_password)


class Game(models.Model):
	class State(Enum):
		WAITING_FOR_DRAW = auto()
		WAITING_FOR_CHUG = auto()
		WAITING_FOR_END = auto()
		ENDED = auto()


	players = models.ManyToManyField(User, through='GamePlayer')
	start_datetime = models.DateTimeField(auto_now_add=True)
	end_datetime = models.DateTimeField(blank=True, null=True)
	sips_per_beer = models.PositiveSmallIntegerField(default=14)
	description = models.CharField(max_length=1000, blank=True)
	official = models.BooleanField(default=True)


	def __str__(self):
		return f'{self.start_datetime}: {self.players_str()}'


	def ordered_players(self):
		return [p.user for p in self.gameplayer_set.all()]


	def next_player_to_draw(self):
		return self.ordered_players()[self.cards.count() % self.players.count()]


	def current_player_to_chug(self):
		card = self.cards.last()
		if card and card.value == 14 and not hasattr(card, 'chug'):
			return card.get_user()

		return None


	def get_state(self):
		if self.end_datetime:
			return self.State.ENDED

		if self.current_player_to_chug():
			return self.State.WAITING_FOR_CHUG

		if self.cards.count() == self.get_total_card_count():
			return self.State.WAITING_FOR_END

		return self.State.WAITING_FOR_DRAW


	def players_str(self):
		return ', '.join(p.username for p in self.ordered_players())


	def ordered_cards(self):
		return self.cards.all()


	def ordered_chugs(self):
		return (c.chug for c in self.cards.filter(chug__isnull=False))


	def get_total_card_count(self):
		return self.players.count() * len(Card.VALUES)


	def get_all_cards(self):
		for suit, _ in Card.SUITS[:self.players.count()]:
			for value, _ in Card.VALUES:
				yield value, suit


	def cards_left(self):
		all_cards = set(self.get_all_cards())
		for card_object in self.cards.all():
			card = card_object.value, card_object.suit
			assert card in all_cards

			all_cards.remove(card)

		return all_cards


	def draw_card(self):
		assert self.get_state() == self.State.WAITING_FOR_DRAW

		value, suit = secrets.choice(list(self.cards_left()))
		return Card.objects.create(
			game=self,
			value=value,
			suit=suit,
		)


	def add_chug(self, duration_in_milliseconds):
		assert self.get_state() == self.State.WAITING_FOR_CHUG

		newest_card = self.cards.last()
		assert newest_card.value == 14

		return Chug.objects.create(
			card=newest_card,
			duration_in_milliseconds=duration_in_milliseconds,
		)


class GamePlayer(models.Model):
	class Meta:
		ordering = ('id',)


	game = models.ForeignKey(Game, on_delete=models.CASCADE)
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	dnf = models.BooleanField(default=False)


class Card(models.Model):
	class Meta:
		unique_together = [('game', 'value', 'suit')]
		ordering = ('id',)


	VALUES = [
		*zip(range(2, 11), range(2, 11)),
		(11, 'J'),
		(12, 'Q'),
		(13, 'K'),
		(14, 'A'),
	]

	SUITS = [
		('S', 'Spades'),
		('C', 'Clubs'),
		('H', 'Hearts'),
		('D', 'Diamonds'),
		('A', 'Carls'),
		('I', 'Heineken'),
	]

	game = models.ForeignKey('Game', on_delete=models.CASCADE, related_name='cards')
	value = models.SmallIntegerField(choices=VALUES)
	suit = models.CharField(max_length=1, choices=SUITS)
	drawn_datetime = models.DateTimeField(auto_now_add=True)


	def __str__(self):
		return f'{self.value} {self.suit}'


	def get_index(self):
		return Card.objects.filter(game=self.game, id__lt=self.id).count()


	def get_user(self):
		i = self.get_index()
		return self.game.ordered_players()[i % self.game.players.count()]


class Chug(models.Model):
	card = models.OneToOneField('Card', on_delete=models.CASCADE, related_name='chug')
	duration_in_milliseconds = models.PositiveIntegerField()


	def duration_str(self):
		td = datetime.timedelta(milliseconds=self.duration_in_milliseconds)
		return str(td)


	def __str__(self):
		return f'{self.card.get_user()}: {self.card} ({self.duration_str()})'
