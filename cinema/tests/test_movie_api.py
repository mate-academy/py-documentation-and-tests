import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
)

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


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


def image_upload_url(movie_id):
    """Return URL for recipe image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        self.movie.image.delete()

    def test_upload_image_to_movie(self):
        """Test uploading an image to movie"""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list(self):
        url = MOVIE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [1],
                    "actors": [1],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())


class EndpointTestTrickeryMixin(TestCase):
    def _subtest_endpoints(
        self, endpoints: list[dict], response_code: int
    ) -> None:
        # Using weird techniques to avoid duplicating code.
        for endpoint in endpoints:
            with self.subTest(
                f"{endpoint['method'].upper()} {endpoint['url']}"
            ):
                # Assign client's request method to a variable.
                method = getattr(self.client, endpoint["method"])

                # Call it as a function to access the endpoint.
                res = method(endpoint["url"])
                # Using "res" instead of "response" because it's the same
                # in the code above.

                self.assertEqual(res.status_code, response_code)


class TestMovieViewSetPublic(EndpointTestTrickeryMixin, TestCase):
    def setUp(self):
        self.client = APIClient()
        self.movie = sample_movie()

    def test_endpoints_require_authorization(self):
        """Test that anonymous users can't access API endpoints"""
        endpoints = [
            {"method": "get", "url": MOVIE_URL},
            {"method": "post", "url": MOVIE_URL},
            {"method": "get", "url": detail_url(self.movie.id)},
        ]

        self._subtest_endpoints(endpoints, status.HTTP_401_UNAUTHORIZED)


class TestMovieViewSetPrivate(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_get_list_of_movies(self):
        # I guess I can actually live with code duplication in tests
        # to make all the test data visible in the test itself.
        sample_movie()
        sample_movie(title="Movie 2")
        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movies_in = [
            sample_movie(title="Sample Movie"),
            sample_movie(title="sample movie 2"),
        ]
        sample_movie(title="Filtered out")

        res = self.client.get(f"{MOVIE_URL}?title=samPle")
        serializer_in = MovieListSerializer(movies_in, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer_in.data)

    def test_filter_movies_by_actors(self):
        movies_in = [
            sample_movie(title="Sample Movie"),
            sample_movie(title="sample movie 2"),
        ]
        movies_out = [
            sample_movie(title="Filtered out"),
            sample_movie(title="Filtered out 2"),
        ]

        actor1 = sample_actor()
        actor2 = sample_actor()
        actor_out = sample_actor()

        movies_in[0].actors.add(actor1)
        movies_in[1].actors.add(actor1, actor2, actor_out)

        movies_out[0].actors.add(actor_out)

        res = self.client.get(f"{MOVIE_URL}?actors=1,2")
        serializer_in = MovieListSerializer(movies_in, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer_in.data)

    def test_filter_movies_by_genres(self):
        movies_in = [
            sample_movie(title="Sample Movie"),
            sample_movie(title="sample movie 2"),
        ]
        movies_out = [
            sample_movie(title="Filtered out"),
            sample_movie(title="Filtered out 2"),
        ]

        genre1 = sample_genre(name="Genre 1")
        genre2 = sample_genre(name="Genre 2")
        genre_out = sample_genre(name="Genre out")

        movies_in[0].genres.add(genre1)
        movies_in[1].genres.add(genre1, genre2, genre_out)

        movies_out[0].genres.add(genre_out)

        res = self.client.get(f"{MOVIE_URL}?genres=1,2")
        serializer_in = MovieListSerializer(movies_in, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer_in.data)

    def test_filter_movies_by_title_actors_and_genres(self):
        """Test filtering behavior when multiple arguments are passed"""
        movies_in = [
            sample_movie(title="Sample Movie"),
        ]
        movies_out = [
            sample_movie(title="Sample Movie 2"),
        ]

        genre = sample_genre()
        actor = sample_actor()

        movies_in[0].genres.add(genre)
        movies_in[0].actors.add(actor)

        res = self.client.get(f"{MOVIE_URL}?title=sample&genres=1&actors=1")
        serializer_in = MovieListSerializer(movies_in, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer_in.data)

    def test_retrieve_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_user_cant_create_movie(self):
        actor = sample_actor()
        genre = sample_genre()
        payload = {
            "title": "Non-created movie",
            "description": "sample",
            "duration": 90,
            "actors": actor.id,
            "genres": genre.id,
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # On one hand, it seems right to test if the movie really wasn't
        # created. On the other hand, it feels like testing built-in
        # functionality, since built-in ViewSet is used.
        movies = Movie.objects.filter(title=payload["title"])
        self.assertEqual(len(movies), 0)


class TestMovieViewSetAdmin(EndpointTestTrickeryMixin, TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_admin_can_create_movie(self):
        actor = sample_actor()
        genre = sample_genre()
        payload = {
            "title": "Created movie",
            "description": "sample",
            "duration": 90,
            "actors": actor.id,
            "genres": genre.id,
        }

        res = self.client.post(MOVIE_URL, payload)
        movies = Movie.objects.filter(title=payload["title"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(movies), 1)

    def test_methods_not_allowed(self):
        # Same argumentation as above; I don't think that it's necessary to
        # test with any payload since it's ViewSet's built-in functionality.
        movie = sample_movie()
        url = detail_url(movie.id)

        endpoints = [
            {"method": "put", "url": url},
            {"method": "patch", "url": url},
        ]

        self._subtest_endpoints(endpoints, status.HTTP_405_METHOD_NOT_ALLOWED)
