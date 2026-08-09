from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.reverse import reverse
from rest_framework import status

from cinema.models import Actor, Genre, Movie
from cinema.serializers import MovieDetailSerializer, MovieListSerializer


MOVIE_URL = reverse("cinema:movie-list")

def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Movie Title",
        "description": "Movie description",
        "duration": 120,
        "image": None
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


class UnauthentikatedMovieApi(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthentikatedMovieApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="TestUserPass"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        movie_with_actors_genres = sample_movie()

        actors = Actor.objects.create(
            first_name="Jackie",
            last_name="Chan"
        )
        genres = Genre.objects.create(name="Action")

        movie_with_actors_genres.actors.add(actors)
        movie_with_actors_genres.genres.add(genres)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_filter_with_actors(self):
        title = "Movie Title Search"
        search_title = "Movie Title"
        movie_without_actors_and_cenres = sample_movie()
        movie_with_actors_genres = sample_movie(title=title)
        
        actors = Actor.objects.create(
            first_name="Jackie",
            last_name="Chan"
        )
        genres = Genre.objects.create(name="Action")

        movie_with_actors_genres.actors.add(actors)
        movie_with_actors_genres.genres.add(genres)

        res = self.client.get(
            MOVIE_URL,
            {
                "actors": f"{actors.id}",
                "genres": f"{genres.id}",
                "title": f"{search_title}"
            }
        )

        serializer_movie_without_actors_genres = MovieListSerializer(
            movie_without_actors_and_cenres
        )
        serializer_movie_with_actors_genres = MovieListSerializer(
            movie_with_actors_genres
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer_movie_without_actors_genres.data, res.data)
        self.assertIn(serializer_movie_with_actors_genres.data, res.data)

    def test_retrieve_movie(self):
        movie = sample_movie()
        movie.actors.add(
            Actor.objects.create(
                first_name="Jackie",
                last_name="Chan"
            )
        )
        movie.genres.add(
            Genre.objects.create(name="Action")
        )

        url = detail_url(movie.id)

        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbiden(self):
            payload = {
                "title": "Test Title",
                "description": "Test description",
                "duration": 110,
                "image": ""
            }
    
            res = self.client.post(MOVIE_URL, payload)
    
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
            self.client = APIClient()
            self.user = get_user_model().objects.create_user(
                email="admin@admin.test",
                password="TestAdminPass",
                is_staff=True
            )
            self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Test Title",
            "description": "Test description",
            "duration": 110,
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors_genres(self):
        actors = Actor.objects.create(
            first_name="Jackie",
            last_name="Chan"
        )
        genres = Genre.objects.create(name="Action")
        payload = {
            "title": "Test Title",
            "description": "Test description",
            "duration": 110,
            "actors": actors.id,
            "genres": genres.id
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        monie_actors = movie.actors.all()
        movie_genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actors, monie_actors)
        self.assertIn(genres, movie_genres)
        self.assertEqual(monie_actors.count(), 1)
        self.assertEqual(movie_genres.count(), 1)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)



