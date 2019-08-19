from django.test import TestCase, Client
from rest_framework.test import APIClient
from games.models import User, Game, Card, GamePlayer, Chug
from django.utils import timezone
from copy import deepcopy
import datetime


class ApiTest(TestCase):
    PLAYER_COUNT = 2
    TOTAL_CARDS = PLAYER_COUNT * 13

    # This seed is the identity permutation
    # Thus it will use the same order as Card.get_ordered_cards_for_players
    SEED = list(range(TOTAL_CARDS - 1, 0, -1))

    def assert_status(self, r, status):
        self.assertEqual(r.status_code, status, getattr(r, "data", None))

    def assert_ok(self, r, status=200):
        self.assert_status(r, 200)

    def create_user(self, client, username, password):
        u = User.objects.create(username=username)
        u.set_password(password)
        u.save()

        r = client.post(
            "/api-token-auth/", {"username": username, "password": password}
        )
        self.assert_ok(r)

        token = r.data["token"]
        return u, token

    def update_game(self, game_data, expected_status=200):
        r = self.client.post(
            f"/api/games/{self.game_id}/update_state/", game_data, format="json"
        )
        self.assert_status(r, expected_status)
        return r

    def get_game_data(self, cards_drawn, include_chug=True):
        game_state = deepcopy(self.final_game_data)
        del game_state["end_datetime"]
        del game_state["description"]

        game_state["cards"] = game_state["cards"][:cards_drawn]
        if not include_chug:
            try:
                game_state["cards"][-1]["chug_duration_ms"]
            except (IndexError, KeyError):
                pass

        return game_state

    def setUp(self):
        self.client = APIClient()

        self.u1, self.t1 = self.create_user(self.client, "Player1", "test1")
        self.u2, self.t2 = self.create_user(self.client, "Player2", "test2")
        self.u3, self.t3 = self.create_user(self.client, "Player3", "test3")
        r = self.client.post("/api/games/", {"tokens": [self.t1, self.t2]})
        self.assert_ok(r)

        self.game_id = r.data["id"]
        self.game_start = r.data["start_datetime"]

        self.final_game_data = {
            "start_datetime": self.game_start,
            "official": True,
            "seed": self.SEED,
            "cards": [],
        }

        for value, suit in Card.get_ordered_cards_for_players(self.PLAYER_COUNT):
            self.final_game_data["cards"].append(
                {"value": value, "suit": suit, "drawn_datetime": timezone.now()}
            )
            if value == 14:
                self.final_game_data["cards"][-1]["chug_duration_ms"] = 1234

        self.final_game_data["end_datetime"] = timezone.now()
        self.final_game_data["description"] = "foo"

    def set_token(self, token):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)

    def test_login(self):
        r = self.client.post(
            "/api-token-auth/", {"username": "Player1", "password": "test1"}
        )
        self.assert_ok(r)

    def test_login_wrong_password(self):
        r = self.client.post(
            "/api-token-auth/", {"username": "Player1", "password": "foobar"}
        )
        self.assert_status(r, 400)

    def test_login_no_such_user(self):
        r = self.client.post(
            "/api-token-auth/", {"username": "Foobar", "password": "foobar"}
        )
        self.assert_status(r, 404)

    def test_login_case_insensitive(self):
        r = self.client.post(
            "/api-token-auth/", {"username": "PLAYER1", "password": "test1"}
        )
        self.assert_ok(r)

    def test_login_case_insensitive_wrong_password(self):
        r = self.client.post(
            "/api-token-auth/", {"username": "PLAYER1", "password": "foobar"}
        )
        self.assert_status(r, 400)

    def test_player_order(self):
        game = Game.objects.get(id=self.game_id)
        self.assertEqual(game.ordered_players(), [self.u1, self.u2])

        r = self.client.post("/api/games/", {"tokens": [self.t2, self.t1]})
        self.assert_ok(r)
        game2 = Game.objects.get(id=r.data["id"])
        self.assertEqual(game2.ordered_players(), [self.u2, self.u1])

    def test_send_final(self):
        self.set_token(self.t1)
        self.update_game(self.final_game_data)
        # Can't update the game once it's finished
        self.update_game(self.final_game_data, 400)

    def send_all_updates(self, send_without_chug, send_with_chug):
        self.set_token(self.t1)
        for i in range(0, self.TOTAL_CARDS + 1):
            if send_without_chug:
                game_data = self.get_game_data(i, False)
                self.update_game(game_data)

            if send_with_chug:
                game_data = self.get_game_data(i, True)
                self.update_game(game_data)

        self.update_game(self.final_game_data)

    def test_send_all(self):
        self.send_all_updates(True, True)

    def test_send_all_without_chug(self):
        self.send_all_updates(True, False)

    def test_send_all_with_chug(self):
        self.send_all_updates(False, True)

    def test_send_wrong_card(self):
        self.set_token(self.t1)

        game_data = self.get_game_data(1)
        game_data["cards"][0]["value"] = 3

        self.update_game(game_data, 400)

    def test_end_game_early(self):
        self.set_token(self.t1)

        game_data = self.get_game_data(5)
        game_data["end_datetime"] = timezone.now()
        game_data["description"] = "!"
        self.update_game(game_data, 400)

    def test_end_game_early_missing_chug(self):
        self.set_token(self.t1)

        game_data = self.final_game_data
        del game_data["cards"][-1]["chug_duration_ms"]

        self.update_game(game_data, 400)

    def test_no_credentials(self):
        self.update_game(self.final_game_data, 403)

    def test_wrong_credentials(self):
        self.set_token(self.t3)
        self.update_game(self.final_game_data, 403)

    def test_send_less_cards(self):
        self.set_token(self.t1)
        game_data = self.get_game_data(5)
        self.update_game(game_data)
        game_data = self.get_game_data(4)
        self.update_game(game_data, 400)

    def test_send_different_start_time(self):
        self.set_token(self.t1)
        game_data = self.get_game_data(10)
        game_data["start_datetime"] = datetime.datetime.fromisoformat(
            game_data["start_datetime"]
        ) - datetime.timedelta(seconds=1)
        self.update_game(game_data, 400)

    def test_send_different_official(self):
        self.set_token(self.t1)
        game_data = self.get_game_data(17)
        game_data["official"] = False
        self.update_game(game_data, 400)

    def test_send_decreasing_times(self):
        self.set_token(self.t1)
        game_data = self.get_game_data(17)
        game_data["cards"][14]["drawn_datetime"] = game_data["cards"][2][
            "drawn_datetime"
        ]
        self.update_game(game_data, 400)

    def test_wrong_end_datetime(self):
        self.set_token(self.t1)
        game_data = self.final_game_data
        game_data["end_datetime"] = game_data["cards"][-2]["drawn_datetime"]
        self.update_game(game_data, 400)


class GameViewTest(TestCase):
    def setUp(self):
        self.player1 = User.objects.create(username="Player1")
        self.player2 = User.objects.create(username="Player2")
        self.game = Game.objects.create(start_datetime=timezone.now())

        GamePlayer.objects.create(game=self.game, user=self.player1, position=0)
        GamePlayer.objects.create(game=self.game, user=self.player2, position=1)

        for i, (value, suit) in enumerate(Card.get_ordered_cards_for_players(2)):
            card = Card.objects.create(
                game=self.game,
                index=i,
                value=value,
                suit=suit,
                drawn_datetime=timezone.now(),
            )
            if value == 14:
                Chug.objects.create(card=card, duration_in_milliseconds=12345)

        self.game.end_datetime = timezone.now()
        self.game.save()

        self.client = Client()

    def assert_can_render_pages(self):
        r = self.client.get(f"/games/")
        self.assertEqual(r.status_code, 200)
        r = self.client.get(f"/games/{self.game.id}/")
        self.assertEqual(r.status_code, 200)

    def test_normal_game(self):
        self.assert_can_render_pages()

    def test_live_game(self):
        self.game.end_datetime = None
        self.game.save()
        self.assert_can_render_pages()

    def test_game_without_card_times(self):
        for c in self.game.ordered_cards():
            c.drawn_datetime = None
            c.save()

        self.assert_can_render_pages()

    def test_game_without_start_time_and_card_times(self):
        for c in self.game.ordered_cards():
            c.drawn_datetime = None
            c.save()

        self.game.start_datetime = None
        self.game.save()
        self.assert_can_render_pages()
