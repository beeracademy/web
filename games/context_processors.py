from .models import Season, all_time_season
from web.utils import updated_query_url


def seasons(request):
    current = Season.current_season()
    season_url = lambda season: updated_query_url(
        request, {"season": season, "page": None}
    )
    season_urls = [(all_time_season, season_url(None))]
    for i in range(current.number, 0, -1):
        season_urls.append((Season(i), season_url(i)))

    return {"current_season": current, "season_urls": season_urls}
