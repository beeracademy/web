from .base import *
from dotenv import load_dotenv

load_dotenv()

DEBUG = False
ALLOWED_HOSTS = ["academy.beer"]

SECRET_KEY = os.environ["SECRET_KEY"]

SESSION_COOKIE_SECURE = True

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "django.drewsen@gmail.com"
EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]

SERVER_EMAIL = "no-reply@academy.beer"
DEFAULT_FROM_EMAIL = "no-reply@academy.beer"

PLAY_URL = "https://game.academy.beer/"
MEDIA_URL = "https://media.academy.beer/"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": "postgres",
        "HOST": "db",
        "PORT": 5432,
    }
}

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Server admins (get an email when server errors happen)
ADMINS = [
	('Asger Hautop Drewsen', 'asgerdrewsen@gmail.com'),
]

FACEBOOK_PAGE_ID = "227174884109471"
FACEBOOK_ACCESS_TOKEN = os.environ["FACEBOOK_ACCESS_TOKEN"]

CELERY_BROKER_URL = "amqp://guest:guest@rabbitmq:5672//"
