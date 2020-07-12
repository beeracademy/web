import concurrent.futures
import datetime
from copy import deepcopy
from threading import Lock
from time import sleep
from unittest.mock import patch

from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from games.models import Card, Chug, Game, OneTimePassword, User
from games.serializers import GameSerializer
from games.utils import get_milliseconds
from games.views import update_game


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

    def authenticate(self, username, password, expected_status=200):
        r = self.client.post(
            "/api-token-auth/", {"username": username, "password": password}
        )
        self.assert_status(r, expected_status)
        return r.data

    def create_user(self, username, password):
        u = User.objects.create(username=username)
        u.set_password(password)
        u.save()

        token = self.authenticate(username, password)["token"]
        return u, token

    def update_game(
        self, game_data, expected_status=200, game_id=None, game_token=None
    ):
        if not game_id:
            game_id = self.game_id

        extra = {}
        if game_token:
            extra["HTTP_AUTHORIZATION"] = "GameToken " + game_token

        r = self.client.post(
            f"/api/games/{game_id}/update_state/", game_data, format="json", **extra,
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

    def create_game(self, tokens):
        r = self.client.post("/api/games/", {"tokens": tokens})
        self.assert_ok(r)
        return r.data

    def setUp(self):
        self.client = APIClient()

        self.u1, self.t1 = self.create_user("Player1", "test1")
        self.u2, self.t2 = self.create_user("Player2", "test2")
        self.u3, self.t3 = self.create_user("Player3", "test3")

        game_data = self.create_game([self.t1, self.t2])

        self.game_id = game_data["id"]
        self.game_token = game_data["token"]
        self.game_start = datetime.datetime.fromisoformat(game_data["start_datetime"])

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

        game_data = self.create_game([self.t2, self.t1])
        game2 = Game.objects.get(id=game_data["id"])
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

    def _test_fix_times(self, game_data):
        game = Game.objects.get(id=self.game_id)
        self.assertFalse(GameSerializer(game, data=game_data).is_valid())
        s = GameSerializer(game, data=game_data, context={"fix_times": True})
        self.assertTrue(s.is_valid())
        self.assertTrue(GameSerializer(game, data=s.validated_data).is_valid())

    def test_send_decreasing_times_fix_times(self):
        game_data = self.final_game_data
        game_data["cards"][14]["start_delta_ms"] = game_data["cards"][2][
            "start_delta_ms"
        ]
        self._test_fix_times(game_data)

    def test_send_decreasing_fix_times_chug_start(self):
        game_data = self.final_game_data
        aces = [c for c in game_data["cards"] if c["value"] == 14]
        aces[0]["chug_start_start_delta_ms"] = game_data["cards"][0]["start_delta_ms"]
        self._test_fix_times(game_data)

    def test_send_decreasing_fix_times_chug_end(self):
        game_data = self.final_game_data
        aces = [c for c in game_data["cards"] if c["value"] == 14]
        aces[0]["chug_end_start_delta_ms"] = aces[0]["chug_start_start_delta_ms"] - 1
        self._test_fix_times(game_data)

    def _update_games_concurrent(self, game_infos):
        def send_game_data(game_info):
            return self.update_game(
                game_info["data"],
                game_id=game_info["id"],
                game_token=game_info["token"],
            )

        lock = Lock()
        times_called = 0
        times_called_at_first_end = None

        def mocked_update_game(game, *args, **kwargs):
            nonlocal times_called, times_called_at_first_end
            with lock:
                times_called += 1
                first_time = times_called == 1

            # Sleep to allow other concurrent updates to finish before the first
            if first_time:
                sleep(0.5)

            update_game(game, *args, **kwargs)

            if first_time:
                with lock:
                    times_called_at_first_end = times_called

        with patch("games.views.update_game", mocked_update_game):
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(send_game_data, game_info)
                    for game_info in game_infos
                ]
                results = [f.result().status_code for f in futures]

                self.assertEqual(set(results), {200}, results)
                self.assertEqual(times_called, len(game_infos))

                return times_called_at_first_end

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_update(self):
        game_info = {
            "data": self.get_game_data(24),
            "id": self.game_id,
            "token": self.game_token,
        }
        times_called_at_first_end = self._update_games_concurrent([game_info] * 2)
        self.assertEqual(times_called_at_first_end, 1)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_update_different_game(self):

        orig_game_data2 = self.create_game([self.t1, self.t2])
        game_id2 = orig_game_data2["id"]
        game_token2 = orig_game_data2["token"]
        game_data2 = self.get_game_data(17)
        game_data2["start_datetime"] = orig_game_data2["start_datetime"]

        game_infos = [
            {
                "data": self.get_game_data(24),
                "id": self.game_id,
                "token": self.game_token,
            },
            {"data": game_data2, "id": game_id2, "token": game_token2},
        ]

        times_called_at_first_end = self._update_games_concurrent(game_infos)
        self.assertEqual(times_called_at_first_end, 2)

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

    def test_otp_can_only_use_once(self):
        otp, _ = OneTimePassword.objects.get_or_create(user=self.u1)
        self.authenticate(self.u1.username, otp.password)
        self.authenticate(self.u1.username, otp.password, 400)

        otp = OneTimePassword.objects.get(user=self.u1)
        self.authenticate(self.u1.username, otp.password)

    def test_merge_users(self):
        self.create_game([self.t2, self.t3])

        self.assertEqual(self.u1.games.count(), 1)
        self.assertEqual(self.u2.games.count(), 2)
        self.assertEqual(self.u3.games.count(), 1)

        self.u1.merge_with(self.u3)

        self.assertEqual(self.u1.games.count(), 2)
        self.assertEqual(self.u2.games.count(), 2)
        with self.assertRaises(User.DoesNotExist):
            self.u3.refresh_from_db()
