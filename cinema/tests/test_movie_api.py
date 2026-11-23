import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

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


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_auth_required(self):
        movie = sample_movie()

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password123"
        )
        self.client.force_authenticate(self.user)

        self.drama = sample_genre(name="Drama")
        self.comedy = sample_genre(name="Comedy")
        self.clooney = sample_actor(first_name="George", last_name="Clooney")
        self.pitt = sample_actor(first_name="Brad", last_name="Pitt")

        self.ocean = sample_movie(title="Ocean's Eleven")
        self.ocean.genres.add(self.comedy)
        self.ocean.actors.add(self.clooney, self.pitt)

        self.gravity = sample_movie(title="Gravity")
        self.gravity.genres.add(self.drama)
        self.gravity.actors.add(self.clooney)

        self.fight_club = sample_movie(title="Fight Club")
        self.fight_club.genres.add(self.drama, self.comedy)
        self.fight_club.actors.add(self.pitt)

    def test_list_movies(self):
        res = self.client.get(MOVIE_URL)

        serializer = MovieListSerializer(Movie.objects.all(), many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": "ocean"})

        serializer = MovieListSerializer(self.ocean)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [serializer.data])

    def test_filter_movies_by_genres(self):
        res = self.client.get(MOVIE_URL, {"genres": f"{self.drama.id}"})

        titles = [movie["title"] for movie in res.data]
        self.assertEqual(sorted(titles), ["Fight Club", "Gravity"])

    def test_filter_movies_by_actors(self):
        res = self.client.get(MOVIE_URL, {"actors": f"{self.pitt.id}"})

        titles = [movie["title"] for movie in res.data]
        self.assertEqual(sorted(titles), ["Fight Club", "Ocean's Eleven"])

    def test_filter_by_several_ids_returns_movie_once(self):
        res = self.client.get(
            MOVIE_URL, {"genres": f"{self.drama.id},{self.comedy.id}"}
        )

        titles = [movie["title"] for movie in res.data]
        self.assertEqual(titles.count("Fight Club"), 1)
        self.assertEqual(len(titles), 3)

    def test_filter_movies_by_title_genres_and_actors(self):
        res = self.client.get(
            MOVIE_URL,
            {
                "title": "club",
                "genres": f"{self.comedy.id}",
                "actors": f"{self.pitt.id}",
            },
        )

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Fight Club")

    def test_list_shows_genre_names_and_actor_full_names(self):
        res = self.client.get(MOVIE_URL, {"title": "gravity"})

        self.assertEqual(res.data[0]["genres"], ["Drama"])
        self.assertEqual(res.data[0]["actors"], ["George Clooney"])

    def test_retrieve_movie_detail(self):
        res = self.client.get(detail_url(self.ocean.id))

        serializer = MovieDetailSerializer(self.ocean)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_missing_movie_returns_404(self):
        res = self.client.get(detail_url(9999))

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "New movie",
            "description": "Description",
            "duration": 100,
            "genres": [self.drama.id],
            "actors": [self.pitt.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title="New movie").exists())

    def test_upload_image_forbidden(self):
        res = self.client.post(
            image_upload_url(self.ocean.id), {}, format="multipart"
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_requests_are_throttled(self):
        for _ in range(30):
            self.client.get(MOVIE_URL)

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password123"
        )
        self.client.force_authenticate(self.admin)
        self.genre = sample_genre()
        self.actor = sample_actor()

    def test_create_movie(self):
        payload = {
            "title": "New movie",
            "description": "Description",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.duration, payload["duration"])
        self.assertEqual(list(movie.genres.all()), [self.genre])
        self.assertEqual(list(movie.actors.all()), [self.actor])

    def test_create_movie_without_title_returns_400(self):
        payload = {"description": "Description", "duration": 100}

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_movie_not_allowed(self):
        movie = sample_movie()

        res_put = self.client.put(detail_url(movie.id), {"title": "New"})
        res_patch = self.client.patch(detail_url(movie.id), {"title": "New"})

        self.assertEqual(res_put.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(
            res_patch.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        res = self.client.delete(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Movie.objects.filter(id=movie.id).exists())
