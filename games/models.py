from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.utils import timezone
import bcrypt
import secrets
import datetime
from enum import Enum, auto


class CaseInsensitiveUserManager(UserManager):
    def get_by_natural_key(self, username):
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})


def get_user_image_path(self, filename):
    return f"user_images/{self.id}.jpg"


class User(AbstractUser):
    objects = CaseInsensitiveUserManager()

    email = models.EmailField(blank=True)
    image = models.ImageField(upload_to=get_user_image_path, blank=True, null=True)
    old_password_hash = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_password(self, raw_password):
        self.old_password_hash = ""
        super().set_password(raw_password)

    def check_password(self, raw_password):
        if self.old_password_hash:
            if bcrypt.checkpw(
                bytes(raw_password, "utf-8"), bytes(self.old_password_hash, "ascii")
            ):
                self.set_password(raw_password)
                self.save()
                return True
            else:
                return False

        return super().check_password(raw_password)


FIRST_SEASON_START = datetime.date(2013, 1, 1)


def get_season_from_date(date):
    season = (date.year - FIRST_SEASON_START.year) * 2 + 1
    if date.month >= 7:
        season += 1

    return season


def get_current_season():
    return get_season_from_date(datetime.date.today())


class Game(models.Model):
    TOTAL_ROUNDS = 13

    class Meta:
        ordering = ("-end_datetime",)

    class State(Enum):
        WAITING_FOR_DRAW = auto()
        WAITING_FOR_CHUG = auto()
        WAITING_FOR_END = auto()
        ENDED = auto()

    players = models.ManyToManyField(User, through="GamePlayer")
    start_datetime = models.DateTimeField(default=timezone.now)
    end_datetime = models.DateTimeField(blank=True, null=True)
    sips_per_beer = models.PositiveSmallIntegerField(default=14)
    description = models.CharField(max_length=1000, blank=True)
    official = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.start_datetime}: {self.players_str()}"

    def get_season(self):
        if not self.end_datetime:
            return None

        return get_season_from_date(self.end_datetime)

    def season_str(self):
        return self.get_season() or "-"

    def get_duration(self):
        if not self.end_datetime:
            return None

        return self.end_datetime - self.start_datetime

    def duration_str(self):
        duration = self.get_duration()
        if not duration:
            return "Live"

        return datetime.timedelta(seconds=round(duration.total_seconds()))

    def end_str(self):
        if not self.end_datetime:
            return "-"

        return self.end_datetime.strftime("%B %d, %Y %H:%M")

    def ordered_players(self):
        return [p.user for p in self.gameplayer_set.all()]

    def next_player_to_draw(self):
        return self.ordered_players()[self.cards.count() % self.players.count()]

    def current_player_to_chug(self):
        card = self.cards.last()
        if card and card.value == 14 and not hasattr(card, "chug"):
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
        return ", ".join(p.username for p in self.ordered_players())

    def ordered_cards(self):
        return self.cards.all()

    def cards_by_round(self):
        n = self.players.count()
        cards = self.ordered_cards()
        for i in range(self.TOTAL_ROUNDS):
            round_cards = cards[i * n : (i + 1) * n]
            yield list(round_cards) + [None] * (n - len(round_cards))

    def ordered_chugs(self):
        return (c.chug for c in self.cards.filter(chug__isnull=False))

    def get_total_card_count(self):
        return self.players.count() * len(Card.VALUES)

    def get_all_cards(self):
        for suit, _ in Card.SUITS[: self.players.count()]:
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
        return Card.objects.create(game=self, value=value, suit=suit)

    def add_chug(self, duration_in_milliseconds):
        assert self.get_state() == self.State.WAITING_FOR_CHUG

        newest_card = self.cards.last()
        assert newest_card.value == 14

        return Chug.objects.create(
            card=newest_card, duration_in_milliseconds=duration_in_milliseconds
        )

    def get_turn_durations(self):
        prev_datetime = None
        for c in self.ordered_cards():
            if prev_datetime is not None:
                yield c.drawn_datetime - prev_datetime

            prev_datetime = c.drawn_datetime

        if self.get_state() == self.State.ENDED:
            yield self.end_datetime - prev_datetime

    def get_player_stats(self):
        # Note that toal_drawn and total_done,
        # can differ for one player, if the game hasn't ended.
        def div_or_none(a, b):
            if b == 0:
                return None
            return a / b

        n = self.players.count()
        total_sips = [0] * n
        total_drawn = [0] * n
        last_sip = None
        for i, c in enumerate(self.ordered_cards()):
            total_sips[i % n] += c.value
            total_drawn[i % n] += 1
            last_sip = (i % n, c.value)

        total_times = [datetime.timedelta(0)] * n
        total_done = [0] * n
        for i, dt in enumerate(self.get_turn_durations()):
            total_times[i % n] += dt
            total_done[i % n] += 1

        for i, p in enumerate(self.ordered_players()):
            full_beers = total_sips[i] // self.sips_per_beer
            extra_sips = total_sips[i] % self.sips_per_beer

            if last_sip[0] == i and self.get_state() != self.State.ENDED:
                time_per_sip = div_or_none(
                    total_times[i], (total_sips[i] - last_sip[1])
                )
            else:
                time_per_sip = div_or_none(total_times[i], total_sips[i])

            yield {
                "player": p,
                "total_sips": total_sips[i],
                "sips_per_turn": div_or_none(total_sips[i], total_drawn[i]),
                "full_beers": full_beers,
                "extra_sips": extra_sips,
                "total_time": total_times[i],
                "time_per_turn": div_or_none(total_times[i], total_done[i]),
                "time_per_sip": time_per_sip,
            }


class GamePlayer(models.Model):
    class Meta:
        ordering = ("id",)

    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    dnf = models.BooleanField(default=False)


class Card(models.Model):
    class Meta:
        unique_together = [("game", "value", "suit")]
        ordering = ("id",)

    VALUES = [
        *zip(range(2, 11), map(str, range(2, 11))),
        (11, "Jack"),
        (12, "Queen"),
        (13, "King"),
        (14, "Ace"),
    ]

    SUITS = [
        ("S", "Spades"),
        ("C", "Clubs"),
        ("H", "Hearts"),
        ("D", "Diamonds"),
        ("A", "Carls"),
        ("I", "Heineken"),
    ]

    game = models.ForeignKey("Game", on_delete=models.CASCADE, related_name="cards")
    value = models.SmallIntegerField(choices=VALUES)
    suit = models.CharField(max_length=1, choices=SUITS)
    drawn_datetime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.value} {self.suit}"

    def get_index(self):
        return Card.objects.filter(game=self.game, id__lt=self.id).count()

    def get_user(self):
        i = self.get_index()
        return self.game.ordered_players()[i % self.game.players.count()]

    def value_str(self):
        return dict(self.VALUES)[self.value]

    def suit_str(self):
        return dict(self.SUITS)[self.suit]

    def card_str(self):
        return f"{self.value_str()} of {self.suit_str()}"

    def suit_symbol(self):
        mapping = {"S": "♠", "C": "♣", "H": "♥", "D": "♦", "A": "☘", "I": "🟊"}
        return mapping[self.suit]


class Chug(models.Model):
    card = models.OneToOneField("Card", on_delete=models.CASCADE, related_name="chug")
    duration_in_milliseconds = models.PositiveIntegerField()

    def duration_str(self):
        td = datetime.timedelta(milliseconds=self.duration_in_milliseconds)
        return str(td)

    def card_str(self):
        return "Ace of " + self.card.suit_str()

    def __str__(self):
        return f"{self.card.get_user()}: {self.card} ({self.duration_str()})"
