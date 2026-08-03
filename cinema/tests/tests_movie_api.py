from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

def sample_movie(**params) -> Movie:
     defaults = {
         "title": "Avatar",
         "description": "Fantastic world with super power",
         "duration": 120,
     }
     defaults.update(params)
     return Movie.objects.create(**defaults)

def detail_movie(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testuser@user.test",
            password="movieTest",
        )
        self.client.force_authenticate(self.user)

    def test_movies_list_authenticated(self):
        sample_movie()
        movie_with_genres = sample_movie()

        genre_1 = Genre.objects.create(name="Fantasy")
        genre_2 = Genre.objects.create(name="Science")

        movie_with_genres.genres.add(genre_1, genre_2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.prefetch_related("genres")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies(self):
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(first_name="Keanu", last_name="Reeves")

        movie_target = sample_movie(title="Matrix", duration=120)
        movie_target.genres.add(genre)
        movie_target.actors.add(actor)

        movie_other = sample_movie(title="Avatar", duration=180)

        serializer_target = MovieListSerializer(movie_target)
        serializer_other = MovieListSerializer(movie_other)

        test_cases = [
            ({"title": "mat"}, "filter_by_title"),
            ({"duration": 120}, "filter_by_duration"),
            ({"genres": f"{genre.id}"}, "filter_by_genres"),
            ({"actors": f"{actor.id}"}, "filter_by_actors"),
        ]

        for params, subtest_name in test_cases:
            with self.subTest(msg=subtest_name):
                res = self.client.get(MOVIE_URL, params)
                self.assertEqual(res.status_code, status.HTTP_200_OK)
                self.assertIn(serializer_target.data, res.data)
                self.assertNotIn(serializer_other.data, res.data)

    def test_retrieve_movie_by_id(self):
        movie = sample_movie()
        genre = Genre.objects.create(name="Fantasy")
        movie.genres.add(genre)

        url = detail_movie(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {"title": "Dexter", "duration": 25}

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)



class AdminAuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@super.test",
            password="adminSuper",
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_success(self):
        genre = Genre.objects.create(name="Sci-Fi")
        actor = Actor.objects.create(first_name="Leonardo", last_name="DiCaprio")

        payload = {
            "title": "Inception",
            "description": "Mind-bending thriller",
            "duration": 148,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])

        genres = movie.genres.all()
        actors = movie.actors.all()
        self.assertEqual(genres.count(), 1)
        self.assertIn(genre, genres)
        self.assertEqual(actors.count(), 1)
        self.assertIn(actor, actors)
