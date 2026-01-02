from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_LIST_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    defaults = {
        "title": "test title",
        "description": "test description",
        "duration": 10,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_actor(**params):
    defaults = {
        "first_name": "test first name",
        "last_name": "test last name",
    }
    defaults.update(params)
    return Actor.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "test genre",
    }
    defaults.update(params)
    return Genre.objects.create(**defaults)


class TestMovieViewSetWithUnauthorizedUser(TestCase):
    def setUp(self):
        """Create unauthorized user"""
        self.client = APIClient()

    def test_post_method(self):
        res = self.client.post(
            MOVIE_LIST_URL,
            data={
                "title": "test title",
                "description": "test description",
                "duration": 10,
            },
        )

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class TestMovieViewSetWithAuthorizedUser(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testosteronich",
        )
        self.client.force_authenticate(self.user)

    def test_get_list_method(self):
        sample_movie()

        res = self.client.get(MOVIE_LIST_URL)
        serializer = MovieListSerializer(Movie.objects.all(), many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_list_method_with_search(self):
        sample_movie()
        actor = sample_actor()
        genre = sample_genre()
        check = sample_movie(
            title="cool movie", description="cool movie description", duration=8
        )

        check.actors.add(actor)
        check.genres.add(genre)

        serializer = MovieListSerializer(Movie.objects.all(), many=True)
        detail_serializer = MovieListSerializer(check)

        for res in (
            self.client.get(MOVIE_LIST_URL, data={"title": "cool movie"}),
            self.client.get(MOVIE_LIST_URL, data={"actors": f"{actor.id}"}),
            self.client.get(MOVIE_LIST_URL, data={"genres": f"{genre.id}"}),
        ):
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertNotEqual(res.data, serializer.data)
            self.assertIn(detail_serializer.data, res.data)

    def test_get_detail_method(self):
        check = sample_movie()
        url = reverse("cinema:movie-detail", kwargs={"pk": check.id})

        res = self.client.get(url)
        serializer = MovieDetailSerializer(check)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_for_not_staff_user(self):
        actor = sample_actor()
        genre = sample_genre()

        res = self.client.post(
            MOVIE_LIST_URL,
            data={
                "title": "test title",
                "description": "test description",
                "duration": 10,
                "actors": [actor.id],
                "genres": [genre.id],
            },
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class TestMovieViewSetWithIsStaffUser(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.ad",
            password="the_best_admin",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_post_method_for_staff_user(self):
        actor = sample_actor()
        genre = sample_genre()

        res = self.client.post(
            MOVIE_LIST_URL,
            data={
                "title": "test title",
                "description": "test description",
                "duration": 10,
                "actors": [actor.id],
                "genres": [genre.id],
            },
        )
        check = self.client.get(MOVIE_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(check.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], check.data[0]["id"])
