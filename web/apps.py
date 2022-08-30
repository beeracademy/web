from django.apps import AppConfig


class WebConfig(AppConfig):
    name = "web"

    def ready(self):
        from .stats import init_cache

        init_cache()
