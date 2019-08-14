from .base import *

ALLOWED_HOSTS = ["*"]
DEBUG = True

SECRET_KEY = "finish him!"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

PLAY_URL = "localhost:4200"
