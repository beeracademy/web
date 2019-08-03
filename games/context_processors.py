from .models import Season, all_time_season
from web.utils import updated_query_url
from functools import partial


def seasons(request):
    current = Season.current_season()
    season_url = partial(updated_query_url, request, "season")
    season_urls = [(all_time_season, season_url(None))]
    for i in range(current.number, 0, -1):
        season_urls.append((Season(i), season_url(i)))

    return {"current_season": current, "season_urls": season_urls}
