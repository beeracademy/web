from django.test import TestCase
from rest_framework.test import APIClient
from games.models import User, Game, Card
import datetime


class ApiTest(TestCase):
	def create_user(self, client, username, password):
		u = User.objects.create(username=username)
		u.set_password(password)
		u.save()

		r = client.post('/api-token-auth/', {
			'username': username,
			'password': password,
		})
		self.assertEqual(r.status_code, 200)

		token = r.data['token']
		return u, token


	def setUp(self):
		self.client = APIClient()
		self.u1, self.t1 = self.create_user(self.client, 'Player1', 'test1')
		self.u2, self.t2 = self.create_user(self.client, 'Player2', 'test2')
		r = self.client.post('/api/games/', {
			'tokens': [self.t1, self.t2]
		})
		self.assertEqual(r.status_code, 200)
		self.game_id = r.data['id']


	def test_draw_cards(self):
		self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t1)
		r = self.client.post(f'/api/games/{self.game_id}/draw_card/')
		self.assertEqual(r.status_code, 200)

		self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t1)
		r = self.client.post(f'/api/games/{self.game_id}/draw_card/')
		self.assertEqual(r.status_code, 403)

		self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t2)
		r = self.client.post(f'/api/games/{self.game_id}/draw_card/')
		self.assertEqual(r.status_code, 200)


	def test_register_chug(self):
		Card.objects.create(
			game=Game.objects.get(id=self.game_id),
			value=14,
			suit='S',
		)

		self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t2)
		r = self.client.post(f'/api/games/{self.game_id}/register_chug/', {
			'duration_in_milliseconds': 12345,
		})
		self.assertEqual(r.status_code, 403)

		self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t1)
		r = self.client.post(f'/api/games/{self.game_id}/register_chug/', {
			'duration_in_milliseconds': 12345,
		})
		self.assertEqual(r.status_code, 200)


	def test_player_order(self):
		game = Game.objects.get(id=self.game_id)
		self.assertEqual(game.ordered_players(), [self.u1, self.u2])

		r = self.client.post('/api/games/', {
			'tokens': [self.t2, self.t1]
		})
		self.assertEqual(r.status_code, 200)
		game2 = Game.objects.get(id=r.data['id'])
		self.assertEqual(game2.ordered_players(), [self.u2, self.u1])


	def test_end_game(self):
		game = Game.objects.get(id=self.game_id)

		for value, suit in game.get_all_cards():
			Card.objects.create(
				game=game,
				value=value,
				suit=suit,
			)

			if value == 14:
				game.add_chug(12345)


		self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t2)
		r = self.client.post(f'/api/games/{self.game_id}/end_game/', {
			'description': 'foo',
			'end_datetime': datetime.datetime.now().isoformat(),
		})
		self.assertEqual(r.status_code, 200)

		game.refresh_from_db()
		self.assertEqual(game.description, 'foo')


	def test_negative_chug(self):
		Card.objects.create(
			game=Game.objects.get(id=self.game_id),
			value=14,
			suit='S',
		)

		self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t1)
		r = self.client.post(f'/api/games/{self.game_id}/register_chug/', {
			'duration_in_milliseconds': -100,
		})
		self.assertEqual(r.status_code, 400)
