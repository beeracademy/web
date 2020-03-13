import datetime

import pytz
from django.db.models import Q

from .models import Game, PlayerStat, Season, all_time_season

ACHIEVEMENTS = []


class AchievementMetaClass(type):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        if name != "Achievement":
            ACHIEVEMENTS.append(self)


class Achievement(metaclass=AchievementMetaClass):
    __slots__ = ["name", "description", "icon"]

    @staticmethod
    def has_achieved(user):
        raise NotImplementedError


class DNFAchievement(Achievement):
    name = "DNF"
    description = "Participated in a game that completed, where you didn't"
    icon = "coffin"

    def has_achieved(user):
        return (
            user.gameplayer_set.filter(dnf=True)
            .filter(game__dnf=False, game__end_datetime__isnull=False)
            .exists()
        )


class Top10Achievement(Achievement):
    name = "Top 10"
    description = "Placed top 10 total sips in a season"
    icon = "trophy-cup"

    def has_achieved(user):
        current_season = Season.current_season()
        for i in range(1, current_season.number + 1):
            top10 = (
                PlayerStat.objects.filter(season_number=i)
                .order_by("-total_sips")[:10]
                .values("user")
            )
            if {"user": user.id} in top10:
                return True

        return False


class FastGameAchievement(Achievement):
    name = "Fast Game"
    description = "Finished a game in less than 30 minutes"
    icon = "stopwatch"

    def has_achieved(user):
        return (
            Game.add_durations(
                Game.objects.filter(
                    gameplayer__in=user.gameplayer_set.filter(dnf=False).filter(
                        game__dnf=False
                    )
                )
            )
            .filter(duration__lt=datetime.timedelta(minutes=30))
            .exists()
        )


class DanishDSTAchievement(Achievement):
    name = "DST"
    description = "Participated in a game, while a DST transition happened in Denmark"
    icon = "backward-time"

    @staticmethod
    def get_transition_times():
        return map(
            pytz.utc.localize,
            pytz.timezone("Europe/Copenhagen")._utc_transition_times[1:],
        )

    def has_achieved(user):
        query = Q()
        for dt in DanishDSTAchievement.get_transition_times():
            query |= Q(start_datetime__lt=dt, end_datetime__gt=dt)

        return user.games.filter(query).exists()


class TheBarrelAchievement(Achievement):
    name = "The Barrel"
    description = "Consumed 100 beers in-game"
    icon = "barrel"

    def has_achieved(user):
        return (user.stats_for_season(all_time_season).total_sips / 14) >= 100


class BundeCampAchievement(Achievement):
    name = "Chug Camp"
    description = "Got 50 chugs in-game"
    icon = "ace"

    def has_achieved(user):
        return user.stats_for_season(all_time_season).total_chugs >= 50


class StudyHardAchievement(Achievement):
    name = "Study Hard"
    description = f"Spend at least the amount of time corresponding to 2.5 ECTS in game (56 hours)"
    icon = "diploma"

    def has_achieved(user):
        return user.stats_for_season(all_time_season).approx_ects >= 2.5
