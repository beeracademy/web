import os
import sys

from .base import *

ALLOWED_HOSTS = ["*"]
DEBUG = True

SECRET_KEY = "finish him!"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

PLAY_URL = "http://localhost:4200"

AUTOLOGIN_USERNAME = os.environ.get("AUTOLOGIN_USERNAME")

CELERY_TASK_ALWAYS_EAGER = True

if sys.argv[1:2] != ["test"]:
    MIDDLEWARE += ["academy.autologin.AutologinMiddleware"]
