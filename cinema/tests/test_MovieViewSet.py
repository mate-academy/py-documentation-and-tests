from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


MOVIE_URL = reverse("cinema:movie-list")


class AnonymousUserTestBusAPI(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(
            res.status_code, status.HTTP_401_UNAUTHORIZED
        )


class AuthenticatedUserTestBusAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test_password"
        )
        self.client.force_authenticate(user=self.user)

        self.genre_1 = Genre.objects.create(name="Test_genre1")
        self.genre_2 = Genre.objects.create(name="Test_genre2")
        self.genre_3 = Genre.objects.create(name="Test_genre3")

        self.actor_1 = Actor.objects.create(
            first_name="Name1", last_name="Sur1"
        )
        self.actor_2 = Actor.objects.create(
            first_name="Name2", last_name="Sur2"
        )
        self.actor_3 = Actor.objects.create(
            first_name="Name3", last_name="Sur3"
        )

        self.data_set_movie_1 = {
            "title": "Test1",
            "description": "test description 1",
            "duration": 148,
        }

        self.data_set_movie_2 = {
            "title": "Test2",
            "description": "test description 2",
            "duration": 120,
        }
        self.data_set_movie_3 = {
            "title": "Test3",
            "description": "test description 3",
            "duration": 110,
        }

        self.movie_1 = Movie.objects.create(**self.data_set_movie_1)
        self.movie_1.genres.set([self.genre_1, self.genre_2])
        self.movie_1.actors.set([self.actor_1, self.actor_2])

        self.movie_2 = Movie.objects.create(**self.data_set_movie_2)
        self.movie_2.genres.set([self.genre_1])
        self.movie_2.actors.set([self.actor_2])

        self.movie_3 = Movie.objects.create(**self.data_set_movie_3)
        self.movie_3.genres.set([self.genre_2])
        self.movie_3.actors.set([self.actor_1])

    def test_movies_list(self):
        movies = Movie.objects.all()

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Movie.objects.count(), 3)

        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.data, serializer.data)

    def test_get_movies_by_title_filtering(self):
        res = self.client.get(MOVIE_URL, {"title": "Test3"})

        movies = Movie.objects.filter(title__icontains="Test3")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_get_movies_with_filter_by_partial_title(self):
        res = self.client.get(MOVIE_URL, {"title": "st3"})

        movies = Movie.objects.filter(title__icontains="st3")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_get_movies_by_genres_filtering(self):
        res = self.client.get(MOVIE_URL, {"genres": f"{self.genre_1.id}"})

        movies = Movie.objects.filter(genres__id__in=[self.genre_1.id])
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), len(serializer.data))
        self.assertEqual(res.data, serializer.data)

        res = self.client.get(MOVIE_URL, {"genres": f"{self.genre_3.id}"})
        self.assertEqual(len(res.data), 0)

    def test_get_movies_with_actors_filtering(self):
        res = self.client.get(MOVIE_URL, {"actors": f"{self.actor_1.id}"})
        self.assertEqual(len(res.data), 2)

        res = self.client.get(MOVIE_URL, {"actors": f"{self.actor_3.id}"})
        self.assertEqual(len(res.data), 0)

    def test_get_movie_detail(self):
        response = self.client.get(
            reverse("cinema:movie-detail", args=[self.movie_2.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Test2")
        self.assertEqual(response.data["description"], "test description 2")
        self.assertEqual(response.data["duration"], 120)
        self.assertEqual(response.data["genres"][0]["name"], "Test_genre1")
        self.assertEqual(response.data["actors"][0]["first_name"], "Name2")
        self.assertEqual(response.data["actors"][0]["last_name"], "Sur2")
        self.assertEqual(
            response.data["actors"][0]["full_name"], "Name2 Sur2"
        )
        self.assertNotEqual(
            response.data["actors"][0]["full_name"], "Name3 Sur2"
        )

        serializer = MovieDetailSerializer(self.movie_2)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_by_user_forbidden(self):
        payload = {
            "title": "New Movie",
            "description": "new test description",
            "duration": 100,
            "genres": [self.genre_2.id, self.genre_3.id],
            "actors": [self.actor_1.id, self.actor_3.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminBusTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_user(
            email="admin@test.com",
            password="admin_password",
            is_staff=True
        )
        self.client.force_authenticate(user=self.admin)

        self.genre_1 = Genre.objects.create(name="Test_genre1")
        self.genre_2 = Genre.objects.create(name="Test_genre2")
        self.genre_3 = Genre.objects.create(name="Test_genre3")

        self.actor_1 = Actor.objects.create(
            first_name="Name1", last_name="Sur1"
        )
        self.actor_2 = Actor.objects.create(
            first_name="Name2", last_name="Sur2"
        )
        self.actor_3 = Actor.objects.create(
            first_name="Name3", last_name="Sur3"
        )

        self.data_set_movie_1 = {
            "title": "Test1",
            "description": "test description 1",
            "duration": 148,
        }

        self.data_set_movie_2 = {
            "title": "Test2",
            "description": "test description 2",
            "duration": 120,
        }
        self.data_set_movie_3 = {
            "title": "Test3",
            "description": "test description 3",
            "duration": 110,
        }

        self.movie_1 = Movie.objects.create(**self.data_set_movie_1)
        self.movie_1.genres.set([self.genre_1, self.genre_2])
        self.movie_1.actors.set([self.actor_1, self.actor_2])

        self.movie_2 = Movie.objects.create(**self.data_set_movie_2)
        self.movie_2.genres.set([self.genre_1])
        self.movie_2.actors.set([self.actor_2])

        self.movie_3 = Movie.objects.create(**self.data_set_movie_3)
        self.movie_3.genres.set([self.genre_2])
        self.movie_3.actors.set([self.actor_1])

    def test_create_movie_by_admin_allowed(self):
        payload = {
            "title": "New Movie",
            "description": "new test description",
            "duration": 100,
            "genres": [self.genre_2.id, self.genre_3.id],
            "actors": [self.actor_1.id, self.actor_3.id]
        }
        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["id"], movie.id)
        self.assertEqual(sorted(payload["actors"]),
                         sorted(movie.actors.values_list("id", flat=True)))
