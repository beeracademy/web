import datetime

import pytz
from django.db.models import Q

from .models import Game, PlayerStat, Season, all_time_season

ACHIEVEMENTS = []

GOLD = "gold"
SILVER = "silver"
BRONZE = "bronze"
NO_LEVEL = "no_level"


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
            return GOLD
        return NO_LEVEL


class TopAchievement(Achievement):
    name = "Top"
    description = "Placed top (10/5/3) total sips in a season"
    icon = "trophy-cup.svg"

    def get_level(user):
        current_season = Season.current_season()
        highest_rank = NO_LEVEL

        for i in range(1, current_season.number):  # Exclude current season
            top10 = (
                PlayerStat.objects.filter(season_number=i)
                .order_by("-total_sips")[:10]
                .values("user")
            )
            top5 = top10[:5]
            top3 = top10[:3]

            if {"user": user.id} in top3:
                highest_rank = GOLD
                break
            elif {"user": user.id} in top5:
                highest_rank = SILVER
            elif {"user": user.id} in top10:
                if highest_rank != SILVER:
                    highest_rank = BRONZE

        return highest_rank


class FastGameAchievement(Achievement):
    name = "Fast Game"
    description = "Finished a game in less than (45/30/15) minutes"
    icon = "stopwatch.svg"

    def get_level(user):
        if (
            Game.add_durations(
                Game.objects.filter(
                    gameplayer__in=user.gameplayer_set.filter(
                        dnf=False, game__dnf=False
                    )
                )
            )
            .filter(duration__lt=datetime.timedelta(minutes=15))
            .exists()
        ):
            return GOLD
        elif (
            Game.add_durations(
                Game.objects.filter(
                    gameplayer__in=user.gameplayer_set.filter(
                        dnf=False, game__dnf=False
                    )
                )
            )
            .filter(duration__lt=datetime.timedelta(minutes=30))
            .exists()
        ):
            return SILVER
        elif (
            Game.add_durations(
                Game.objects.filter(
                    gameplayer__in=user.gameplayer_set.filter(
                        dnf=False, game__dnf=False
                    )
                )
            )
            .filter(duration__lt=datetime.timedelta(minutes=45))
            .exists()
        ):
            return BRONZE
        else:
            return NO_LEVEL


class DanishDSTAchievement(Achievement):
    name = "DST"
    description = "Participated in a game, while a DST transition happened in Denmark"
    icon = "backward-time.svg"

    @staticmethod
    def get_transition_times():
        return map(
            pytz.utc.localize,
            pytz.timezone("Europe/Copenhagen")._utc_transition_times[1:],
        )

    def get_level(user):
        query = Q()
        for dt in DanishDSTAchievement.get_transition_times():
            query |= Q(start_datetime__lt=dt, end_datetime__gt=dt)

        if user.games.filter(query).exists():
            return GOLD
        return NO_LEVEL


class TheBarrelAchievement(Achievement):
    name = "The Barrel"
    description = "Consumed (100/250/500) beers in-game"
    icon = "barrel.svg"

    def get_level(user):
        total_sips = user.stats_for_season(all_time_season).total_sips / 14
        if total_sips >= 500:
            return GOLD
        elif total_sips >= 250:
            return SILVER
        elif total_sips >= 100:
            return BRONZE
        return NO_LEVEL


class BundeCampAchievement(Achievement):
    name = "Chug Camp"
    description = "Got (50/75/100) chugs in-game"
    icon = "ace.svg"

    def get_level(user):
        total_chugs = user.stats_for_season(all_time_season).total_chugs
        if total_chugs >= 100:
            return GOLD
        elif total_chugs >= 75:
            return SILVER
        elif total_chugs >= 50:
            return BRONZE
        return NO_LEVEL


class StudyHardAchievement(Achievement):
    name = "Study Hard"
    description = (
        "Spend at least the amount of time corresponding to (2.5/5/10) ECTS in game"
    )
    icon = "diploma.svg"

    def get_level(user):
        ects = user.stats_for_season(all_time_season).approx_ects
        if ects >= 10:
            return GOLD
        elif ects >= 5:
            return SILVER
        elif ects >= 2.5:
            return BRONZE
        return NO_LEVEL


class PilfingerAchievement(Achievement):
    name = "Pilfinger"
    description = "Stille stille stille, Pille pille pille"
    icon = "pilfinger.jpg"

    def get_level(user):
        if user.id == 2030:
            return GOLD
        return NO_LEVEL

    def is_hidden(user):
        return PilfingerAchievement.get_level(user) != GOLD
