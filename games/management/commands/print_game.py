from django.core.management.base import BaseCommand

from games.models import Game


class Command(BaseCommand):
    help = "Prints info about a game given its id"

    def add_arguments(self, parser):
        parser.add_argument("game_id", type=int)

    def handle(self, *args, **options):
        game = Game.objects.get(id=options["game_id"])
        print("Start:", game.start_datetime)
        print("Description:", game.description)

        player_count = game.players.count()
        print(f"Players ({player_count}):")
        for i, player in enumerate(game.ordered_players()):
            print(f"{i + 1} {player}")

        print()
        print("Cards:")
        for i, card in enumerate(game.ordered_cards()):
            print(card.value, end="\t")
            if (i + 1) % player_count == 0:
                print()

        print()
        print("Chugs:")
        for i, chug in enumerate(game.ordered_chugs()):
            print(chug)
