from django.conf import settings
from django.contrib.auth import login
from games.models import User


class AutologinMiddleware:
    def __init__(self, get_response):
        self.first_request = True
        self.get_response = get_response

    def __call__(self, request):

        if self.first_request:
            self.first_request = False

            username = getattr(settings, "AUTOLOGIN_USERNAME", None)
            if username:
                user = User.objects.get(username=username)
                login(
                    request, user, backend="django.contrib.auth.backends.ModelBackend"
                )

        return self.get_response(request)
