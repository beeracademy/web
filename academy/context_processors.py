from django.conf import settings


def constants(request):
    return {"PLAY_URL": settings.PLAY_URL}
