from .base import *

DEBUG = False
ALLOWED_HOSTS = ["academy.beer"]

SECRET_KEY = os.getenv("SECRET_KEY")

SESSION_COOKIE_SECURE = True

# Server admins (get an email when server errors happen)
ADMINS = [("Asger Hautop Drewsen", "asgerdrewsen@gmail.com")]
