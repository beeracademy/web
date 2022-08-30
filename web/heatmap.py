import datetime
from collections import Counter
from typing import Any

from django.utils import timezone

from games.models import Season, all_time_season, filter_season


def games_heatmap_data(games, season: Season) -> dict[str, Any]:
    if season == all_time_season:
        last_date = timezone.now().date()
        first_date = last_date - datetime.timedelta(days=53 * 7 - 1)
    else:
        last_date = season.end_datetime.date()
        first_date = season.start_datetime.date()

    games_played = Counter()
    for g in filter_season(games, season):
        if g.end_datetime:
            games_played[g.end_datetime.date()] += 1

    weekday = last_date.weekday()

    DAY_NAMES = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    DAY_NAMES = DAY_NAMES[weekday + 1 :] + DAY_NAMES[: weekday + 1]

    series = []
    dates = []
    categories = []
    for d in DAY_NAMES:
        series.append({"name": d, "data": []})
        dates.append([])

    # Ensure we have a whole number of weeks
    rounded_first_date = (
        first_date
        + (last_date - first_date) % datetime.timedelta(days=7)
        - datetime.timedelta(days=6)
    )
    date = rounded_first_date
    i = 0
    while date <= last_date:
        if i % 7 == 0:
            if date.day <= 7:
                categories.append(date.strftime("%b"))
            else:
                categories.append("")

        if date >= first_date:
            played = games_played[date]
        else:
            played = None

        series[i % 7]["data"].append(played)
        dates[i % 7].append(date)
        date += datetime.timedelta(days=1)
        i += 1

    return {"series": series, "categories": categories, "dates": dates}
