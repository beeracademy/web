from django.conf import settings

from games.models import User


def constants(request):
    width, height = User.IMAGE_SIZE
    return {"PLAY_URL": settings.PLAY_URL, "IMAGE_WIDTH": width, "IMAGE_HEIGHT": height}
