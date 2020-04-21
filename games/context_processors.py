from web.utils import SeasonChooser

from .models import Season


def seasons(request):
    chooser = SeasonChooser(request)
    return {"current_season": Season.current_season(), "season_chooser": chooser}
