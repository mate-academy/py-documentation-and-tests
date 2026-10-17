from django.contrib.auth import get_user_model
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

    def test_filter_movies_by_genre(self):
        movie_without_genre = sample_movie()
        movie_with_genre_1 = sample_movie()
        movie_with_genre_2 = sample_movie()
        movie_with_genre_3 = sample_movie()

        genre_1 = Genre.objects.create(name="Sci-fi")
        genre_2 = Genre.objects.create(name="Detective")
        genre_3 = Genre.objects.create(name="Comedy")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)
        movie_with_genre_3.genres.add(genre_3)

        res = self.client.get(MOVIE_URL_LIST, {"genres": f"{genre_1.id},{genre_2.id}"})

        serializer_without_genre = MovieListSerializer(movie_without_genre)
        serializer_with_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_with_genre_2 = MovieListSerializer(movie_with_genre_2)
        serializer_with_genre_3 = MovieListSerializer(movie_with_genre_3)

        self.assertIn(serializer_with_genre_1.data, res.data)
        self.assertNotIn(serializer_with_genre_3.data, res.data)
        self.assertNotIn(serializer_without_genre.data, res.data)
        self.assertIn(serializer_with_genre_2.data, res.data)

    def test_filter_movies_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actor_1 = sample_movie()
        movie_with_actor_2 = sample_movie()
        movie_with_actor_3 = sample_movie()

        actor_1 = Actor.objects.create(
            first_name="Kendric",
            last_name="Lamar"
        )
        actor_2 = Actor.objects.create(
            first_name="William",
            last_name="Delupac"
        )
        actor_3 = Actor.objects.create(
            first_name="Lil",
            last_name="Uzi"
        )

        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)
        movie_with_actor_3.actors.add(actor_3)

        res = self.client.get(MOVIE_URL_LIST, {"actors": f"{actor_1.id},{actor_3.id}"})

        serializer_without_genre = MovieListSerializer(movie_without_actors)
        serializer_with_genre_1 = MovieListSerializer(movie_with_actor_1)
        serializer_with_genre_2 = MovieListSerializer(movie_with_actor_2)
        serializer_with_genre_3 = MovieListSerializer(movie_with_actor_3)

        self.assertIn(serializer_with_genre_1.data, res.data)
        self.assertIn(serializer_with_genre_3.data, res.data)
        self.assertNotIn(serializer_without_genre.data, res.data)
        self.assertNotIn(serializer_with_genre_2.data, res.data)

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

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

