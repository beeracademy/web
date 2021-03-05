from urllib.parse import urljoin

from django.conf import settings


def get_absolute_url(url):
    return urljoin(settings.SERVER_URL, url)
