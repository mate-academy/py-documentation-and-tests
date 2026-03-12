import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

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


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com", "password"
        )
        self.client.force_authenticate(user=self.user)

    def test_retrieve_movies_as_authenticated_user(self):
        res = self.client.get(MOVIE_URL)
        items = Movie.objects.all()
        serializer = MovieListSerializer(items, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_movie_filtering_by_genres(self):
        genre_comedy = sample_genre(name="Comedy Genre Test")
        genre_horror = sample_genre(name="Horror Genre Test")
        comedy_movie = sample_movie(title="Comedy Movie Test")
        horror_movie = sample_movie(title="Horror Movie Test")

        comedy_movie.genres.add(genre_comedy)
        horror_movie.genres.add(genre_horror)

        filtering_params_comedy = {"genres": f"{genre_comedy.id}"}
        filtering_params_horror = {"genres": f"{genre_horror.id}"}

        res_comedy = self.client.get(MOVIE_URL, filtering_params_comedy)
        self.assertEqual(res_comedy.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_comedy.json()), 1)
        self.assertEqual(res_comedy.json()[0]["title"], comedy_movie.title)

        res_horror = self.client.get(MOVIE_URL, filtering_params_horror)
        self.assertEqual(res_horror.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_horror.json()), 1)
        self.assertEqual(res_horror.json()[0]["title"], horror_movie.title)

    def text_movie_filtering_by_actors(self):
        actor_1 = sample_actor(first_name="Actor", last_name="One")
        actor_2 = sample_actor(first_name="Actor", last_name="Two")
        movie_1 = sample_movie(title="Movie One")
        movie_2 = sample_movie(title="Movie Two")

        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_2)

        filtering_params_actor_1 = {"actors": f"{actor_1.id}"}
        filtering_params_actor_2 = {"actors": f"{actor_2.id}"}

        res_actor_1 = self.client.get(MOVIE_URL, filtering_params_actor_1)
        self.assertEqual(res_actor_1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_actor_1.json()), 1)
        self.assertEqual(res_actor_1.json()[0]["title"], movie_1.title)

        res_actor_2 = self.client.get(MOVIE_URL, filtering_params_actor_2)
        self.assertEqual(res_actor_2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_actor_2.json()), 1)
        self.assertEqual(res_actor_2.json()[0]["title"], movie_2.title)

    def test_movie_filtering_by_title(self):
        movie_1 = sample_movie(title="Unique Movie Title")
        movie_2 = sample_movie(title="Another Movie Title")

        filtering_params_title = {"title": "Unique Movie Title"}

        res = self.client.get(MOVIE_URL, filtering_params_title)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]["title"], movie_1.title)

        res = self.client.get(MOVIE_URL, {"title": "Another Movie Title"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]["title"], movie_2.title)

    def test_movie_filtering_by_title_and_genre_and_actors(self):
        genre_comedy = sample_genre(name="Comedy Genre Test")
        genre_horror = sample_genre(name="Horror Genre Test")
        actor_1 = sample_actor(first_name="Actor", last_name="One")
        actor_2 = sample_actor(first_name="Actor", last_name="Two")
        movie_1 = sample_movie(title="Unique Movie Title")
        movie_2 = sample_movie(title="Another Movie Title")

        movie_1.genres.add(genre_comedy)
        movie_1.actors.add(actor_1)

        movie_2.genres.add(genre_horror)
        movie_2.actors.add(actor_2)

        filtering_params = {
            "title": "Unique Movie Title",
            "genres": f"{genre_comedy.id}",
            "actors": f"{actor_1.id}",
        }

        res = self.client.get(MOVIE_URL, filtering_params)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]["title"], movie_1.title)

    def test_filterning_by_non_existent_genre(self):
        filtering_params = {"genres": "9999"}
        res = self.client.get(MOVIE_URL, filtering_params)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.json()), 0)

    def test_filterning_by_non_existent_actor(self):
        filtering_params = {"actors": "9999"}
        res = self.client.get(MOVIE_URL, filtering_params)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.json()), 0)

    def test_filterning_by_non_existent_title(self):
        filtering_params = {"title": "Non Existent Movie Title"}
        res = self.client.get(MOVIE_URL, filtering_params)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.json()), 0)

    def test_single_movie_retrieval(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], movie.title)
        self.assertEqual(res.data["description"], movie.description)
        self.assertEqual(res.data["duration"], movie.duration)

    def test_create_movie_not_allowed(self):
        payload = {
            "title": "Test not existent Movie",
            "description": "New Movie Description",
            "duration": 120,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title=payload["title"]).exists())


class AdminMovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        admin_user = get_user_model().objects.create_user(
            email="admin@example.com",
            password="adminpassword",
            is_staff=True,
        )
        self.client.force_authenticate(user=admin_user)

    def test_create_movie_as_admin(self):
        action_genre = sample_genre(name="Action")
        test_actor = sample_actor(first_name="Test", last_name="Actor")
        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 120,
            "genres": [action_genre.id],
            "actors": [test_actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title=payload["title"]).exists())
