from django.contrib.auth import get_user_model
from rest_framework.status import HTTP_403_FORBIDDEN
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.reverse import reverse

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL_LIST = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Inception",
        "description": "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
        "duration": 148,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieViewSetTests(APITestCase):
    def test_auth_required(self):
        res = self.client.get(MOVIE_URL_LIST)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewSetTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="passwordtest"
        )
        self.client.force_authenticate(user=self.user)

    def test_movie_list(self):
        sample_movie()
        movie = sample_movie()

        genre_1 = Genre.objects.create(name="Drama")
        genre_2 = Genre.objects.create(name="Crime")

        actor_1 = Actor.objects.create(first_name="Max", last_name="Kaspersky")
        actor_2 = Actor.objects.create(first_name="Oleksii", last_name="Flud")

        movie.genres.add(genre_1, genre_2)
        movie.actors.add(actor_1, actor_2)

        res = self.client.get(MOVIE_URL_LIST)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie_without_title = sample_movie()
        movie_with_title_1 = sample_movie(title="Interstellar")
        movie_with_title_2 = sample_movie(title="Mentalist")

        res = self.client.get(MOVIE_URL_LIST, {"title": "Interstellar"})

        serializer_without_title = MovieListSerializer(movie_without_title)
        serializer_with_title_1 = MovieListSerializer(movie_with_title_1)
        serializer_with_title_2 = MovieListSerializer(movie_with_title_2)

        self.assertIn(serializer_with_title_1.data, res.data)
        self.assertNotIn(serializer_without_title.data, res.data)
        self.assertNotIn(serializer_with_title_2.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()

        actor = Actor.objects.create(first_name="Roman", last_name="Melnyk")

        movie.genres.add(Genre.objects.create(name="Sci-fi"))
        movie.actors.add(actor)

        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Interstellar",
            "description": "test description",
            "duration": 132,
        }

        res = self.client.post(MOVIE_URL_LIST, payload)

        self.assertEqual(res.status_code, HTTP_403_FORBIDDEN)
