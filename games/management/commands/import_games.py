from django.core.management.base import BaseCommand
from django.core.files import File
from django.db.utils import IntegrityError
import csv
import datetime
import pytz
from tqdm import tqdm
from games.models import User, Game, Card, Chug


class Command(BaseCommand):
    help = "Imports games from the old academy database"

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true")
        parser.add_argument("--users", action="store_true")
        parser.add_argument("--user-images", action="store_true")
        parser.add_argument("--games", action="store_true")
        parser.add_argument("--game-player-relations", action="store_true")
        parser.add_argument("--cards", action="store_true")
        parser.add_argument("--chugs", action="store_true")

    def get_rows(self, table_name):
        with open(f"dump/tables/{table_name}.tsv", newline="") as f:
            reader = csv.DictReader(f, dialect="excel-tab")
            return tqdm(list(reader))

    def timestamp_seconds_to_datetime(self, timestamp):
        d = datetime.datetime.fromtimestamp(int(timestamp))
        return pytz.utc.localize(d)

    def timestamp_milliseconds_to_datetime(self, timestamp):
        return self.timestamp_seconds_to_datetime(int(timestamp) / 1000)

    def import_users(self):
        print("Importing users...")
        User.objects.all().delete()
        for user in self.get_rows("user"):
            User.objects.create(
                id=user["id"],
                username=user["username"],
                email="" if user["email"] == "NULL" else user["email"],
                old_password_hash=user["password_hash"],
                created_at=self.timestamp_seconds_to_datetime(user["created_at"]),
                updated_at=self.timestamp_seconds_to_datetime(user["updated_at"]),
            )

    def import_user_images(self):
        print("Importing user images...")
        for user in tqdm(User.objects.all()):
            try:
                image_path = f"dump/profilepictures/thumb_{user.id}.jpg"
                with open(image_path, "rb") as f:
                    user.image.save(None, File(f), save=True)
            except FileNotFoundError:
                pass

    def import_games(self):
        print("Importing games...")
        Game.objects.all().delete()
        for game in self.get_rows("game"):
            Game.objects.create(
                id=game["id"],
                start_datetime=self.timestamp_milliseconds_to_datetime(
                    game["starttime"]
                ),
                end_datetime=self.timestamp_milliseconds_to_datetime(game["time"]),
                description=game["description"],
                sips_per_beer=game["sips"],
                official=game["official"] == "\x01",
            )

    def import_game_player_relations(self):
        print("Importing game-player relations...")
        for relation in self.get_rows("playergamerelation"):
            game = Game.objects.get(id=relation["gameid"])
            user = User.objects.get(id=relation["profileid"])
            game.players.add(user)

    def get_value_and_suit(self, card_id):
        i = int(card_id) - 1
        value = Card.VALUES[i % len(Card.VALUES)][0]
        suit = Card.SUITS[i // len(Card.VALUES)][0]
        return value, suit

    def create_card(self, card_id, game, drawn_datetime):
        value, suit = self.get_value_and_suit(card_id)
        Card.objects.create(
            game=game, value=value, suit=suit, drawn_datetime=drawn_datetime
        )

    def import_cards(self):
        print("Importing cards...")
        Card.objects.all().delete()

        player_game_relations = {
            r["id"]: r for r in self.get_rows("playergamerelation")
        }

        for relation in self.get_rows("gamecardrelation"):
            pg_relation = player_game_relations[relation["playergamerelation"]]
            game = Game.objects.get(id=pg_relation["gameid"])
            drawn_datetime = datetime.datetime.strptime(
                relation["drawtime"], "%Y-%m-%d %H:%M:%S"
            )
            try:
                self.create_card(relation["cardid"], game, drawn_datetime)
            except IntegrityError:
                print(
                    f"Bad game: {game.id} (duplicate cards: {self.get_value_and_suit(relation['cardid'])})"
                )
                game.delete()

        for game in Game.objects.all():
            player_count = game.players.count()
            expected_cards = player_count * Game.TOTAL_ROUNDS

            if expected_cards != game.cards.count():
                print(
                    f"Bad game: {game.id} ({game.cards.count()} instead of {expected_cards} cards)"
                )
                game.delete()

    def import_chugs(self):
        print("Importing chugs...")
        Chug.objects.all().delete()

        for chug in self.get_rows("chuck"):
            card_id = chug["cardid"]
            value, suit = self.get_value_and_suit(card_id)
            try:
                game = Game.objects.get(id=chug["gameid"])
            except Game.DoesNotExist:
                # This can happen if the game is bad
                # and hasn't been imported
                continue

            if value != Chug.VALUE:
                print(f"Bad game: {game.id} (chug on card {(value, suit)})")
                game.delete()
                continue

            card = Card.objects.get(game=game, value=value, suit=suit)
            Chug.objects.create(card=card, duration_in_milliseconds=chug["millis"])

        for game in Game.objects.all():
            chugs = len(list(game.ordered_chugs()))
            players = game.players.count()
            if chugs != players:
                print(f"Bad game: {game.id} ({chugs} instead of {players} chugs)")
                game.delete()

    def handle(self, *args, **options):
        if options["all"] or options["users"]:
            self.import_users()

        if options["all"] or options["user_images"]:
            self.import_user_images()

        if options["all"] or options["games"]:
            self.import_games()

        if options["all"] or options["game_player_relations"]:
            self.import_game_player_relations()

        if options["all"] or options["cards"]:
            self.import_cards()

        if options["all"] or options["chugs"]:
            self.import_chugs()
