from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from django.urls import reverse, get_resolver
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import (
    MovieSerializer,
    MovieListSerializer,
    MovieDetailSerializer,
)
from user.models import User

BASE_URL = reverse("cinema:movies-list")


def detail_url(movies_id):
    return reverse("cinema:movies-detail", args=[movies_id])


def movie_example(**params):
    defaults = {
        "title": "test_title",
        "description": "test_description",
        "duration": 140,
    }
    defaults.update(params)
    movie = Movie.objects.create(**defaults)
    return movie


class TestUnauthenticatedMovieAPI(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        get_resolver()._populate()
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestAuthenticatedMovieAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@user.com",
            password="test_password",
        )
        self.client.force_authenticate(user=self.user)

    def test_movies_list_response(self):
        movie = movie_example()
        actors = Actor.objects.create(first_name="Angelina", last_name="Smith")
        genres = Genre.objects.create(name="Science")
        movie.actors.add(actors)
        movie.genres.add(genres)
        response = self.client.get(BASE_URL)
        serializer = MovieListSerializer([movie], many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filtered_movies_list_by_actors(self):
        movie_with_first_actor = movie_example(title="Film")
        movie_with_second_actor = movie_example(title="Another one Film")
        actor_1 = Actor.objects.create(first_name="Angelina", last_name="Smith")
        actor_2 = Actor.objects.create(first_name="John", last_name="Dilan")
        movie_with_first_actor.actors.add(actor_1)
        movie_with_second_actor.actors.add(actor_2)
        res = self.client.get(BASE_URL, {"actors": actor_1.id})
        serializer_first = MovieListSerializer([movie_with_first_actor], many=True)
        serializer_second = MovieListSerializer([movie_with_second_actor], many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer_first.data)
        self.assertNotEqual(res.data, serializer_second.data)

    def test_filtered_movies_list_by_genres(self):
        movie_with_first_genre = movie_example(title="Science Film")
        movie_with_second_genre = movie_example(title="Comedy Film")
        genre_1 = Genre.objects.create(name="Science")
        genre_2 = Genre.objects.create(name="Comedy")
        movie_with_first_genre.genres.add(genre_1)
        movie_with_second_genre.genres.add(genre_2)
        res = self.client.get(BASE_URL, {"genres": genre_1.id})
        serializer_first = MovieListSerializer([movie_with_first_genre], many=True)
        serializer_second = MovieListSerializer([movie_with_second_genre], many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer_first.data)
        self.assertNotEqual(res.data, serializer_second.data)

    def test_retrieve_movie_detail(self):
        movie = movie_example()
        movie.actors.add(Actor.objects.create(first_name="Angelina", last_name="Smith"))
        movie.genres.add(Genre.objects.create(name="Science"))
        movie_url = detail_url(movie.id)
        res = self.client.get(movie_url)
        serializer_details = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer_details.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "test_title",
            "description": "test_description",
            "duration": 140,
        }
        res = self.client.post(BASE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_throttling(self):
        for k in range(30):
            res = self.client.get(BASE_URL)
            self.assertNotEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        res = self.client.get(BASE_URL)
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)



class TestAdminMovieAPI(TestCase):
    def setUp(self):
        admin_user = User.objects.create_superuser(
            email="admin@email.com", password="admin_password", is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(user=admin_user)

    def test_create_movie_by_admin(self):
        actor = Actor.objects.create(first_name="Angelina", last_name="Smith")
        genre = Genre.objects.create(name="Science")
        payload = {
            "title": "test_title",
            "description": "test_description",
            "duration": 140,
            "actors": [actor.id],
            "genres": [genre.id],
        }

        res = self.client.post(BASE_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], "test_title")

    def test_delete_movie_not_allowed(self):
        movie = movie_example()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
