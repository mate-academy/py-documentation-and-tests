import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

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


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def test_list_movies(self):
        movie_drama = sample_movie(title="Sample drama movie")
        movie_jc = sample_movie(title="Sample movie with JC")

        movie_drama.genres.set([self.genre.id])
        movie_jc.actors.set([self.actor.id])

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie_2 = sample_movie(title="Second sample movie")

        serializer = MovieListSerializer(self.movie)
        serializer_2 = MovieListSerializer(movie_2)

        res = self.client.get(MOVIE_URL, {"title": "second"})
        self.assertIn(serializer_2.data, res.data)
        self.assertNotIn(serializer.data, res.data)

    def test_filter_movies_by_genres(self):
        genre_r = sample_genre(name="Romance")

        movie_r = sample_movie(title="Romance sample movie")
        movie_rd = sample_movie(title="Romance and drama sample movie")

        movie_r.genres.set([genre_r.id])
        movie_rd.genres.set([self.genre.id, genre_r.id])

        serializer = MovieListSerializer(self.movie)
        serializer_r = MovieListSerializer(movie_r)
        serializer_rd = MovieListSerializer(movie_rd)

        res_r = self.client.get(MOVIE_URL, {"genres": f"{self.genre.id}"})
        self.assertIn(serializer_rd.data, res_r.data)
        self.assertNotIn(serializer_r.data, res_r.data)
        self.assertNotIn(serializer.data, res_r.data)

        res_rd = self.client.get(MOVIE_URL, {"genres": f"{genre_r.id},{self.genre.id}"})
        self.assertIn(serializer_rd.data, res_rd.data)
        self.assertIn(serializer_r.data, res_rd.data)
        self.assertNotIn(serializer.data, res_rd.data)

    def test_filter_movies_by_actors(self):
        actor_jd = sample_actor(first_name="Johnny", last_name="Depp")

        movie_jd = sample_movie(title="Sample movie with JD")
        movie_jd_gc = sample_movie(title="Sample movie with JD and GC")

        movie_jd.actors.set([actor_jd.id])
        movie_jd_gc.actors.set([self.actor.id, movie_jd.id])

        serializer = MovieListSerializer(self.movie)
        serializer_jd = MovieListSerializer(movie_jd)
        serializer_jd_gc = MovieListSerializer(movie_jd_gc)

        res_jd = self.client.get(MOVIE_URL, {"actors": f"{self.actor.id}"})
        self.assertIn(serializer_jd_gc.data, res_jd.data)
        self.assertNotIn(serializer_jd.data, res_jd.data)
        self.assertNotIn(serializer.data, res_jd.data)

        res_rd = self.client.get(MOVIE_URL, {"actors": f"{actor_jd.id},{self.actor.id}"})
        self.assertIn(serializer_jd_gc.data, res_rd.data)
        self.assertIn(serializer_jd.data, res_rd.data)
        self.assertNotIn(serializer.data, res_rd.data)

    def test_retrieve_movie(self):
        self.movie.genres.set([self.genre.id])
        self.movie.actors.set([self.actor.id])

        url = detail_url(self.movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(self.movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample movie description",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
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


class MovieImageUploadTests(AdminMovieApiTests):
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


class MovieApiTests(AdminMovieApiTests):
    def test_create_movie(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample movie description",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self):
        genre_r = sample_genre(name="Romance")
        actor_jd = sample_actor(first_name="Johnny", last_name="Depp")

        payload = {
            "title": "Sample movie",
            "description": "Sample movie description",
            "duration": 120,
            "genres": [self.genre.id, genre_r.id],
            "actors": [self.actor.id, actor_jd.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(movie.genres.count(), 2)
        self.assertEqual(movie.actors.count(), 2)

    def test_delete_movie_not_allowed(self):
        url = detail_url(self.movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_movie_not_allowed(self):
        payload_put = {
            "title": "Updated sample movie",
            "description": "Sample description",
            "duration": 90,
        }
        payload_patch = {
            "title": "Updated sample movie",
        }
        url = detail_url(self.movie.id)

        res = self.client.put(url, payload_put)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.put(url, payload_patch)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
