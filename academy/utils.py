import os
import sys
from urllib.parse import urljoin

from django.conf import settings


def get_absolute_url(url):
    return urljoin(settings.SERVER_URL, url)


def is_running_real_server() -> bool:
    if settings.TESTING:
        return False

    if "RUN_MAIN" in os.environ:
        return True

    if sys.argv[0].endswith("daphne"):
        return True

    return False
