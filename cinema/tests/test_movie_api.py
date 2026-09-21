import tempfile
import os
from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieSerializer,
    MovieListSerializer,
    MovieDetailSerializer,
    MovieImageSerializer,
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
    """Return URL for movie image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_image():
    image = BytesIO()
    Image.new("RGB", (10, 10)).save(image, format="JPEG")
    return SimpleUploadedFile(
        "movie.jpg", image.getvalue(), content_type="image/jpeg"
    )


def movie_results(response):
    if isinstance(response.data, dict):
        return response.data["results"]
    return response.data


class MovieAPITestCase(TestCase):
    def setUp(self):
        super().setUp()
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(
            MEDIA_ROOT=media.name,
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": "movie-api-tests",
                }
            },
        )
        settings.enable()
        self.addCleanup(settings.disable)
        cache.clear()
        self.addCleanup(cache.clear)


class MovieImageUploadTests(MovieAPITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def test_upload_image_to_movie(self):
        """Test uploading an image to movie"""
        url = image_upload_url(self.movie.id)
        with sample_image() as ntf:
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))
        serializer = MovieImageSerializer(
            self.movie, context={"request": res.wsgi_request}
        )
        self.assertEqual(res.data, serializer.data)

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", res.data)
        self.movie.refresh_from_db()
        self.assertFalse(self.movie.image)

    def test_post_image_to_movie_list(self):
        url = MOVIE_URL
        with sample_image() as ntf:
            res = self.client.post(
                url,
                {
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [self.genre.id],
                    "actors": [self.actor.id],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)
        with sample_image() as ntf:
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)
        with sample_image() as ntf:
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", movie_results(res)[0])

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with sample_image() as ntf:
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())

    def test_regular_user_cannot_upload_image(self):
        user = get_user_model().objects.create_user(
            "regular@myproject.com", "password"
        )
        self.client.force_authenticate(user)
        with sample_image() as image:
            res = self.client.post(
                image_upload_url(self.movie.id),
                {"image": image},
                format="multipart",
            )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.movie.refresh_from_db()
        self.assertFalse(self.movie.image)

    def test_upload_image_to_missing_movie(self):
        with sample_image() as image:
            res = self.client.post(
                image_upload_url(self.movie.id + 1),
                {"image": image},
                format="multipart",
            )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class MovieApiTests(MovieAPITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.genre = sample_genre()
        self.other_genre = sample_genre(name="Comedy")
        self.actor = sample_actor()
        self.other_actor = sample_actor(first_name="Emma", last_name="Stone")
        self.movie = sample_movie(title="The Night Train")
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)
        self.other_movie = sample_movie(title="Daylight")
        self.other_movie.genres.add(self.other_genre)
        self.other_movie.actors.add(self.other_actor)
        self.payload = {
            "title": "A New Movie",
            "description": "A new description",
            "duration": 120,
            "genres": [self.genre.id, self.other_genre.id],
            "actors": [self.actor.id, self.other_actor.id],
        }

    def authenticate_admin(self):
        admin = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(admin)

    def assert_movies(self, response, movies):
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        serializer = MovieListSerializer(
            sorted(movies, key=lambda movie: movie.title),
            many=True,
            context={"request": response.wsgi_request},
        )
        self.assertEqual(movie_results(response), serializer.data)

    def test_list_movies(self):
        res = self.client.get(MOVIE_URL)
        self.assert_movies(res, [self.movie, self.other_movie])

    def test_retrieve_movie(self):
        res = self.client.get(detail_url(self.movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        serializer = MovieDetailSerializer(
            self.movie, context={"request": res.wsgi_request}
        )
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.data["genres"][0]["name"], self.genre.name)
        self.assertEqual(res.data["actors"][0]["full_name"], self.actor.full_name)

    def test_retrieve_missing_movie(self):
        res = self.client.get(detail_url(self.other_movie.id + 1))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_title_case_insensitive_substring(self):
        another_match = sample_movie(title="Midnight Express")
        res = self.client.get(MOVIE_URL, {"title": "nIgHt"})
        self.assert_movies(res, [self.movie, another_match])

    def test_filter_title_no_matches(self):
        res = self.client.get(MOVIE_URL, {"title": "unmatched"})
        self.assert_movies(res, [])

    def test_filter_single_genre(self):
        res = self.client.get(MOVIE_URL, {"genres": self.genre.id})
        self.assert_movies(res, [self.movie])

    def test_filter_multiple_genres_without_duplicates(self):
        self.movie.genres.add(self.other_genre)
        unrelated = sample_movie(title="Unrelated")
        unrelated.genres.add(sample_genre(name="Horror"))
        res = self.client.get(
            MOVIE_URL, {"genres": f"{self.genre.id},{self.other_genre.id}"}
        )
        self.assert_movies(res, [self.movie, self.other_movie])

    def test_filter_single_actor(self):
        res = self.client.get(MOVIE_URL, {"actors": self.actor.id})
        self.assert_movies(res, [self.movie])

    def test_filter_multiple_actors_without_duplicates(self):
        self.movie.actors.add(self.other_actor)
        unrelated = sample_movie(title="Unrelated")
        unrelated.actors.add(sample_actor(first_name="Other"))
        res = self.client.get(
            MOVIE_URL, {"actors": f"{self.actor.id},{self.other_actor.id}"}
        )
        self.assert_movies(res, [self.movie, self.other_movie])

    def test_combined_filters(self):
        wrong_title = sample_movie(title="Day Train")
        wrong_title.genres.add(self.genre)
        wrong_title.actors.add(self.actor)
        wrong_genre = sample_movie(title="Night Sky")
        wrong_genre.genres.add(self.other_genre)
        wrong_genre.actors.add(self.actor)
        wrong_actor = sample_movie(title="Night Road")
        wrong_actor.genres.add(self.genre)
        wrong_actor.actors.add(self.other_actor)
        res = self.client.get(
            MOVIE_URL,
            {
                "title": "night",
                "genres": self.genre.id,
                "actors": self.actor.id,
            },
        )
        self.assert_movies(res, [self.movie])

    def test_admin_can_create_movie_with_relationships(self):
        self.authenticate_admin()
        count = Movie.objects.count()
        res = self.client.post(MOVIE_URL, self.payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), count + 1)
        movie = Movie.objects.get(id=res.data["id"])
        for field in ["title", "description", "duration"]:
            self.assertEqual(getattr(movie, field), self.payload[field])
        self.assertCountEqual(
            movie.genres.values_list("id", flat=True), self.payload["genres"]
        )
        self.assertCountEqual(
            movie.actors.values_list("id", flat=True), self.payload["actors"]
        )
        self.assertEqual(res.data, MovieSerializer(movie).data)

    def test_admin_create_invalid_movie(self):
        self.authenticate_admin()
        count = Movie.objects.count()
        payload = dict(self.payload, title="")
        res = self.client.post(MOVIE_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", res.data)
        self.assertEqual(Movie.objects.count(), count)

    def test_regular_user_cannot_create_movie(self):
        count = Movie.objects.count()
        res = self.client.post(MOVIE_URL, self.payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Movie.objects.count(), count)

    def test_anonymous_access_denied(self):
        self.client.force_authenticate(user=None)
        count = Movie.objects.count()
        requests = [
            ("get", MOVIE_URL, {}),
            ("get", detail_url(self.movie.id), {}),
            ("post", MOVIE_URL, self.payload),
            ("post", image_upload_url(self.movie.id), {}),
        ]
        for method, url, data in requests:
            with self.subTest(method=method, url=url):
                res = getattr(self.client, method)(url, data, format="json")
                self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Movie.objects.count(), count)
        self.movie.refresh_from_db()
        self.assertFalse(self.movie.image)

    def test_update_and_delete_are_not_supported(self):
        self.authenticate_admin()
        for method in ["put", "patch", "delete"]:
            with self.subTest(method=method):
                res = getattr(self.client, method)(
                    detail_url(self.movie.id), self.payload, format="json"
                )
                self.assertEqual(
                    res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
                )
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.title, "The Night Train")
