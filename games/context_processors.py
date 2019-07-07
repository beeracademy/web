from .models import get_current_season


def seasons(request):
    return {"seasons": reversed(range(1, get_current_season() + 1))}
