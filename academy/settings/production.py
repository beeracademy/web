from .base import *

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

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("127.0.0.1", 6379)],},
    },
}

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Server admins (get an email when server errors happen)
ADMINS = [("Asger Hautop Drewsen", "asgerdrewsen@gmail.com")]

FACEBOOK_PAGE_ID = "227174884109471"
FACEBOOK_ACCESS_TOKEN = os.environ["FACEBOOK_ACCESS_TOKEN"]

CELERY_BROKER_URL = "redis://redis:6379/0"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        # Include the default Django email handler for errors
        # This is what you'd get without configuring logging at all.
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
            "level": "ERROR",
            # But the emails are plain text by default - HTML is nicer
            "include_html": True,
        },
        # Log to a text file that can be rotated by logrotate
        "logfile": {
            "class": "logging.handlers.WatchedFileHandler",
            "filename": "/app/django.log",
        },
    },
    "loggers": {
        # Again, default Django configuration to email unhandled exceptions
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
        # Might as well log any errors anywhere else in Django
        "django": {"handlers": ["logfile"], "level": "ERROR", "propagate": False},
    },
}
