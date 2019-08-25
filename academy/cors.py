from django.conf import settings


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/") or request.path.startswith(
            "/api-token-auth/"
        ):
            if settings.DEBUG:
                origin = "*"
            else:
                origin = "https://game.academy.beer"

            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = "options, get, post"
            response["Access-Control-Allow-Headers"] = "content-type, authorization"

        return response
