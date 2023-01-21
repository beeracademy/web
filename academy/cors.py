from django.conf import settings


ALLOWED_HOSTS = [
    "https://game.academy.beer",
    "https://beta.academy.beer",
]


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not request.path.startswith("/api/") and not request.path.startswith(
            "/api-token-auth/"
        ):
            return response

        if settings.DEBUG:
            origin = "*"
        elif request.get_host() in ALLOWED_HOSTS:
            origin = request.get_host()

        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Methods"] = "options, get, post"
        response["Access-Control-Allow-Headers"] = "content-type, authorization"

        return response
