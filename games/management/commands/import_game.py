from django.core.management.base import BaseCommand, CommandError
from games.models import Game
from games.serializers import GameSerializer
from games.views import update_game
import argparse
import json


class Command(BaseCommand):
    help = "Imports game from a json file"

    def add_arguments(self, parser):
        parser.add_argument("file", type=argparse.FileType("r"))
        parser.add_argument("--fix_times", action="store_true")

    def handle(self, *args, **options):
        data = json.load(options["file"])

        game, created = Game.objects.get_or_create(
            id=data["id"], defaults={"start_datetime": None}
        )

        s = GameSerializer(game, data=data, context={"fix_times": options["fix_times"]})
        if not s.is_valid():
            raise CommandError(s.errors)

        update_game(game, s.validated_data)
        if created:
            print(f"Created game with id {data['id']}")
        else:
            print(f"Updated game with id {data['id']}")
