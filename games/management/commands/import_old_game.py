from django.core.management.base import BaseCommand, CommandError
from games.models import User, Game, Card, Chug, GamePlayer, update_stats_on_game_finished
from django.db import transaction
import datetime
import argparse
import pytz


class Command(BaseCommand):
    help = "Imports game from an old log format"

    def add_arguments(self, parser):
        parser.add_argument("logfile", type=argparse.FileType("r"))
        parser.add_argument("--ignore-ids", action="store_true")

    def timestamp_to_datetime(self, t):
        try:
            return pytz.timezone("Europe/Copenhagen").localize(
                datetime.datetime.fromtimestamp(int(t) / 1000)
            )
        except ValueError:
            raise CommandError(f"Invalid timestamp: {t}")

    def parse_card(self, s):
        SUIT_MAP = {"sp": "S", "cl": "C", "he": "H", "di": "D", "ca": "A", "hi": "I"}

        suit_str, value_str = s[:2], s[2:]

        suit = SUIT_MAP.get(suit_str)
        if suit is None:
            raise CommandError(f"Unknown suit: {suit_str}")

        try:
            value = int(value_str)
            if not (2 <= value <= 14):
                raise ValueError
        except ValueError:
            raise CommandError(f"Invalid value: {value_str}")

        return (value, suit)

    def parse_duration(self, d):
        parts = d.split(":")
        if len(parts) != 3:
            raise CommandError(f"Unknown chug time: {d}")

        try:
            minutes, seconds, ms = [int(x) for x in parts]
        except ValueError:
            raise CommandError(f"Unknown chug time: {d}")

        return ((minutes * 60) + seconds) * 1000 + ms

    def handle(self, *args, **options):
        lines = list(options["logfile"].readlines())

        first_parts = lines[0].split()
        if len(first_parts) < 2:
            raise CommandError(f"First line has fewer than 2 words")

        name, start_timestamp, *ids = first_parts
        if name != "startime":
            raise CommandError(f"First line doesn't start with 'startime'")

        if not (2 <= len(ids) <= 6):
            raise CommandError(f"Not between 2 and 6 players")

        if options["ignore_ids"]:
            ids = ["0"] * len(ids)

        try:
            ids = [int(x) for x in ids]
        except ValueError:
            raise CommandError(f"Ids are not numeric")

        last_parts = lines[-1].split()
        if len(last_parts) != 2:
            raise CommandError(f"Not 2 words on last line")

        name, end_timestamp = last_parts
        if name != "endtime":
            raise CommandError(f"Last line doesn't start with 'endtime'")

        player_count = len(ids)
        find_ids = options["ignore_ids"] or ids[0] == "0"
        if not find_ids and len(set(ids)) != player_count:
            print("Same id found multiple times.")
            if input("Ignore ids and rely on names instead? [Yn] ") not in ["n", "N"]:
                find_ids = True

        if find_ids:
            ids = []

            i = 0
            while len(ids) < player_count:
                i += 1
                l = lines[i]
                parts = l.split()
                if len(parts) == 6:
                    continue
                elif len(parts) == 4:
                    username, *_ = parts
                    try:
                        ids.append(User.objects.get(username=username).id)
                    except User.DoesNotExist:
                        raise CommandError(
                            f"Couldn't find user with username {username}"
                        )
                else:
                    raise CommandError(f"Unknown line with {len(parts)} words: {l}")

        users = []
        for user_id in ids:
            try:
                users.append(User.objects.get(id=user_id))
            except User.DoesNotExist:
                raise CommandError(f"Couldn't find user with id {user_id}")

        with transaction.atomic():
            game = Game.objects.create(
                start_datetime=self.timestamp_to_datetime(start_timestamp),
                end_datetime=self.timestamp_to_datetime(end_timestamp),
                description="Game from academyv2 log",
            )

            for i, user in enumerate(users):
                GamePlayer.objects.create(game=game, user=user, position=i)

            last_card = None
            card_index = 0
            for l in lines[1:-1]:
                parts = l.split()
                if len(parts) == 6:
                    if last_card is None or last_card.value != 14:
                        raise CommandError(f"Chuck without an ace before")

                    duration_ms = self.parse_duration(parts[4])
                    Chug.objects.create(
                        card=last_card, duration_in_milliseconds=duration_ms
                    )
                elif len(parts) == 4:
                    _, _, card, drawn_timestamp = parts

                    drawn_datetime = self.timestamp_to_datetime(drawn_timestamp)
                    value, suit = self.parse_card(card)
                    last_card = Card.objects.create(
                        game=game,
                        index=card_index,
                        value=value,
                        suit=suit,
                        drawn_datetime=drawn_datetime,
                    )
                    card_index += 1
                else:
                    raise CommandError(f"Unknown line with {len(parts)} words: {l}")

            expected_cards = player_count * 13
            if game.cards.count() != expected_cards:
                raise CommandError(
                    f"Wrong number of drawn cards: {game.cards.count()}, but expected {expected_cards}"
                )

            chugs_count = len(list(game.ordered_chugs()))
            if chugs_count != player_count:
                raise CommandError(
                    f"Wrong number of chugs: {chugs_count}, but expected {player_count}"
                )

            update_stats_on_game_finished(game)

        print(f"Successfully imported game. Id: {game.id}")
