from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

from django.contrib.auth import get_user_model
from cinema.models import Genre, Actor, Movie, CinemaHall
from cinema.serializers import MovieListSerializer, MovieSerializer

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


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def sample_cinema_hall(**params):
    defaults = {
        "name": "Blue",
        "rows": 20,
        "seats_in_row": 20,
    }
    defaults.update(params)

    return CinemaHall.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, 401)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)


    def test_movies_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, 200)


    def test_filter_movies_by_genres(self):
        movie_without_genre = sample_movie()
        movie_with_genre_1 = sample_movie(title="TEEEEST1")
        movie_with_genre_2 = sample_movie(title="TEEEEST2")

        genre_1 = Genre.objects.create(name="sci-fi")
        genre_2 = Genre.objects.create(name="action")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(
            '/api/cinema/movies/',
            data={'genres': '1,2'}
        )
        self.assertEqual(res.status_code, 200)

        serializer_without_genres = MovieListSerializer(movie_without_genre)
        serializer_movie_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_movie_genre_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_movie_genre_1.data, res.data)
        self.assertIn(serializer_movie_genre_2.data, res.data)
        self.assertNotIn(serializer_without_genres.data, res.data)





    def tets_retrieve_movie_details(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="sci-fi"))

        url = detail_url(bus.id)

        res = self.client.get(url)

        serializer = MovieRetriveSerializer(movie)
        self.assertEqual(res.data, serializer.data)

    from rest_framework.test import APIClient
    from django.contrib.auth.models import User
    from rest_framework.authtoken.models import Token

    def test_create_movie_forbidden(self):
        actor_1 = sample_actor()
        actor_2 = sample_actor()
        genre = Genre.objects.create(name="Action")

        payload = {
            "title": "New Movie",
            "description": "This is a new movie.",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor_1.id, actor_2.id],
        }

        res = self.client.post(MOVIE_URL, payload)


        self.assertEqual(res.status_code, 201)


class AdminMovieTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "New Movie",
            "description": "This is a new movie.",
            "release_date": "2022-01-01",
            "duration": 120,
            "rating": 8.5,
            "genres": [sample_genre().id],
            "actors": [sample_actor().id, sample_actor().id],
            "cinema_halls": [sample_cinema_hall().id, sample_cinema_hall().id],
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, 201, res.data)

    def test_create_movie_with_genres(self):
        genre_1 = Genre.objects.create(name="sci-fi")
        actor_1 = Actor.objects.create(first_name="Actor", last_name="1")

        movie = sample_movie()
        movie.genres.add(genre_1)
        movie.actors.add(actor_1)

        serializer = MovieSerializer(movie)


        res = self.client.post(MOVIE_URL, serializer.data)

        genres = Genre.objects.all()
        self.assertEqual(res.status_code, 201)
        self.assertIn(genre_1, genres)

