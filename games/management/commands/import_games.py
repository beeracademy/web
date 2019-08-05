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
        parser.add_argument("--fix-times", action="store_true")
        parser.add_argument("--chugs", action="store_true")

    def get_rows(self, table_name):
        with open(f"dump/tables/{table_name}.tsv", newline="") as f:
            reader = csv.DictReader(f, dialect="excel-tab")
            return list(reader)

    def timestamp_seconds_to_datetime(self, timestamp):
        d = datetime.datetime.fromtimestamp(int(timestamp))
        return pytz.utc.localize(d)

    def timestamp_milliseconds_to_datetime(self, timestamp):
        return self.timestamp_seconds_to_datetime(int(timestamp) / 1000)

    def import_users(self):
        print("Importing users...")
        User.objects.all().delete()
        for user in tqdm(self.get_rows("user")):
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
        for game in tqdm(self.get_rows("game")):
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
        relations = sorted(
            self.get_rows("playergamerelation"), key=lambda r: int(r["place"])
        )
        for relation in tqdm(relations):
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

    def is_bad_card_date(self, dt):
        # Every card drawn on this date,
        # actually has an unknown drawn datetime
        BAD_CARD_DATE = (2015, 7, 5)

        return dt.timetuple()[:3] == BAD_CARD_DATE

    def import_cards(self):
        print("Importing cards...")
        Card.objects.all().delete()

        player_game_relations = {
            r["id"]: r for r in self.get_rows("playergamerelation")
        }

        relations = sorted(
            self.get_rows("gamecardrelation"),
            key=lambda relation: (
                int(relation["roundid"]),
                int(player_game_relations[relation["playergamerelation"]]["place"]),
            ),
        )

        card_delta = {}

        for relation in tqdm(relations):
            pg_relation = player_game_relations[relation["playergamerelation"]]
            try:
                game = Game.objects.get(id=pg_relation["gameid"])
            except Game.DoesNotExist:
                # This can happen if the game is bad
                # and hasn't been imported
                continue

            # Actually not in UTC, but we will try to fix this.
            drawn_datetime = pytz.utc.localize(
                datetime.datetime.strptime(relation["drawtime"], "%Y-%m-%d %H:%M:%S")
            )

            if game.id not in card_delta:
                # First card in game
                # Try to adjust it to start_datetime, which is in UTC
                if game.start_datetime.year == 1970 or self.is_bad_card_date(
                    drawn_datetime
                ):
                    card_delta[game.id] = datetime.timedelta()
                else:
                    diff_start = drawn_datetime - game.start_datetime
                    seconds = diff_start.total_seconds()
                    hours = seconds / (60 * 60)
                    rounded_hours = round(hours)
                    delta = datetime.timedelta(hours=rounded_hours)
                    card_delta[game.id] = delta
                    assert diff_start - delta >= datetime.timedelta(), (
                        diff_start,
                        game.id,
                    )

            drawn_datetime -= card_delta[game.id]

            try:
                self.create_card(relation["cardid"], game, drawn_datetime)
            except IntegrityError:
                # Game 1072 has a harmless duplicate card
                if game.id == 1072:
                    continue

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

    def fix_times(self):
        print("Fixing times of games/cards")
        for game in tqdm(Game.objects.all()):
            cards = game.ordered_cards()

            if self.is_bad_card_date(cards.first().drawn_datetime):
                # We assume that the first card has an unknown drawn datetime
                # if and only if all of them have
                continue

            # We generally expect cards draw times to be ordered,
            # but they don't necessarily lie in the interval of
            # [game.start_datetime, game.end_datetime]
            prev_dt = None
            bad_card_order = False
            for c in cards:
                if prev_dt is not None and c.drawn_datetime < prev_dt:
                    bad_card_order = True
                    break
                prev_dt = c.drawn_datetime

            if game.start_datetime > game.end_datetime:
                bad_card_order = True

            first_card = cards.first()
            last_card = cards.last()

            card_duration = last_card.drawn_datetime - first_card.drawn_datetime
            game_duration = game.get_duration()
            if card_duration > game_duration:
                print(card_duration, game_duration)
                bad_card_order = True

            # Manually fix for some specific games
            if bad_card_order:
                bad_card_order = False
                if game.id == 1339:
                    # A specially fucked up game
                    print(f"Manually fixing {game.id}")

                    game.end_datetime += datetime.timedelta(hours=2)
                    game.save()

                    after_dst = False
                    prev_dt = None
                    for c in cards:
                        if prev_dt is not None and c.drawn_datetime < prev_dt:
                            after_dst = True
                        prev_dt = c.drawn_datetime

                        if after_dst:
                            c.drawn_datetime += datetime.timedelta(hours=2)
                            c.save()
                elif game.id == 1229:
                    # I don't know what happened to this game,
                    # but it isn't that hard to fix
                    print(f"Manually fixing {game.id}")

                    cards_l = list(cards)
                    cards_l[7].drawn_datetime += datetime.timedelta(seconds=15)
                    cards_l[7].save()
                    cards_l[8].drawn_datetime += datetime.timedelta(seconds=15)
                    cards_l[8].save()
                elif game.id == 1294:
                    # This was played while a DST transition happened
                    print(f"Manually fixing {game.id}")

                    game.save()

                    after_dst = False
                    prev_dt = None
                    for c in cards:
                        if (
                            prev_dt is not None
                            and c.drawn_datetime > prev_dt + datetime.timedelta(hours=1)
                        ):
                            after_dst = True
                        prev_dt = c.drawn_datetime

                        if after_dst:
                            c.drawn_datetime -= datetime.timedelta(hours=1)
                            c.save()

            if (
                first_card.drawn_datetime < game.start_datetime
                or last_card.drawn_datetime > game.end_datetime
            ):
                bad_card_order = True

            if bad_card_order:
                print(f"== Game with bad card order found: {game.id} ==")
                print("Start:", game.start_datetime)
                print("End:", game.end_datetime)
                print()

                for c in cards:
                    print(str(c.drawn_datetime.time()))

                print()

    def import_chugs(self):
        print("Importing chugs...")
        Chug.objects.all().delete()

        for chug in tqdm(self.get_rows("chuck")):
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

        if options["all"] or options["fix_times"]:
            self.fix_times()

        if options["all"] or options["chugs"]:
            self.import_chugs()
