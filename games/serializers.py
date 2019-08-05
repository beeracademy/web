from rest_framework import serializers

# from rest_framework import generics
from rest_framework.authtoken.models import Token
from .models import User, Game, Card, GamePlayer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "is_superuser", "image", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User(username=validated_data["username"])
        user.set_password(validated_data["password"])
        user.save()
        return user


class GameInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ["id", "start_datetime"]


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


class CardUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = ["value", "suit", "drawn_datetime", "chug_duration_ms"]

    drawn_datetime = serializers.DateTimeField()
    chug_duration_ms = serializers.IntegerField(write_only=True, required=False)

    def validate_chug_duration_ms(self, value):
        if value < 0:
            raise serializers.ValidationError("Chug duration must be positive")

        return value

    def validate(self, data):
        if data["value"] != 14 and data.get("chug"):
            raise serializers.ValidationError(
                {"chug": f"Chug data on non-ace: {data['value']} {data['suit']}"}
            )
        return data


class GameUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = [
            "start_datetime",
            "end_datetime",
            "description",
            "official",
            "cards",
            "seed",
        ]

    start_datetime = serializers.DateTimeField(required=True)
    official = serializers.BooleanField(required=True)
    cards = CardUpdateSerializer(many=True)
    seed = serializers.ListField(child=serializers.IntegerField(), write_only=True)

    def __init__(self, game, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = game

    def validate(self, data):
        def check_field(field, default=None):
            value = getattr(self.game, field)
            new_value = data.get(field, default)
            if value != default and value != new_value:
                if new_value == default:
                    raise serializers.ValidationError(
                        {field: "Missing even though server has it"}
                    )
                else:
                    raise serializers.ValidationError(
                        {
                            field: "Differs from server value: {repr(value)} != {repr(new_value)}"
                        }
                    )

        if self.game.get_state() == Game.State.ENDED:
            raise serializers.ValidationError({"non_field_errors": "Game has finished"})

        check_field("start_datetime")
        check_field("end_datetime")
        check_field("official")
        check_field("description", "")

        cards = self.game.ordered_cards()
        new_cards = data["cards"]

        previous_cards = len(cards)

        seed = data["seed"]
        seed_cards = Card.get_shuffled_deck(self.game.players.count(), seed)

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
            data["start_datetime"],
            *(d["drawn_datetime"] for d in new_cards),
        ]
        end_dt = data.get("end_datetime")
        if end_dt:
            increasing_datetimes.append(end_dt)

        previous_dt = None
        for dt in increasing_datetimes:
            if previous_dt and dt < previous_dt:
                raise serializers.ValidationError(
                    {"cards": "Card times are not increasing"}
                )

            previous_dt = dt

        for i, card_data in enumerate(new_cards):
            if card_data["value"] == 14 and "chug_duration_ms" not in card_data:
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
            chug_data = card_data.get("chug_duration_ms")
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
