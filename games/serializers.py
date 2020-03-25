import datetime
import re
from urllib.parse import urlencode

from django.urls import reverse
from django.utils.html import format_html

from rest_framework import serializers
from rest_framework.authtoken.models import Token

from .models import Card, Game, GamePlayer, PlayerStat, User
from .seed import is_seed_valid_for_players


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "is_superuser", "image_url", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User(username=validated_data["username"])
        user.set_password(validated_data["password"])
        user.save()
        return user


class CreateGameSerializer(serializers.Serializer):
    tokens = serializers.ListField(
        child=serializers.CharField(), min_length=2, max_length=6
    )
    official = serializers.BooleanField()

    def validate_tokens(self, value):
        users = []
        for key in value:
            try:
                token = Token.objects.get(key=key)
                user = token.user
                if user in users:
                    raise serializers.ValidationError(
                        f"Same user logged in multiple times: {user.username}"
                    )

                users.append(user)
            except Token.DoesNotExist:
                raise serializers.ValidationError(f"User with token not found: {key}")

        return users

    def create(self, validated_data):
        game = Game.objects.create()
        for i, user in enumerate(validated_data["tokens"]):
            GamePlayer.objects.create(game=game, user=user, position=i)

        return game


class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = ["value", "suit", "drawn_datetime", "chug_duration_ms", "chug_id"]

    drawn_datetime = serializers.DateTimeField()
    chug_duration_ms = serializers.IntegerField(
        required=False, source="chug.duration_in_milliseconds"
    )
    chug_id = serializers.IntegerField(read_only=True, source="chug.id")

    def validate_chug_duration_ms(self, value):
        if value < 0:
            raise serializers.ValidationError("Chug duration must be positive")

        return value

    def validate(self, data):
        if data["value"] != 14 and data.get("chug_duration_ms"):
            raise serializers.ValidationError(
                {
                    "chug_duration_ms": f"Chug data on non-ace: {data['value']} {data['suit']}"
                }
            )
        return data


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = [
            "id",
            "start_datetime",
            "end_datetime",
            "description",
            "official",
            "dnf",
            "cards",
            "seed",
            "player_ids",
            "player_names",
            "sips_per_beer",
            "description_html",
        ]

    start_datetime = serializers.DateTimeField(required=False)
    official = serializers.BooleanField(required=True)
    cards = CardSerializer(many=True)
    seed = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    player_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True
    )
    player_names = serializers.ListField(child=serializers.CharField(), write_only=True)
    description_html = serializers.SerializerMethodField()

    hashtag_re = re.compile(r"#([^# ]+)")

    def get_description_html(self, obj):
        def hashtag_link(m):
            s = m.group()
            url = reverse("game_list") + "?" + urlencode({"query": s})
            return format_html("<a href='{}'>{}</a>", url, s)

        return self.hashtag_re.sub(hashtag_link, obj.description)

    def validate(self, data):
        DEFAULT = object()

        def check_field(field, default=None, new_value=DEFAULT):
            value = getattr(self.instance, field)
            if new_value is DEFAULT:
                new_value = data.get(field, default)
            if value != default and value != new_value:
                if new_value == default:
                    raise serializers.ValidationError(
                        {field: "Missing even though server has it"}
                    )
                else:
                    raise serializers.ValidationError(
                        {
                            field: f"Differs from server value: {repr(value)} != {repr(new_value)}"
                        }
                    )

        if self.instance.has_ended:
            raise serializers.ValidationError({"non_field_errors": "Game has finished"})

        check_field("end_datetime")
        check_field("official")
        check_field("description", "")

        cards = self.instance.ordered_cards()
        new_cards = data["cards"]

        previous_cards = len(cards)

        player_count = len(data["player_names"])
        instance_player_count = self.instance.players.count()
        if instance_player_count > 0:
            if player_count != instance_player_count:
                raise serializers.ValidationError(
                    {
                        "player_names": f"Number of players doesn't match server: {instance_player_count} != {player_count}"
                    }
                )

            player_ids = [p.id for p in self.instance.ordered_players()]
            if data["player_ids"] != player_ids:
                raise serializers.ValidationError(
                    {
                        "player_ids": f"Player ids doesn't match server: {player_ids} != {data['player_ids']}"
                    }
                )

        seed = data["seed"]
        if not is_seed_valid_for_players(seed, player_count):
            raise serializers.ValidationError({"seed": "Invalid seed"})
        seed_cards = Card.get_shuffled_deck(player_count, seed)

        if len(cards) > len(new_cards):
            raise serializers.ValidationError(
                {"cards": "More cards in database than provided"}
            )

        if len(new_cards) > len(seed_cards):
            raise serializers.ValidationError(
                {"cards": "More cards than expected for the game"}
            )

        final_update = "end_datetime" in data

        if final_update and len(new_cards) < len(seed_cards):
            raise serializers.ValidationError(
                {"cards": "Can't end game before drawing every card"}
            )

        increasing_datetimes = [
            self.instance.start_datetime,
            *(d["drawn_datetime"] for d in new_cards),
        ]
        end_dt = data.get("end_datetime")
        if end_dt:
            increasing_datetimes.append(end_dt)

        previous_dt = None
        extra_time = datetime.timedelta()
        for dt in increasing_datetimes:
            dt += extra_time
            if previous_dt and dt < previous_dt:
                if self.context.get("fix_times"):
                    time_increase = previous_dt - dt + datetime.timedelta(seconds=13)
                    print(f"Moving time forward by {time_increase}")
                    extra_time += time_increase
                    dt += time_increase
                else:
                    raise serializers.ValidationError(
                        {"cards": "Card times are not increasing"}
                    )

            previous_dt = dt

        for i, card_data in enumerate(new_cards):
            if card_data["value"] == 14 and "chug" not in card_data:
                if i != len(new_cards) - 1 or final_update:
                    raise serializers.ValidationError(
                        {"cards": f"Card {i} has missing chug data"}
                    )

        for i, (card, card_data) in enumerate(zip(cards, new_cards)):
            if (card.value, card.suit, card.drawn_datetime) != (
                card_data["value"],
                card_data["suit"],
                card_data["drawn_datetime"],
            ):
                raise serializers.ValidationError(
                    {"cards": f"Card {i} has different data than server"}
                )

            chug = getattr(card, "chug", None)
            chug_data = card_data.get("chug", {}).get("duration_in_milliseconds")
            if (chug and chug_data and chug.duration_in_milliseconds != chug_data) or (
                chug and not chug_data
            ):
                raise serializers.ValidationError(
                    {"cards": f"Card {i} has different chug data than server"}
                )

            if not chug and chug_data:
                assert i == len(cards) - 1

        for i, (seed_card, card_data) in enumerate(
            zip(seed_cards[previous_cards:], new_cards[previous_cards:])
        ):
            if seed_card != (card_data["value"], card_data["suit"]):
                raise serializers.ValidationError(
                    {
                        "cards": f"Card {previous_cards + i} has different data than seed would generate"
                    }
                )

        return data


class GameSerializerWithPlayerStats(GameSerializer):
    class Meta(GameSerializer.Meta):
        fields = GameSerializer.Meta.fields + ["player_stats"]

    player_stats = serializers.SerializerMethodField()

    def get_player_stats(self, obj):
        l = []
        for stats in obj.get_player_stats():
            for k, v in stats.items():
                if isinstance(v, datetime.timedelta):
                    stats[k] = v.total_seconds() * 1000
            stats["id"] = obj.id
            l.append(stats)

        return l


class PlayerStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerStat
        fields = [
            "season_number",
            "total_games",
            "total_time_played_seconds",
            "total_sips",
            "best_game",
            "worst_game",
            "best_game_sips",
            "worst_game_sips",
            "total_chugs",
            "fastest_chug",
            "fastest_chug_duration_ms",
            "average_chug_time_seconds",
        ]

    fastest_chug_duration_ms = serializers.IntegerField(
        required=False, source="fastest_chug.duration_in_milliseconds"
    )
