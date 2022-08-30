import os
from urllib.parse import urljoin

from django.conf import settings


def get_absolute_url(url):
    return urljoin(settings.SERVER_URL, url)


def is_running_real_server() -> bool:
    if settings.TESTING:
        return False

    return "RUN_MAIN" in os.environ or not settings.DEBUG
