import datetime
import re
from urllib.parse import urlencode

from django.urls import reverse
from django.utils.html import format_html
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from .models import Card, Chug, Game, GamePlayer, PlayerStat, User
from .shuffle_indices import generate_shuffle_indices_for_players


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
        tokens = validated_data["tokens"]
        shuffle_indices = generate_shuffle_indices_for_players(len(tokens))
        game = Game.objects.create(shuffle_indices=shuffle_indices)
        for i, user in enumerate(tokens):
            GamePlayer.objects.create(game=game, user=user, position=i)

        return game


CHUG_FIELDS = ["chug_start_start_delta_ms", "chug_end_start_delta_ms"]
STORED_CHUG_FIELDS = ["chug_start_start_delta_ms", "chug_duration_ms"]


class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = [
            "value",
            "suit",
            "start_delta_ms",
            "chug_start_start_delta_ms",
            "chug_end_start_delta_ms",
            "chug_duration_ms",
            "chug_id",
        ]

    start_delta_ms = serializers.IntegerField()
    chug_start_start_delta_ms = serializers.IntegerField(
        required=False, source="chug.start_start_delta_ms"
    )
    chug_end_start_delta_ms = serializers.IntegerField(required=False)
    chug_duration_ms = serializers.IntegerField(
        read_only=True, source="chug.duration_ms"
    )
    chug_id = serializers.IntegerField(read_only=True, source="chug.id")

    def validate(self, data):
        chug_start = data.get("chug", {}).get("start_start_delta_ms")
        if chug_start:
            data["chug_start_start_delta_ms"] = chug_start

        if data["value"] != Chug.VALUE:
            for f in CHUG_FIELDS:
                if f in data:
                    raise serializers.ValidationError(
                        {f: f"Chug data on non-ace: {data['value']} {data['suit']}"}
                    )

        if (
            "chug_end_start_delta_ms" in data
            and "chug_start_start_delta_ms" not in data
        ):
            raise serializers.ValidationError(
                {
                    "chug_start_start_delta_ms": "Must be provided, when chug_end_start_delta_ms is given"
                }
            )

        if "chug_end_start_delta_ms" in data:
            data["chug_duration_ms"] = (
                data["chug_end_start_delta_ms"] - data["chug_start_start_delta_ms"]
            )

        return data


class LocationSerializer(serializers.Serializer):
    latitude = serializers.FloatField(source="location_latitude")
    longitude = serializers.FloatField(source="location_longitude")
    accuracy = serializers.FloatField(source="location_accuracy")


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
            "shuffle_indices",
            "cards",
            "player_ids",
            "player_names",
            "players",
            "sips_per_beer",
            "has_ended",
            "description_html",
            "dnf_player_ids",
            "location",
            "image",
        ]

    start_datetime = serializers.DateTimeField(required=False)
    official = serializers.BooleanField(required=True)
    dnf = serializers.BooleanField(required=False, default=False)
    shuffle_indices = serializers.ListField(
        child=serializers.IntegerField(), read_only=True
    )
    cards = CardSerializer(many=True)
    player_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True
    )
    player_names = serializers.ListField(child=serializers.CharField(), write_only=True)
    players = serializers.SerializerMethodField()
    has_ended = serializers.BooleanField(required=True)
    description_html = serializers.SerializerMethodField()
    dnf_player_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=[]
    )
    location = LocationSerializer(required=False, source="*")

    hashtag_re = re.compile(r"#([^# ]+)")

    def get_description_html(self, obj):
        def hashtag_link(m):
            s = m.group()
            url = reverse("game_list") + "?" + urlencode({"query": s})
            return format_html("<a href='{}'>{}</a>", url, s)

        return self.hashtag_re.sub(hashtag_link, obj.description)

    def get_players(self, obj):
        return [UserSerializer(p).data for p in obj.ordered_players()]

    def validate(self, data):
        DEFAULT = object()
        allow_overwrite = self.context.get("allow_overwrite")

        def check_field(field, default=None, new_value=DEFAULT):
            value = getattr(self.instance, field)
            if new_value is DEFAULT:
                new_value = data.get(field, default)
            if value != default and value != new_value:
                if new_value == default:
                    raise serializers.ValidationError(
                        {field: "Missing even though server has it"}
                    )
                elif not allow_overwrite:
                    raise serializers.ValidationError(
                        {
                            field: f"Differs from server value: {repr(value)} != {repr(new_value)}"
                        }
                    )

        if self.instance.has_ended and not self.context.get("ignore_finished"):
            raise serializers.ValidationError({"non_field_errors": "Game has finished"})

        if not (set(data["dnf_player_ids"]) <= set(data["player_ids"])):
            raise serializers.ValidationError(
                {"dnf_player_ids": "dnf_player_ids is not a subset of player_ids"}
            )

        check_field("start_datetime")
        check_field("end_datetime")
        check_field("official")
        check_field("description", "")

        if self.context.get("fix_player_ids"):
            for i, (player_id, player_name) in enumerate(
                zip(data["player_ids"], data["player_names"])
            ):
                if player_id == -1:
                    try:
                        data["player_ids"][i] = User.objects.get(
                            username_iexact=player_name
                        ).id
                    except User.DoesNotExist:
                        raise serializers.ValidationError(
                            {
                                "player_name": f"Player with username {player_name} not found"
                            }
                        )

        for i, player_id in enumerate(data["player_ids"]):
            try:
                User.objects.get(id=player_id)
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    {"player_ids": f"Player with id {player_id} not found"}
                )

        cards = self.instance.ordered_cards()
        new_cards = data["cards"]

        ended = data["has_ended"]
        dnf = data["dnf"]
        completed = ended and not dnf
        if not completed and data.get("description") is not None:
            raise serializers.ValidationError(
                {"description": "Can't set description before game has ended"}
            )

        if dnf and not ended:
            raise serializers.ValidationError(
                {"dnf": "has_ended must be true if dnf is true"}
            )

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

        shuffled_cards = self.instance.get_shuffled_deck()

        if len(cards) > len(new_cards):
            raise serializers.ValidationError(
                {"cards": "More cards in database than provided"}
            )

        if shuffled_cards:
            if len(new_cards) > len(shuffled_cards):
                raise serializers.ValidationError(
                    {"cards": "More cards than expected for the game"}
                )

            if completed and len(new_cards) < len(shuffled_cards):
                raise serializers.ValidationError(
                    {"cards": "Can't end game before drawing every card"}
                )

        increasing_deltas = []
        for card_data in new_cards:
            increasing_deltas.append(card_data["start_delta_ms"])

            for f in CHUG_FIELDS:
                if f in card_data:
                    increasing_deltas.append(card_data[f])

        previous_delta = None
        extra_time = 0
        for i, delta in enumerate(increasing_deltas):
            if delta < 0 and not self.context.get("fix_times"):
                raise serializers.ValidationError(
                    {"cards": "Card times are not non-negative"}
                )

            delta += extra_time
            if previous_delta and delta < previous_delta:
                if self.context.get("fix_times"):
                    time_increase = previous_delta - delta + 13 * 1000
                    print(f"Moving time forward by {time_increase} ms")
                    extra_time += time_increase
                    delta += time_increase
                else:
                    raise serializers.ValidationError(
                        {
                            "cards": f"Card times are not increasing: {delta} < {previous_delta} ({i - 1}, {i})"
                        }
                    )

            increasing_deltas[i] = delta
            previous_delta = delta

        if self.context.get("fix_times"):
            g = iter(increasing_deltas)
            for card_data in new_cards:
                card_data["start_delta_ms"] = next(g)

                for f in CHUG_FIELDS:
                    if f in card_data:
                        card_data[f] = next(g)

                if "chug_duration_ms" in card_data:
                    card_data["chug_duration_ms"] = (
                        card_data["chug_end_start_delta_ms"]
                        - card_data["chug_start_start_delta_ms"]
                    )

        for i, card_data in enumerate(new_cards):
            if card_data["value"] == 14 and "chug_end_start_delta_ms" not in card_data:
                if i != len(new_cards) - 1 or completed:
                    raise serializers.ValidationError(
                        {"cards": f"Card {i} has missing chug data"}
                    )

        if completed:
            last_card = new_cards[-1]
            if hasattr(self, "chug"):
                end_start_delta_ms = (
                    last_card["start_start_delta_ms"] + last_card["chug.duration_ms"]
                )
            else:
                end_start_delta_ms = last_card["start_delta_ms"]

            data["end_datetime"] = data["start_datetime"] + datetime.timedelta(
                milliseconds=end_start_delta_ms
            )

        for i, (card, card_data) in enumerate(zip(cards, new_cards)):
            if (card.value, card.suit, card.start_delta_ms) != (
                card_data["value"],
                card_data["suit"],
                card_data["start_delta_ms"],
            ) and not allow_overwrite:
                raise serializers.ValidationError(
                    {"cards": f"Card {i} has different data than server"}
                )

            chug = getattr(card, "chug", None)
            if chug:
                chug_data = {k: getattr(chug, k, None) for k in STORED_CHUG_FIELDS}
                new_chug_data = {k: card_data.get(k) for k in STORED_CHUG_FIELDS}
                if not chug_data:
                    raise serializers.ValidationError(
                        {"cards": f"Card {i} has missing chug data"}
                    )

                for f in STORED_CHUG_FIELDS:
                    if chug_data[f] and not new_chug_data[f]:
                        raise serializers.ValidationError(
                            {"cards": f"Card {i} has missing chug_data"}
                        )

                    if (
                        chug_data[f]
                        and new_chug_data[f]
                        and chug_data[f] != new_chug_data
                    ) and not allow_overwrite:
                        raise serializers.ValidationError(
                            {"cards": f"Card {i} has different chug data than server"}
                        )

                if not chug and chug_data:
                    assert i == len(cards) - 1

        if shuffled_cards:
            for i, (shuffled_card, card_data) in enumerate(
                zip(shuffled_cards[previous_cards:], new_cards[previous_cards:])
            ):
                if shuffled_card != (card_data["value"], card_data["suit"]):
                    raise serializers.ValidationError(
                        {
                            "cards": f"Card {previous_cards + i} is different than expected from shuffle_indices"
                        }
                    )

        return data


class GameSerializerWithPlayerStats(GameSerializer):
    class Meta(GameSerializer.Meta):
        fields = GameSerializer.Meta.fields + ["player_stats"]

    player_stats = serializers.SerializerMethodField()

    def get_player_stats(self, obj):
        res = []
        for stats in obj.get_player_stats():
            for k, v in stats.items():
                if isinstance(v, datetime.timedelta):
                    stats[k] = v.total_seconds() * 1000
            res.append(stats)

        return res


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
        required=False, source="fastest_chug.duration_ms"
    )
