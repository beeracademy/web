import datetime
import os
import secrets

import pytz
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import Count, DurationField, ExpressionWrapper, F, Q, Subquery
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from PIL import Image
from tqdm import tqdm

from .seed import shuffle_with_seed


class CaseInsensitiveUserManager(UserManager):
    def get_by_natural_key(self, username):
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})


def get_user_image_name(user, filename=None):
    return f"user_images/{user.id}.png"


def q_between(key, lower, upper):
    return Q(**{f"{key}__gte": lower, f"{key}__lte": upper})


def filter_season(qs, season, key=None, should_include_live=False):
    if key:
        key += "__"
    else:
        key = ""

    end_key = key + "end_datetime"

    q = q_between(end_key, season.start_datetime, season.end_datetime)
    q |= Q(**{f"{key}dnf": True}) & q_between(
        f"{key}start_datetime", season.start_datetime, season.end_datetime
    )

    includes_live = season == all_time_season or Season.current_season() == season
    if includes_live and should_include_live:
        q |= Q(**{f"{end_key}__isnull": True, f"{key}dnf": False})

    return qs.filter(q)


def filter_player_count(qs, player_count, key=None):
    if player_count == None:
        return qs

    if key:
        key += "__"
    else:
        key = ""

    gameplayer_key = key + "gameplayer"

    return qs.annotate(player_count=Count(gameplayer_key)).filter(
        player_count=player_count
    )


def filter_season_and_player_count(qs, season, player_count, key=None):
    return filter_player_count(filter_season(qs, season, key), player_count, key)


def recalculate_all_stats():
    PlayerStat.recalculate_all()
    GamePlayerStat.recalculate_all()


def update_stats_on_game_finished(game):
    PlayerStat.update_on_game_finished(game)
    GamePlayerStat.update_on_game_finished(game)


class GamePlayerStat(models.Model):
    gameplayer = models.OneToOneField("GamePlayer", on_delete=models.CASCADE)
    value_sum = models.PositiveIntegerField(default=0)
    chugs = models.PositiveIntegerField(default=0)

    @classmethod
    def recalculate_all(cls):
        GamePlayerStat.objects.all().delete()
        for game in tqdm(Game.objects.all()):
            cls.update_on_game_finished(game)

    @classmethod
    def update_on_game_finished(cls, game):
        if not game.is_completed:
            return

        stats = [
            GamePlayerStat.objects.get_or_create(gameplayer=gp)[0]
            for gp in game.ordered_gameplayers()
        ]

        for round_cards in game.cards_by_round():
            for i, c in enumerate(round_cards):
                stats[i].value_sum += c.value
                stats[i].chugs += c.value == Chug.VALUE

        for s in stats:
            s.save()

    @classmethod
    def get_stats_with_player_count(cls, season, player_count):
        return filter_season_and_player_count(
            cls.objects, season, player_count, "gameplayer__game"
        )

    @classmethod
    def get_distribution(cls, field, season, player_count):
        sq = Subquery(
            cls.get_stats_with_player_count(season, player_count).values("id")
        )
        return (
            GamePlayerStat.objects.filter(id__in=sq)
            .values(value=F(field))
            .annotate(Count("value"))
            .order_by(field)
        )

    @classmethod
    def get_sips_distribution(cls, season, player_count):
        return cls.get_distribution("value_sum", season, player_count)

    @classmethod
    def get_chugs_distribution(cls, season, player_count):
        return cls.get_distribution("chugs", season, player_count)


class PlayerStat(models.Model):
    class Meta:
        unique_together = [("user", "season_number")]

    user = models.ForeignKey("User", on_delete=models.CASCADE)
    season_number = models.PositiveIntegerField()

    total_games = models.PositiveIntegerField(default=0)
    total_time_played_seconds = models.FloatField(default=0)

    total_sips = models.PositiveIntegerField(default=0)

    best_game = models.ForeignKey(
        "Game", on_delete=models.CASCADE, null=True, related_name="+"
    )
    worst_game = models.ForeignKey(
        "Game", on_delete=models.CASCADE, null=True, related_name="+"
    )
    best_game_sips = models.PositiveIntegerField(null=True)
    worst_game_sips = models.PositiveIntegerField(null=True)

    total_chugs = models.PositiveIntegerField(default=0)

    fastest_chug = models.ForeignKey(
        "Chug", on_delete=models.CASCADE, null=True, related_name="+"
    )

    average_chug_time_seconds = models.FloatField(null=True)

    @classmethod
    def update_on_game_finished(cls, game):
        season = game.get_season()
        for s in [season, all_time_season]:
            for player in game.players.all():
                ps, _ = PlayerStat.objects.get_or_create(
                    user=player, season_number=s.number
                )
                ps.update_from_new_game(game)

    @classmethod
    def recalculate_all(cls):
        for season_number in tqdm(range(Season.current_season().number + 1)):
            cls.recalculate_season(Season(season_number))

    @classmethod
    def recalculate_season(cls, season):
        for user in tqdm(User.objects.all()):
            ps, _ = PlayerStat.objects.get_or_create(
                user=user, season_number=season.number
            )
            ps.recalculate()

    @classmethod
    def recalculate_user(cls, user):
        for season_number in tqdm(range(Season.current_season().number + 1)):
            ps, _ = PlayerStat.objects.get_or_create(
                user=user, season_number=season_number
            )
            ps.recalculate()

    def recalculate(self):
        for f in self._meta.fields:
            if f.default != models.fields.NOT_PROVIDED:
                setattr(self, f.name, f.default)
            elif f.null:
                setattr(self, f.name, None)

        gameplayers = filter_season(
            self.user.gameplayer_set, self.season, key="game"
        ).filter(game__official=True, game__dnf=False)

        for gp in gameplayers:
            self.update_from_new_game(gp.game)

    def update_from_new_game(self, game):
        if not game.official or game.dnf:
            return

        gp = game.gameplayer_set.get(user=self.user)
        if gp.dnf:
            return

        self.total_games += 1

        player_index = gp.position
        duration = game.get_duration()
        if duration:
            self.total_time_played_seconds += duration.total_seconds()

        if self.average_chug_time_seconds:
            total_chug_time = self.total_chugs * self.average_chug_time_seconds
        else:
            total_chug_time = 0
        game_sips = 0
        for i, c in enumerate(game.ordered_cards()):
            if i % game.players.count() == player_index:
                game_sips += c.value
                if hasattr(c, "chug"):
                    self.total_chugs += 1
                    chug_time = c.chug.duration
                    if chug_time:
                        total_chug_time += chug_time.total_seconds()
                        if (
                            not self.fastest_chug
                            or chug_time < self.fastest_chug.duration
                        ):
                            self.fastest_chug = c.chug

        self.total_sips += game_sips

        if not self.best_game or game_sips > self.best_game_sips:
            self.best_game = game
            self.best_game_sips = game_sips

        if not self.worst_game or game_sips < self.worst_game_sips:
            self.worst_game = game
            self.worst_game_sips = game_sips

        if self.total_chugs > 0:
            self.average_chug_time_seconds = total_chug_time / self.total_chugs

        self.save()

    @property
    def season(self):
        if self.season_number == 0:
            return all_time_season
        return Season(self.season_number)

    @property
    def total_time_played(self):
        return datetime.timedelta(seconds=self.total_time_played_seconds)

    @property
    def total_beers(self):
        return self.total_sips / Game.STANDARD_SIPS_PER_BEER

    @property
    def approx_ects(self):
        HOURS_PER_ECTS = 28
        hours_played = self.total_time_played_seconds / (60 * 60)
        return hours_played / HOURS_PER_ECTS

    @property
    def approx_money_spent_tk(self):
        AVERAGE_BEER_PRICE_DKK = 250 / 30
        cost = self.total_beers * AVERAGE_BEER_PRICE_DKK
        return f"{int(cost)} DKK"

    @property
    def approx_money_spent_føtex(self):
        AVERAGE_BEER_PRICE_DKK = 105 / 30  # Klaus' estimate
        cost = self.total_beers * AVERAGE_BEER_PRICE_DKK
        return f"{int(cost)} DKK"

    @property
    def average_game_sips(self):
        if self.total_games == 0:
            return None
        return round(self.total_sips / self.total_games, 1)

    @property
    def average_chug_time(self):
        if not self.average_chug_time_seconds:
            return None
        return datetime.timedelta(seconds=self.average_chug_time_seconds)


class User(AbstractUser):
    IMAGE_SIZE = (156, 262)

    objects = CaseInsensitiveUserManager()

    class Meta:
        ordering = ("username",)

    email = models.EmailField(blank=True)
    image = models.ImageField(upload_to=get_user_image_name, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save()

        # Ensure that the image file is always saved
        # at the location governed by get_user_image_name
        # and deleted when the image is removed.
        expected_image_name = get_user_image_name(self)
        expected_image_path = self.image.storage.path(expected_image_name)
        if self.image:
            if self.image.path != expected_image_path:
                os.rename(self.image.path, expected_image_path)
                self.image.name = expected_image_name
                super().save()

            try:
                image = Image.open(expected_image_path)
                thumb = image.resize(self.IMAGE_SIZE)
                thumb.save(expected_image_path)
            except FileNotFoundError:
                pass
        else:
            try:
                os.remove(expected_image_path)
            except FileNotFoundError:
                pass

    def total_game_count(self):
        return self.gameplayer_set.count()

    def current_season_game_count(self):
        season = Season.current_season()
        return filter_season(self.gameplayer_set, season, key="game").count()

    def stats_for_season(self, season):
        return PlayerStat.objects.get_or_create(user=self, season_number=season.number)[
            0
        ]

    def image_url(self):
        if self.image:
            return self.image.url
        else:
            return static("user.png")

    def get_absolute_url(self):
        return reverse("player_detail", args=[self.id])

    def merge_with(self, other_user):
        other_user.gameplayer_set.update(user_id=self)
        other_user.delete()
        PlayerStat.recalculate_user(self)


class OneTimePassword(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    password = models.CharField(max_length=20)

    @classmethod
    def check_password(cls, username, password):
        try:
            user = User.objects.get(username__iexact=username)
            obj = cls.objects.get(user=user, password=password)
            obj.password = None
            obj.save()
            return True
        except (User.DoesNotExist, cls.DoesNotExist):
            pass

        return False

    def save(self, *args, **kwargs):
        if not self.password:
            self.password = secrets.token_hex(10)
        return super().save(*args, **kwargs)


class Season:
    FIRST_SEASON_START = datetime.date(2013, 1, 1)

    def __init__(self, number):
        self.number = number

    def __str__(self):
        return f"Season {self.number}"

    def __eq__(self, other):
        return self.number == other.number

    def __neq__(self, other):
        return self.number != other.number

    @property
    def start_datetime(self):
        extra_half_years = self.number - 1
        date = self.FIRST_SEASON_START
        date = date.replace(year=date.year + extra_half_years // 2)
        if extra_half_years % 2 == 1:
            date = date.replace(month=7)

        return pytz.utc.localize(datetime.datetime(date.year, date.month, date.day))

    @property
    def end_datetime(self):
        return Season(self.number + 1).start_datetime - datetime.timedelta(
            microseconds=1
        )

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
    number = 0
    start_datetime = Season(1).start_datetime

    @property
    def end_datetime(self):
        return Season.current_season().end_datetime

    def __str__(self):
        return "All time"


all_time_season = _AllTimeSeason()


class Game(models.Model):
    TOTAL_ROUNDS = 13
    STANDARD_SIPS_PER_BEER = 14

    class Meta:
        ordering = ("-end_datetime",)

    """
    Game data updates:
    - 2013-02-01: First version (example: 119)
    - 2014-04-09: Introduced start_datetime and thus game durations (example: 279)
    - 2015-07-02: Introduced individual times for cards (example: 1800)
    - 2019-08-29: Introduced dnf games, thus finished games are no longer those with no end_datetime (example: 2240)
        - However note that either start_datetime or end_datetime always exists for a game
    - 2020-04-23: Introduced start times for chugs, which gives a better turn time (example: N/A)
    """

    players = models.ManyToManyField(User, through="GamePlayer", related_name="games")
    start_datetime = models.DateTimeField(blank=True, null=True, default=timezone.now)
    end_datetime = models.DateTimeField(blank=True, null=True)
    sips_per_beer = models.PositiveSmallIntegerField(default=STANDARD_SIPS_PER_BEER)
    description = models.CharField(max_length=1000, blank=True)
    official = models.BooleanField(default=True)
    dnf = models.BooleanField(default=False)
    location_latitude = models.FloatField(null=True, blank=True)
    location_longitude = models.FloatField(null=True, blank=True)
    location_accuracy = models.FloatField(null=True, blank=True)

    @staticmethod
    def add_durations(qs):
        return qs.annotate(
            duration=ExpressionWrapper(
                F("end_datetime") - F("start_datetime"), DurationField()
            )
        )

    def __str__(self):
        return f"{self.datetime}: {self.players_str()}"

    @property
    def is_completed(self):
        return self.end_datetime is not None

    @property
    def has_ended(self):
        return self.is_completed or self.dnf

    @property
    def is_live(self):
        return not self.is_completed and not self.dnf

    @property
    def datetime(self):
        return self.end_datetime or self.start_datetime

    @property
    def date(self):
        return self.datetime.date()

    def get_last_activity_time(self):
        if self.end_datetime:
            return self.end_datetime

        cards = self.ordered_cards()
        if len(cards) > 0:
            return cards.last().drawn_datetime

        return self.start_datetime

    def get_season(self):
        if not self.has_ended:
            return None

        return Season.season_from_date(self.get_last_activity_time())

    def season_number_str(self):
        season = self.get_season()
        if not season:
            return "-"
        return str(season.number)

    def get_duration(self):
        if self.dnf:
            return self.get_last_activity_time() - self.start_datetime

        if not (self.start_datetime and self.end_datetime):
            return None

        return self.end_datetime - self.start_datetime

    def duration_str(self):
        if not self.start_datetime:
            return "?"

        duration = self.get_duration()
        if duration == None:
            duration = timezone.now() - self.start_datetime

        return datetime.timedelta(seconds=round(duration.total_seconds()))

    def end_str(self):
        if self.dnf:
            return "DNF"

        if not self.end_datetime:
            return "Live"

        return timezone.localtime(self.end_datetime).strftime("%B %d, %Y %H:%M")

    def ordered_gameplayers(self):
        return self.gameplayer_set.order_by("position")

    def ordered_players(self):
        return [p.user for p in self.ordered_gameplayers()]

    def players_str(self):
        return ", ".join(p.username for p in self.ordered_players())

    def ordered_cards(self):
        return self.cards.order_by("index")

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

    def get_turn_durations(self):
        prev_finish_start_delta_ms = 0
        for c in self.ordered_cards():
            if c.finish_start_delta_ms is None:
                return

            if prev_finish_start_delta_ms is not None:
                yield c.finish_start_delta_ms - prev_finish_start_delta_ms

            prev_finish_start_delta_ms = c.finish_start_delta_ms

    def get_player_stats(self):
        # Note that toal_drawn and total_done,
        # can differ for one player, if the game hasn't ended.
        def div_or_none(a, b):
            if a is None or not b:
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

        first_card = self.ordered_cards().first()
        if first_card and first_card.start_delta_ms:
            total_times = [0] * n
            total_done = [0] * n
            for i, dt in enumerate(self.get_turn_durations()):
                total_times[i % n] += dt
                total_done[i % n] += 1
        else:
            total_times = [None] * n
            total_done = [None] * n

        ordered_players = self.ordered_players()
        for i in range(n):
            full_beers = total_sips[i] // self.sips_per_beer
            extra_sips = total_sips[i] % self.sips_per_beer

            if not self.start_datetime:
                time_per_sip = None
            elif last_sip and last_sip[0] == i and not self.is_completed:
                time_per_sip = div_or_none(
                    total_times[i], (total_sips[i] - last_sip[1])
                )
            else:
                time_per_sip = div_or_none(total_times[i], total_sips[i])

            yield {
                "id": ordered_players[i].id,
                "username": ordered_players[i].username,
                "total_sips": total_sips[i],
                "sips_per_turn": div_or_none(total_sips[i], total_drawn[i]),
                "full_beers": full_beers,
                "extra_sips": extra_sips,
                "total_time": total_times[i],
                "time_per_turn": div_or_none(total_times[i], total_done[i]),
                "time_per_sip": time_per_sip,
            }

    def get_absolute_url(self):
        return reverse("game_detail", args=[self.id])


class GameToken(models.Model):
    key = models.CharField(max_length=40, unique=True)
    game = models.OneToOneField(Game, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    def generate_key(self):
        return secrets.token_hex(20)


class GamePlayer(models.Model):
    class Meta:
        unique_together = [("game", "user", "position")]
        ordering = ("position",)

    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField()
    dnf = models.BooleanField(default=False)


class Card(models.Model):
    class Meta:
        unique_together = [("game", "value", "suit"), ("game", "index")]
        ordering = ("index",)

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

    FACE_CARD_VALUES = [13, 12, 11]

    game = models.ForeignKey("Game", on_delete=models.CASCADE, related_name="cards")
    index = models.PositiveSmallIntegerField()
    value = models.SmallIntegerField(choices=VALUES)
    suit = models.CharField(max_length=1, choices=SUITS)
    start_delta_ms = models.PositiveIntegerField(blank=True, null=True)

    @classmethod
    def get_ordered_cards_for_players(cls, player_count):
        for suit, _ in Card.SUITS[:player_count]:
            for value, _ in Card.VALUES:
                yield value, suit

    @classmethod
    def get_shuffled_deck(cls, player_count, seed):
        cards = list(cls.get_ordered_cards_for_players(player_count))
        shuffle_with_seed(cards, seed)
        return cards

    @property
    def drawn_datetime(self):
        if self.game.start_datetime and self.start_delta_ms:
            return self.game.start_datetime + datetime.timedelta(
                milliseconds=self.start_delta_ms
            )

        return None

    @property
    def finish_start_delta_ms(self):
        if self.value == Chug.VALUE:
            chug = getattr(self, "chug", None)
            if chug and chug.duration_ms:
                if chug.start_start_delta_ms:
                    chug_start = chug.start_start_delta_ms
                else:
                    chug_start = self.start_delta_ms

                return chug_start + self.chug.duration_ms

            return None

        return self.start_delta_ms

    def __str__(self):
        return f"{self.value} {self.suit}"

    def get_user(self):
        return self.game.ordered_players()[self.index % self.game.players.count()]

    def value_str(self):
        return dict(self.VALUES)[self.value]

    def suit_str(self):
        return dict(self.SUITS)[self.suit]

    def card_str(self):
        return f"{self.value_str()} of {self.suit_str()}"

    SUIT_SYMBOLS = {
        "S": ("♠", "black"),
        "C": ("♣", "black"),
        "H": ("♥", "red"),
        "D": ("♦", "red"),
        "A": ("☘", "green"),
        "I": ("🟊", "green"),
    }

    def suit_symbol(self):
        return self.SUIT_SYMBOLS[self.suit]

    def colored_suit_symbol(self):
        symbol, color = self.SUIT_SYMBOLS[self.suit]
        return format_html("<span style='color: {};'>{}</span>", color, symbol)


class Chug(models.Model):
    VALUE = 14

    card = models.OneToOneField("Card", on_delete=models.CASCADE, related_name="chug")
    start_start_delta_ms = models.PositiveIntegerField(blank=True, null=True)
    duration_ms = models.PositiveIntegerField(blank=True, null=True)

    @property
    def duration(self):
        if not self.duration_ms:
            return None

        return datetime.timedelta(milliseconds=self.duration_ms)

    def duration_str(self):
        if self.duration:
            return str(self.duration)
        else:
            return "Not done"

    def __str__(self):
        return f"{self.card.get_user()}: {self.card} ({self.duration_str()})"
