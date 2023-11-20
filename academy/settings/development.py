import os

from django.db.backends.signals import connection_created

from .base import *  # noqa: F403
from .base import TESTING, MIDDLEWARE

ALLOWED_HOSTS = ["*"]
DEBUG = True

SECRET_KEY = "finish him!"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

SERVER_URL = "http://localhost:8000/"
PLAY_URL = "http://localhost:4200/"

AUTOLOGIN_USERNAME = os.environ.get("AUTOLOGIN_USERNAME")

CELERY_TASK_ALWAYS_EAGER = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
        }
    },
    "loggers": {
        "django": {},
    },
    "root": {
        "handlers": [
            "console",
        ],
        "level": "INFO",
    },
}


def on_connection_created(connection, **kwargs):
    if connection.vendor != "sqlite":
        return

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA busy_timeout = 5000;")


connection_created.connect(on_connection_created)

if not TESTING:
    MIDDLEWARE += ["academy.autologin.AutologinMiddleware"]
    # CORS_ALLOW_ALL_ORIGINS = True
