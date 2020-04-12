from django.core.management.base import BaseCommand
from collections import Counter
import json

from games.models import Game


class Command(BaseCommand):
    help = "Beep boop"

    def handle(self, *args, **options):
        total_sips = Counter()
        data = []

        for g in Game.objects.filter(end_datetime__isnull=False, dnf=False).order_by("end_datetime"):
            for s in g.get_player_stats():
                total_sips[s["username"]] += s["total_sips"]

            data.append((g.end_datetime.timestamp(), [{"x": k, "y": v} for k, v in total_sips.most_common(10)]))

        print("var race_data = ", end="")
        print(json.dumps(data))
