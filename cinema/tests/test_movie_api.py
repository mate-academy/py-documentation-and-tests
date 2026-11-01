import tempfile

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Actor, Genre, Movie
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {"name": "Drama"}
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


class BaseMovieApiTest(TestCase):
    def setUp(self):
        # throttling counters live in cache, so reset them for each test
        cache.clear()
        self.client = APIClient()


class UnauthenticatedMovieApiTest(BaseMovieApiTest):
    def test_list_requires_auth(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_requires_auth(self):
        movie = sample_movie()

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_auth(self):
        payload = {"title": "New", "description": "Desc", "duration": 100}

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(BaseMovieApiTest):
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie(title="Movie 1")
        sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Matrix")
        movie2 = sample_movie(title="Inception")

        res = self.client.get(MOVIE_URL, {"title": "matr"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_genres(self):
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Comedy")
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie3 = sample_movie(title="Movie 3")
        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"}
        )

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertIn(MovieListSerializer(movie2).data, res.data)
        self.assertNotIn(MovieListSerializer(movie3).data, res.data)

    def test_filter_movies_by_actors(self):
        actor1 = sample_actor(first_name="Keanu", last_name="Reeves")
        actor2 = sample_actor(first_name="Brad", last_name="Pitt")
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie3 = sample_movie(title="Movie 3")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(
            MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"}
        )

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertIn(MovieListSerializer(movie2).data, res.data)
        self.assertNotIn(MovieListSerializer(movie3).data, res.data)

    def test_filter_movies_by_all_params(self):
        genre = sample_genre()
        actor = sample_actor()
        movie1 = sample_movie(title="Matrix")
        movie2 = sample_movie(title="Matrix 2")
        movie1.genres.add(genre)
        movie1.actors.add(actor)

        res = self.client.get(
            MOVIE_URL,
            {
                "title": "matrix",
                "genres": str(genre.id),
                "actors": str(actor.id),
            },
        )

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)

    def test_filter_does_not_return_duplicates(self):
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Comedy")
        movie = sample_movie()
        movie.genres.add(genre1, genre2)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"}
        )

        self.assertEqual(len(res.data), 1)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        res = self.client.get(detail_url(movie.id))

        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_nonexistent_movie(self):
        res = self.client.get(detail_url(999999))

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_movie_forbidden(self):
        payload = {"title": "New", "description": "Desc", "duration": 100}

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title="New").exists())

    def test_upload_image_forbidden(self):
        movie = sample_movie()

        res = self.client.post(image_upload_url(movie.id), {})

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(BaseMovieApiTest):
    def setUp(self):
        super().setUp()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.admin)
        self.movie = sample_movie()

    def tearDown(self):
        self.movie.refresh_from_db()
        self.movie.image.delete()

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "New movie",
            "description": "New description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_create_movie_invalid_payload(self):
        res = self.client.post(MOVIE_URL, {"title": ""}, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_movie_not_allowed(self):
        res = self.client.put(
            detail_url(self.movie.id),
            {"title": "Changed", "description": "d", "duration": 1},
            format="json",
        )

        self.assertEqual(
            res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_delete_movie_not_allowed(self):
        res = self.client.delete(detail_url(self.movie.id))

        self.assertEqual(
            res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.assertTrue(Movie.objects.filter(id=self.movie.id).exists())

    def test_upload_image_to_movie(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(self.movie.image.name)

    def test_upload_invalid_image(self):
        url = image_upload_url(self.movie.id)

        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        