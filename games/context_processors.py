from .models import Season
from web.utils import SeasonChooser


def seasons(request):
    chooser = SeasonChooser(request)
    return {"current_season": Season.current_season(), "season_chooser": chooser}
