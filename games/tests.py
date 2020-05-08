import concurrent.futures
import datetime
from copy import deepcopy

from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from games.models import Card, Chug, Game, User
from games.utils import get_milliseconds


class ApiTest(TransactionTestCase):
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
        if expected_status:
            self.assert_status(r, expected_status)
        return r

    def get_game_data(self, cards_drawn, include_chug=True):
        game_state = deepcopy(self.final_game_data)
        game_state["has_ended"] = False
        del game_state["description"]

        game_state["cards"] = game_state["cards"][:cards_drawn]
        if not include_chug:
            try:
                del game_state["cards"][-1]["chug_start_start_delta_ms"]
                del game_state["cards"][-1]["chug_end_start_delta_ms"]
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
        self.game_token = r.data["token"]
        self.game_start = datetime.datetime.fromisoformat(r.data["start_datetime"])

        self.final_game_data = {
            "start_datetime": self.game_start,
            "official": True,
            "seed": self.SEED,
            "cards": [],
            "player_ids": [self.u1.id, self.u2.id],
            "player_names": [self.u1.username, self.u2.username],
            "has_ended": True,
        }

        delta = 0

        for value, suit in Card.get_ordered_cards_for_players(self.PLAYER_COUNT):
            delta += 1
            card_data = {
                "value": value,
                "suit": suit,
                "start_delta_ms": get_milliseconds(timezone.now() - self.game_start)
                + delta,
            }
            self.final_game_data["cards"].append(card_data)

            if value == Chug.VALUE:
                delta += 1
                card_data["chug_start_start_delta_ms"] = (
                    get_milliseconds(timezone.now() - self.game_start) + delta
                )
                delta += 1
                card_data["chug_end_start_delta_ms"] = (
                    get_milliseconds(timezone.now() - self.game_start) + delta
                )

        self.final_game_data["description"] = "foo"

    def set_token(self, token):
        self.client.credentials(HTTP_AUTHORIZATION="GameToken " + token)

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

    def test_correct_final(self):
        self.set_token(self.game_token)
        self.update_game(self.final_game_data)
        game = Game.objects.get(id=self.game_id)

        for f in ["start_datetime", "official", "has_ended"]:
            self.assertEqual(getattr(game, f), self.final_game_data[f])

        self.assertEqual(game.cards.count(), len(self.final_game_data["cards"]))
        for card, card_data in zip(game.cards.all(), self.final_game_data["cards"]):
            for f in ["value", "suit", "start_delta_ms"]:
                self.assertEqual(getattr(card, f), card_data[f])

            self.assertEqual(hasattr(card, "chug"), card.value == 14)
            if card.value == 14:
                self.assertEqual(
                    card.chug.start_start_delta_ms,
                    card_data["chug_start_start_delta_ms"],
                )
                self.assertEqual(
                    card.chug.duration_ms,
                    card_data["chug_end_start_delta_ms"]
                    - card_data["chug_start_start_delta_ms"],
                )

    def test_send_final(self):
        self.set_token(self.game_token)
        self.update_game(self.final_game_data)
        # Can't update the game once it's finished
        self.update_game(self.final_game_data, 400)

    def send_all_updates(self, send_without_chug, send_with_chug):
        self.set_token(self.game_token)
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
        self.set_token(self.game_token)

        game_data = self.get_game_data(1)
        game_data["cards"][0]["value"] = 3

        self.update_game(game_data, 400)

    def test_end_game_early(self):
        self.set_token(self.game_token)

        game_data = self.get_game_data(5)
        game_data["description"] = "!"
        game_data["has_ended"] = True
        self.update_game(game_data, 400)

    def test_end_game_early_missing_chug(self):
        self.set_token(self.game_token)

        game_data = self.final_game_data
        del game_data["cards"][-1]["chug_end_start_delta_ms"]

        self.update_game(game_data, 400)

    def test_no_credentials(self):
        self.update_game(self.final_game_data, 403)

    def test_wrong_credentials(self):
        r = self.client.post("/api/games/", {"tokens": [self.t2, self.t3]})
        self.set_token(r.data["token"])
        self.update_game(self.final_game_data, 403)

    def test_send_less_cards(self):
        self.set_token(self.game_token)
        game_data = self.get_game_data(5)
        self.update_game(game_data)
        game_data = self.get_game_data(4)
        self.update_game(game_data, 400)

    def test_send_different_start_time(self):
        self.set_token(self.game_token)
        game_data = self.get_game_data(10)
        game_data["start_datetime"] = game_data["start_datetime"] - datetime.timedelta(
            seconds=1
        )
        self.update_game(game_data, 400)
        game_data["start_datetime"] = game_data["start_datetime"] + datetime.timedelta(
            seconds=1
        )
        self.update_game(game_data)

    def test_send_different_official(self):
        self.set_token(self.game_token)
        game_data = self.get_game_data(17)
        game_data["official"] = False
        self.update_game(game_data, 400)

    def test_send_decreasing_times(self):
        self.set_token(self.game_token)
        game_data = self.get_game_data(17)
        game_data["cards"][14]["start_delta_ms"] = game_data["cards"][2][
            "start_delta_ms"
        ]
        self.update_game(game_data, 400)

    def test_concurrent_update(self):
        self.set_token(self.game_token)
        game_data = self.get_game_data(24)

        def send_game_data():
            return self.update_game(game_data, None)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            f1 = executor.submit(send_game_data)
            f2 = executor.submit(send_game_data)

            s1 = f1.result().status_code
            s2 = f2.result().status_code

            self.assertLessEqual({s1, s2}, {200, 503}, [s1, s2])

    def test_non_integer_game_id(self):
        r = self.client.get("/api/games/foo/")
        self.assertEqual(r.status_code, 404)
        r = self.client.get("/api/stats/foo/")
        self.assertEqual(r.status_code, 404)

    def test_negative_times(self):
        self.set_token(self.game_token)
        game_data = self.final_game_data
        game_data["cards"][0]["start_delta_ms"] = -1
        self.update_game(game_data, 400)

    def test_dnf(self):
        self.set_token(self.game_token)
        game_data = self.get_game_data(5)
        game_data["dnf_player_ids"] = [self.u1.id]
        self.update_game(game_data)

        game = Game.objects.get(id=self.game_id)
        gp1 = game.gameplayer_set.get(user_id=self.u1)
        gp2 = game.gameplayer_set.get(user_id=self.u2)
        self.assertTrue(gp1.dnf)
        self.assertFalse(gp2.dnf)

        game_data["dnf_player_ids"] = [self.u2.id]
        self.update_game(game_data)

        gp1.refresh_from_db()
        gp2.refresh_from_db()
        self.assertFalse(gp1.dnf)
        self.assertTrue(gp2.dnf)
