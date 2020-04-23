from django.contrib.auth.backends import BaseBackend

from .models import OneTimePassword, User


class OneTimePasswordBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        try:
            user = User.objects.get(username__iexact=username)
            if OneTimePassword.check_password(username, password):
                return user
        except User.DoesNotExist:
            pass

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
