from django.core.management.base import BaseCommand
from games.models import recalculate_all_stats


class Command(BaseCommand):
    help = "Updates cached stats"

    def handle(self, *args, **options):
        recalculate_all_stats()
