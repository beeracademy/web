from .base import *
import os

ALLOWED_HOSTS = ["*"]
DEBUG = True

SECRET_KEY = "finish him!"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

PLAY_URL = "http://localhost:4200"

AUTOLOGIN_USERNAME = os.environ.get("AUTOLOGIN_USERNAME")

MIDDLEWARE += ["academy.autologin.AutologinMiddleware"]
