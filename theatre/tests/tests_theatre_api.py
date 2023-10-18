from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from theatre.models import Play, Actor, Genre
from theatre.serializers import PlayListSerializer, PlayDetailSerializer

PLAY_URL = reverse("theatre:play-list")
PERFORMANCE_URL = reverse("theatre:performance-list")


def sample_play(**params):
    defaults = {
        "title": "Sample play",
        "description": "Sample description",
    }
    defaults.update(params)
    return Play.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def detail_url(play_id):
    return reverse("theatre:play-detail", args=[play_id])


class UnauthenticatedTheatreApiTest(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(PLAY_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTheatreApiTest(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass1"
        )
        self.client.force_authenticate(self.user)

    def test_list_plays(self):
        sample_play()
        play_with_actors_and_genres = sample_play()
        actor = sample_actor(
            first_name="Olga",
            last_name="Sumska"
        )
        genre = sample_genre(name="drama")
        play_with_actors_and_genres.actors.add(actor)
        play_with_actors_and_genres.genres.add(genre)
        res = self.client.get(PLAY_URL)
        plays = Play.objects.all()
        serializer = PlayListSerializer(plays, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_play_by_actors(self):
        play1 = sample_play()
        play2 = sample_play()

        actor1 = sample_actor(first_name="Olga", last_name="Sumska")
        actor2 = sample_actor(first_name="Bruce", last_name="Lee")

        play1.actors.add(actor1)
        play2.actors.add(actor2)

        play3 = sample_play()

        res = self.client.get(PLAY_URL, {"actors": f"{actor1.id},{actor2.id}"})

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_play_by_genres_ids(self):
        play1 = sample_play()
        play2 = sample_play()

        genre1 = sample_genre(name="drama")
        genre2 = sample_genre(name="comedy")

        play1.genres.add(genre1)
        play2.genres.add(genre2)

        play3 = sample_play()

        res = self.client.get(PLAY_URL, {"genres": f"{genre1.id},{genre2.id}"})

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_play_detail(self):
        play = sample_play()
        genre = sample_genre(name="drama")
        actor = sample_actor(first_name="Olga", last_name="Sumska")
        play.genres.add(genre)
        play.actors.add(actor)

        url = detail_url(play.id)

        res = self.client.get(url)

        serializer = PlayDetailSerializer(play)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_play_forbidden(self):
        payload = {
            "title": "Play",
            "description": "Some description",
        }

        res = self.client.post(PLAY_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminPlayApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="testpass",
            is_staff=True

        )
        self.client.force_authenticate(self.user)

    def test_create_play(self):
        payload = {
            "title": "Play",
            "description": "Some description",
        }

        res = self.client.post(PLAY_URL, payload)
        play = Play.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(play, key))

    def test_create_play_with_actor_and_genres(self):
        genre1 = sample_genre(name="drama")
        genre2 = sample_genre(name="comedy")

        actor1 = sample_actor(first_name="Olga", last_name="Sumska")
        actor2 = sample_actor(first_name="Bruce", last_name="Lee")

        payload = {
            "title": "Movie",
            "description": "Some description",
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id]
        }

        res = self.client.post(PLAY_URL, payload)

        play = Play.objects.get(id=res.data["id"])

        actors = play.actors.all()
        genres = play.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(actors.count(), 2)
        self.assertEqual(genres.count(), 2)

        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)

        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)

    def test_delete_play_not_allowed(self):
        play = sample_play()
        url = detail_url(play.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
