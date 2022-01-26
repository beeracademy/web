from django.test import Client, TestCase
from django.utils import timezone

from games.models import Card, Chug, Game, GamePlayer, User
from games.utils import get_milliseconds
from games.views import update_stats_on_game_finished


def create_game(self):
    self.player1 = User.objects.create(username="Player1")
    self.player2 = User.objects.create(username="Player2")
    self.game = Game.objects.create(start_datetime=timezone.now())

    GamePlayer.objects.create(game=self.game, user=self.player1, position=0)
    GamePlayer.objects.create(game=self.game, user=self.player2, position=1)

    delta = 0

    for i, (value, suit) in enumerate(Card.get_ordered_cards_for_players(2)):
        card = Card.objects.create(
            game=self.game,
            index=i,
            value=value,
            suit=suit,
            start_delta_ms=get_milliseconds(timezone.now() - self.game.start_datetime)
            + delta,
        )
        if value == 14:
            Chug.objects.create(card=card, duration_ms=12345)

    self.game.end_datetime = timezone.now()
    self.game.save()

    update_stats_on_game_finished(self.game)

    self.client = Client()


class GameViewTest(TestCase):
    def setUp(self):
        create_game(self)

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
            c.start_delta_ms = None
            c.save()

        self.assert_can_render_pages()

    def test_game_without_start_time_and_card_times(self):
        for c in self.game.ordered_cards():
            c.start_delta_ms = None
            c.save()

        self.game.start_datetime = None
        self.game.save()
        self.assert_can_render_pages()


class ViewTest(TestCase):
    def assert_can_render_pages(self):
        URLS = [
            "/",
            "/about/",
            "/games/",
            "/upload_game/",
            "/players/",
            "/ranking/",
            "/stats/",
            "/login/",
        ]
        REDIRECT_URLS = [
            "/settings/",
            "/logout/",
        ]

        for url in URLS:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)

        for url in REDIRECT_URLS:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)

    def test_with_no_games(self):
        self.assert_can_render_pages()

    def test_with_one_game(self):
        create_game(self)
        self.assert_can_render_pages()

    def test_player_detail_with_no_game(self):
        self.player1 = User.objects.create(username="Player1")
        r = self.client.get(f"/players/{self.player1.id}/")
        self.assertEqual(r.status_code, 200)

    def test_player_detail_with_one_game(self):
        create_game(self)
        r = self.client.get(f"/players/{self.player1.id}/")
        self.assertEqual(r.status_code, 200)


class WebPushTest(TestCase):
    def post_subscribe(self):
        return self.client.post(
            "/webpush/save_information",
            {
                "status_type": "subscribe",
                "subscription": {
                    "endpoint": "https://example.org/",
                    "keys": {
                        "auth": "AAA",
                        "p256dh": "AAAA",
                    },
                },
                "user_agent": "Foo Bar",
                "browser": "firefox",
                "group": "new_games",
            },
            content_type="application/json",
        )

    def test_subscribe(self):
        u = User(username="test")
        u.set_password("test")
        u.save()

        r = self.post_subscribe()
        self.assertEqual(r.status_code, 201)

        r = self.client.login(username="test", password="test")
        self.assertTrue(r)

        r = self.post_subscribe()
        self.assertEqual(r.status_code, 201)

        self.client.logout()

        r = self.post_subscribe()
        self.assertEqual(r.status_code, 201)
