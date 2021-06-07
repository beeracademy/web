import os
import sys

from .base import *

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
    "": {
        "handlers": [
            "console",
        ],
        "level": "INFO",
    },
}

if not TESTING:
    MIDDLEWARE += ["academy.autologin.AutologinMiddleware"]
