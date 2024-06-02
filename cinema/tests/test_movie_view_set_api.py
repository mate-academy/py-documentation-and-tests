from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


class UnauthenticatedApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="test12345"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, serializer.data)

    def test_movies_list_with_actors_and_genres(self):
        sample_movie()

        movie_with_actor = sample_movie(title="Movie with actor")
        actor = Actor.objects.create(first_name="George", last_name="Clooney")
        movie_with_actor.actors.add(actor)

        movie_with_genre = sample_movie(title="Movie with genre")
        genre = Genre.objects.create(name="Drama")
        movie_with_genre.genres.add(genre)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_actors_and_genres_title(self):
        movie_with_actor = sample_movie(title="Criminal")
        movie_with_genre = sample_movie(title="Flash")
        another_movie = sample_movie(title="Another Movie")

        actor = Actor.objects.create(first_name="George", last_name="Clooney")
        genre = Genre.objects.create(name="Drama")

        movie_with_actor.actors.add(actor)
        movie_with_genre.genres.add(genre)

        res = self.client.get(MOVIE_URL, {'actors': actor.id})
        serializer = MovieListSerializer(Movie.objects.filter(actors__id=actor.id).distinct(), many=True)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, serializer.data)
        self.assertNotIn(another_movie.id, [movie['id'] for movie in res.data])

        res = self.client.get(MOVIE_URL, {'genres': genre.id})
        serializer = MovieListSerializer(Movie.objects.filter(genres__id=genre.id).distinct(), many=True)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, serializer.data)

        res = self.client.get(MOVIE_URL, {'title': 'Criminal'})
        serializer = MovieListSerializer(Movie.objects.filter(title__icontains='Criminal').distinct(), many=True)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, serializer.data)

        res = self.client.get(MOVIE_URL, {'actors': actor.id, 'genres': genre.id, 'title': 'Criminal'})
        serializer = MovieListSerializer(
            Movie.objects.filter(
                actors__id=actor.id,
                genres__id=genre.id,
                title__icontains='Criminal'
            ).distinct(), many=True
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_movie(self):
        movie = sample_movie()
        movie.actors.add(Actor.objects.create(first_name="George", last_name="Clooney"))
        movie.genres.add(Genre.objects.create(name="Drama"))

        url = detail_url(movie.id)

        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {"title": "Sample movie",
                   "description": "Sample description",
                   "duration": 90,
                   }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com", password="admin12345", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {"title": "Sample movie",
                   "description": "Sample description",
                   "duration": 90,
                   }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(
            title=payload["title"],
            description=payload["description"],
            duration=payload["duration"]
        )

        self.assertIsNotNone(movie)
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])

    def test_create_movie_with_genre(self):
        actor = Actor.objects.create(first_name="George", last_name="Clooney")
        genre = Genre.objects.create(name="Drama")
        payload = {"title": "Sample movie",
                   "description": "Sample description",
                   "duration": 90,
                   "actors": [actor.id],
                   "genres": [genre.id]
                   }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor.id, res.data["actors"])
        self.assertIn(genre.id, res.data["genres"])
