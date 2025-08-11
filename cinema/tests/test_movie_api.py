import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer

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


class MovieViewSetUnLoggedTest(TestCase):

    def test_get_list_movies(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieViewSetUserTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        user = get_user_model().objects.create_user(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(user)
        for _ in range(5):
            sample_movie()

    def test_get_list(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_filter_by_actor(self):
        movie1 = sample_movie()
        actor1 = sample_actor()
        actor_query = f"?actors={actor1.id}"

        response = self.client.get(MOVIE_URL + actor_query)
        self.assertEqual(response.data, [])

        movie1.actors.add(actor1)

        response = self.client.get(MOVIE_URL + actor_query)
        serializer = MovieListSerializer([movie1], many=True).data
        self.assertEqual(response.data, serializer)

        movie2 = sample_movie()
        actor2 = sample_actor()
        movie2.actors.add(actor2)
        actor_query += f",{actor2.id}"

        response = self.client.get(MOVIE_URL + actor_query)
        serializer = MovieListSerializer([movie1, movie2], many=True).data
        self.assertEqual(response.data, serializer)

    def test_list_filter_by_genre(self):
        movie1 = sample_movie()
        genre1 = sample_genre()
        genre_query = f"?genres={genre1.id}"

        response = self.client.get(MOVIE_URL + genre_query)
        self.assertEqual(response.data, [])

        movie1.genres.add(genre1)

        response = self.client.get(MOVIE_URL + genre_query)
        serializer = MovieListSerializer([movie1], many=True).data
        self.assertEqual(response.data, serializer)

        movie2 = sample_movie()
        genre2 = sample_genre(name="Comedy")
        movie2.genres.add(genre2)
        genre_query += f",{genre2.id}"

        response = self.client.get(MOVIE_URL + genre_query)
        serializer = MovieListSerializer([movie1, movie2], many=True).data
        self.assertEqual(response.data, serializer)

    def test_list_filter_by_title(self):
        movie = sample_movie(title="Test")
        title_query = f"?title={movie.title}"

        response = self.client.get(MOVIE_URL + title_query + "a")
        self.assertEqual(response.data, [])

        response = self.client.get(MOVIE_URL + title_query)
        serializer = MovieListSerializer([movie], many=True).data
        self.assertEqual(response.data, serializer)

    def test_list_filter_by_actors_genres_title(self):
        movie = sample_movie()
        actor = sample_actor()
        genre = sample_genre()
        filter_query = f"?title={movie.title}&actors={actor.id}&genres={genre.id}"

        movie.actors.add(actor)
        movie.genres.add(genre)

        response = self.client.get(MOVIE_URL + filter_query)
        serializer = MovieListSerializer([movie], many=True).data
        self.assertEqual(response.data, serializer)

    def test_unsafe_method(self):
        response = self.client.delete(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.put(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MovieViewSetAdminTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(user)

    def test_get_detail(self):
        movie = sample_movie()
        response = self.client.get(
            reverse(
                "cinema:movie-detail",
                kwargs={"pk": movie.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        response = self.client.delete(MOVIE_URL)
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_post(self):
        genre = sample_genre()
        actor = sample_actor()

        data = {
            "title": "Title",
            "description": "Description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        response = self.client.post(MOVIE_URL, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), 1)

    def test_update(self):
        response = self.client.patch(
            reverse("cinema:movie-detail", kwargs={"pk": 1})
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
