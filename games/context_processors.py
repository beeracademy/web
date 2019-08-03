from .models import Season, all_time_season


def seasons(request):
    current = Season.current_season()
    menu_seasons = [all_time_season]
    for i in range(current.number, 0, -1):
        menu_seasons.append(Season(i))

    return {"current_season": current, "menu_seasons": menu_seasons}
