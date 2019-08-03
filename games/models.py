from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.utils import timezone
import bcrypt
import secrets
import datetime
from enum import Enum, auto
from operator import itemgetter


class CaseInsensitiveUserManager(UserManager):
    def get_by_natural_key(self, username):
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})


def get_user_image_path(self, filename):
    return f"user_images/{self.id}.jpg"


class User(AbstractUser):
    objects = CaseInsensitiveUserManager()

    class Meta:
        ordering = ("username",)

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

    def total_game_count(self):
        return self.gameplayer_set.count()

    def current_season_game_count(self):
        season = Season.current_season()
        return self.gameplayer_set.filter(
            game__start_datetime__gte=season.start_date,
            game__end_datetime__isnull=False,
        ).count()

    def stats_for_season(self, season):
        games = self.gameplayer_set.filter(
            game__start_datetime__gte=season.start_date,
            game__end_datetime__lte=season.end_date,
        )

        stats = {}
        stats["total_games"] = games.count()
        stats["total_time_played"] = datetime.timedelta()
        stats["total_sips"] = 0
        stats["total_chugs"] = 0
        best_game = (-float("inf"), None)
        worst_game = (float("inf"), None)
        fastest_chug = None
        total_chug_time = datetime.timedelta()

        for gameplayer in games.all():
            game = gameplayer.game

            if game.get_state() == Game.State.ENDED:
                player_index = game.ordered_players().index(self)
                stats["total_time_played"] += game.get_duration()

                game_sips = 0

                for i, c in enumerate(game.ordered_cards()):
                    if i % game.players.count() == player_index:
                        game_sips += c.value
                        if c.value == 14:
                            chug_time = c.chug.duration
                            stats["total_chugs"] += 1
                            total_chug_time += chug_time
                            if not fastest_chug or chug_time < fastest_chug.duration:
                                fastest_chug = c.chug

                stats["total_sips"] += game_sips

                combined = (game_sips, game)
                best_game = max(best_game, combined, key=itemgetter(0))
                worst_game = min(worst_game, combined, key=itemgetter(0))

        hours_played = stats["total_time_played"].total_seconds() / (60 * 60)
        stats["approx_ects"] = hours_played / 28

        stats["best_game_sips"] = None
        stats["best_game_id"] = None
        stats["worst_game_sips"] = None
        stats["worst_game_id"] = None
        stats["average_game_sips"] = None
        if stats["total_games"] > 0:
            stats["best_game_sips"] = best_game[0]
            stats["best_game_id"] = best_game[1].id
            stats["worst_game_sips"] = worst_game[0]
            stats["worst_game_id"] = worst_game[1].id
            stats["average_game_sips"] = stats["total_sips"] / stats["total_games"]

        stats["fastest_chug_time"] = None
        stats["fastest_chug_game_id"] = None
        stats["average_chug_time"] = None
        if stats["total_chugs"] > 0:
            stats["fastest_chug_time"] = fastest_chug.duration
            stats["fastest_chug_game_id"] = fastest_chug.card.game.id
            stats["average_chug_time"] = total_chug_time / stats["total_chugs"]

        return stats


class Season:
    FIRST_SEASON_START = datetime.date(2013, 1, 1)

    def __init__(self, number):
        self.number = number

    def __str__(self):
        return f"Season {self.number}"

    @property
    def start_date(self):
        extra_half_years = self.number - 1
        date = self.FIRST_SEASON_START
        date = date.replace(year=date.year + extra_half_years // 2)
        if extra_half_years % 2 == 1:
            date = date.replace(month=7)
        return date

    @property
    def end_date(self):
        return Season(self.number + 1).start_date - datetime.timedelta(days=1)

    @classmethod
    def season_from_date(cls, date):
        year_diff = date.year - cls.FIRST_SEASON_START.year
        season_number = year_diff * 2 + 1
        if date.month >= 7:
            season_number += 1

        return Season(season_number)

    @classmethod
    def current_season(cls):
        return cls.season_from_date(datetime.date.today())

    @classmethod
    def is_valid_season_number(cls, number):
        try:
            number = int(number)
        except (ValueError, TypeError):
            return False

        return 1 <= number <= Season.current_season().number


class _AllTimeSeason:
    number = ""
    start_date = Season.FIRST_SEASON_START
    end_date = Season.current_season().end_date

    def __str__(self):
        return "All time"


all_time_season = _AllTimeSeason()


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

        return Season.season_from_date(self.end_datetime)

    def season_number_str(self):
        season = self.get_season()
        if not season:
            return "-"
        return str(season.number)

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

        total_times = [datetime.timedelta()] * n
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

    @property
    def duration(self):
        return datetime.timedelta(milliseconds=self.duration_in_milliseconds)

    def duration_str(self):
        return str(self.duration)

    def card_str(self):
        return "Ace of " + self.card.suit_str()

    def __str__(self):
        return f"{self.card.get_user()}: {self.card} ({self.duration_str()})"
