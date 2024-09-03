import datetime
import zoneinfo
from collections import Counter
from enum import StrEnum

from django.db.models import Q

from .models import Game, PlayerStat, Season, all_time_season

ACHIEVEMENTS = []


TIMEZONE_FILENAME = zoneinfo._tzpath.find_tzfile("Europe/Copenhagen")
with open(TIMEZONE_FILENAME, "rb") as f:
    TIMEZONE_DATA = zoneinfo._common.load_data(f)
VALID_DATES = filter(lambda t: t > 0, TIMEZONE_DATA[1])
DST_TRANSITION_TIMES = [
    datetime.datetime.fromtimestamp(t, tz=datetime.timezone.utc) for t in VALID_DATES
]


class AchievementLevel(StrEnum):
    """Each level must correspond to a style in styles.css"""

    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    BASE = "base"
    NO_LEVEL = "no_level"

    def __gt__(self, other):
        return list(AchievementLevel).index(self) < list(AchievementLevel).index(other)


class AchievementMetaClass(type):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        if name != "Achievement":
            ACHIEVEMENTS.append(self)


class Achievement(metaclass=AchievementMetaClass):
    __slots__ = ["name", "description", "icon"]

    @staticmethod
    def get_level(user):
        raise NotImplementedError

    @staticmethod
    def is_hidden(user):
        return False


class DNFAchievement(Achievement):
    name = "DNF"
    description = "Participated in a game that completed, where you didn't"
    icon = "coffin.svg"

    def get_level(user):
        if (
            user.gameplayer_set.filter(dnf=True)
            .filter(game__dnf=False, game__end_datetime__isnull=False)
            .exists()
        ):
            return AchievementLevel.GOLD
        return AchievementLevel.NO_LEVEL


class TopAchievement(Achievement):
    name = "Top"
    description = "Placed top (10/5/3/1) total sips in a season"
    icon = "trophy-cup.svg"

    def get_level(user):
        current_season = Season.current_season()
        highest_tier = AchievementLevel.NO_LEVEL
        for i in range(1, current_season.number):  # Exclude current season
            top10 = list(
                PlayerStat.objects.filter(season_number=i)
                .order_by("-total_sips")[:10]
                .values("user")
            )
            try:
                rank = top10.index({"user": user.id})
                if rank < 1:
                    return AchievementLevel.GOLD
                elif rank < 3:
                    highest_tier = max(AchievementLevel.SILVER, highest_tier)
                elif rank < 5:
                    highest_tier = max(AchievementLevel.BRONZE, highest_tier)
                elif rank < 10:
                    highest_tier = max(AchievementLevel.BASE, highest_tier)
            except ValueError:
                continue
        return highest_tier


class FastGameAchievement(Achievement):
    name = "Fast Game"
    description = "Finished a game in less than (30/20/15/10) minutes"
    icon = "stopwatch.svg"

    def get_level(user):
        short_games = Game.add_durations(
            Game.objects.filter(
                gameplayer__in=user.gameplayer_set.filter(dnf=False, game__dnf=False)
            )
        ).filter(duration__lt=datetime.timedelta(minutes=30))
        if short_games.filter(duration__lt=datetime.timedelta(minutes=10)).exists():
            return AchievementLevel.GOLD
        elif short_games.filter(duration__lt=datetime.timedelta(minutes=15)).exists():
            return AchievementLevel.SILVER
        elif short_games.filter(duration__lt=datetime.timedelta(minutes=20)).exists():
            return AchievementLevel.BRONZE
        elif short_games.exists():
            return AchievementLevel.BASE
        else:
            return AchievementLevel.NO_LEVEL


class DanishDSTAchievement(Achievement):
    name = "DST"
    description = "Participated in a game, while a DST transition happened in Denmark"
    icon = "backward-time.svg"

    def get_level(user):
        query = Q()
        for dt in DST_TRANSITION_TIMES:
            query |= Q(start_datetime__lt=dt, end_datetime__gt=dt)

        if user.games.filter(query).exists():
            return AchievementLevel.BASE
        return AchievementLevel.NO_LEVEL


class TheBarrelAchievement(Achievement):
    name = "The Barrel"
    description = "Consumed (100/1000/2000/4000) beers in-game"
    icon = "barrel.svg"

    def get_level(user):
        total_sips = user.stats_for_season(all_time_season).total_sips / 14
        if total_sips >= 4000:
            return AchievementLevel.GOLD
        elif total_sips >= 2000:
            return AchievementLevel.SILVER
        elif total_sips >= 1000:
            return AchievementLevel.BRONZE
        elif total_sips >= 100:
            return AchievementLevel.BASE
        return AchievementLevel.NO_LEVEL


class BundeCampAchievement(Achievement):
    name = "Chug Camp"
    description = "Got (50/100/250/500) chugs in-game"
    icon = "ace.svg"

    def get_level(user):
        total_chugs = user.stats_for_season(all_time_season).total_chugs
        if total_chugs >= 500:
            return AchievementLevel.GOLD
        elif total_chugs >= 250:
            return AchievementLevel.SILVER
        elif total_chugs >= 100:
            return AchievementLevel.BRONZE
        elif total_chugs >= 50:
            return AchievementLevel.BASE
        return AchievementLevel.NO_LEVEL


class StudyHardAchievement(Achievement):
    name = "Study Hard"
    description = (
        "Spend at least the amount of time corresponding to (2.5/15/30/60) ECTS in game"
    )
    icon = "diploma.svg"

    def get_level(user):
        ects = user.stats_for_season(all_time_season).approx_ects
        if ects >= 60:
            return AchievementLevel.GOLD
        elif ects >= 30:
            return AchievementLevel.SILVER
        elif ects >= 15:
            return AchievementLevel.BRONZE
        elif ects >= 2.5:
            return AchievementLevel.BASE
        return AchievementLevel.NO_LEVEL


class TheMoreTheMerrierAchievement(Achievement):
    name = "The More The Merrier"
    description = (
        "Play atleast 5/10/15/20 games with as many different players"
    )
    icon = "merrier.svg"
    def get_level(user):
        played_with_count = Counter()
        for game in user.games.filter():
            for player in game.players.all():
                if player != user:
                   played_with_count[player.username] += 1

        top20 = sorted(
            ({"x": k, "y": v} for k, v in played_with_count.items()),
            key=lambda x: -x["y"],
        )[:30]
        if len(top20) < 20:
            return AchievementLevel.NO_LEVEL
        if top20[19].get("y") >= 20:
            return AchievementLevel.GOLD
        elif top20[14].get("y") >= 15:
            return AchievementLevel.SILVER
        elif top20[9].get("y") >= 10:
            return AchievementLevel.BRONZE
        elif top20[4].get("y") >= 5:
            return AchievementLevel.BASE
        else:
            return AchievementLevel.NO_LEVEL

class PilfingerAchievement(Achievement):
    name = "Pilfinger"
    description = "Stille stille stille, Pille pille pille"
    icon = "pilfinger.jpg"

    def get_level(user):
        if user.id == 2030:
            return AchievementLevel.GOLD
        return AchievementLevel.NO_LEVEL

    def is_hidden(user):
        return PilfingerAchievement.get_level(user) != AchievementLevel.GOLD
