from django.core.management.base import BaseCommand
from games.models import PlayerStat


class Command(BaseCommand):
    help = "Updates cached player stats"

    def handle(self, *args, **options):
        PlayerStat.update_all()
