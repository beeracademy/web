from .base import *

DEBUG = False
ALLOWED_HOSTS = ["academy.beer"]

SECRET_KEY = os.getenv("SECRET_KEY")

SESSION_COOKIE_SECURE = True

# Server admins (get an email when server errors happen)
ADMINS = [("Asger Hautop Drewsen", "asgerdrewsen@gmail.com")]

EMAIL_HOST = "smtp.gmail.com"
EMAIL_HOST_USER = "django.drewsen@gmail.com"
EMAIL_USE_SSL = True
EMAIL_PORT = 465

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
        }
    },
    "loggers": {
        # Again, default Django configuration to email unhandled exceptions
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        }
    },
}
