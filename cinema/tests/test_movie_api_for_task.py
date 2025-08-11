from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


def sample_movie(**kwargs) -> Movie:
    movie_data = {
        "title": "Sample Movie",
        "description": "Sample description",
        "duration": 10,
    }
    movie_data.update(kwargs)
    return Movie.objects.create(**movie_data)


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_anon_client(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test_password"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movie_by_title(self):
        test_movie = sample_movie()
        terminator = sample_movie(title="Terminator")

        res = self.client.get(
            MOVIE_URL,
            {"title": "Terminator"}
        )

        test_serializer = MovieListSerializer(test_movie)
        serializer_terminator = MovieListSerializer(terminator)

        self.assertIn(serializer_terminator.data, res.data)
        self.assertNotIn(test_serializer.data, res.data)

    def test_filter_movie_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actor1 = sample_movie(title="Terminator")
        movie_with_actor2 = sample_movie(title="Troy")
        movie_with_actors_1_2 = sample_movie(title="Transporter")

        actor_1 = Actor.objects.create(first_name="Arnold",
                                       last_name="Schwarzenegger")
        actor_2 = Actor.objects.create(first_name="Brad",
                                       last_name="Pitt")

        movie_with_actor1.actors.add(actor_1)
        movie_with_actor2.actors.add(actor_2)
        movie_with_actors_1_2.actors.add(actor_1, actor_2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer_movie_without_actors = MovieSerializer(movie_without_actors)
        serializer_movie_with_actor1 = MovieListSerializer(movie_with_actor1)
        serializer_movie_with_actor2 = MovieListSerializer(movie_with_actor2)
        serializer_movie_with_actors_1_2 = MovieListSerializer(movie_with_actors_1_2)

        self.assertIn(serializer_movie_with_actor1.data, res.data)
        self.assertIn(serializer_movie_with_actor2.data, res.data)
        self.assertIn(serializer_movie_with_actors_1_2.data, res.data)
        self.assertNotIn(serializer_movie_without_actors.data, res.data)

    def test_filter_movie_by_genres(self):
        movie_without_genres = sample_movie()
        movie_with_genre1 = sample_movie(title="Terminator")
        movie_with_genre2 = sample_movie(title="Troy")
        movie_with_genres_1_2 = sample_movie(title="Transporter")

        genre_1 = Genre.objects.create(name="action")
        genre_2 = Genre.objects.create(name="adventure")

        movie_with_genre1.genres.add(genre_1)
        movie_with_genre2.genres.add(genre_2)
        movie_with_genres_1_2.genres.add(genre_1, genre_2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        serializer_movie_without_genres = MovieSerializer(movie_without_genres)
        serializer_movie_with_genre1 = MovieListSerializer(movie_with_genre1)
        serializer_movie_with_genre2 = MovieListSerializer(movie_with_genre2)
        serializer_movie_with_genres_1_2 = MovieListSerializer(movie_with_genres_1_2)

        self.assertIn(serializer_movie_with_genre1.data, res.data)
        self.assertIn(serializer_movie_with_genre2.data, res.data)
        self.assertIn(serializer_movie_with_genres_1_2.data, res.data)
        self.assertNotIn(serializer_movie_without_genres.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.actors.add(Actor.objects.create(
            first_name="Arnold",
            last_name="Schwarzenegger"
        ))
        movie.genres.add(Genre.objects.create(name="action"))

        res = self.client.get(detail_url(movie.id))

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "User Movie",
            "description": "User description",
            "duration": 66,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="test_password",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Admin Movie",
            "description": "Admin description",
            "duration": 76,
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres(self):
        genre_1 = Genre.objects.create(name="action")
        genre_2 = Genre.objects.create(name="adventure")

        payload = {
            "title": "Admin Movie",
            "description": "Admin description",
            "duration": 76,
            "genres": [genre_1.id, genre_2.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)

    def test_create_movie_with_actors(self):
        actor_1 = Actor.objects.create(first_name="Arnold",
                                       last_name="Schwarzenegger")
        actor_2 = Actor.objects.create(first_name="Brad",
                                       last_name="Pitt")

        payload = {
            "title": "Admin Movie",
            "description": "Admin description",
            "duration": 76,
            "actors": [actor_1.id, actor_2.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(actors.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        res = self.client.delete(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_movie_not_allowed(self):
        movie = sample_movie()

        res = self.client.post(detail_url(movie.id), {"title": "New"})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
