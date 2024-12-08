import os
import tempfile
from datetime import datetime

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Actor, CinemaHall, Genre, Movie, MovieSession

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params) -> Movie:
    """Create and return a sample movie for testing"""
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params) -> Genre:
    """Create and return a sample genre for testing"""
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params) -> Actor:
    """Create and return a sample actor for testing"""
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params) -> MovieSession:
    """Create and return a sample movie session for testing"""
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )

    defaults = {
        "show_time": timezone.make_aware(
            datetime(2022, 6, 2, 14, 0)
        ),
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id: int) -> str:
    """Return URL for movie image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id: int) -> str:
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self) -> None:
        self.movie.image.delete()

    def test_upload_image_to_movie(self) -> None:
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

    def test_upload_image_bad_request(self) -> None:
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list(self) -> None:
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

    def test_image_url_is_shown_on_movie_detail(self) -> None:
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self) -> None:
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data["results"][0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self) -> None:
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data["results"][0].keys())


class MovieViewSetTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.genre = sample_genre(name="Test genre")
        self.actor = sample_actor(first_name="Test", last_name="Actor")

    def test_list_movies(self) -> None:
        """Test retrieving a list of movies"""
        sample_movie()
        sample_movie(title="Another movie")

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)

    def test_retrieve_movie_detail(self) -> None:
        """Test retrieving movie details"""
        movie = sample_movie()
        movie.genres.add(self.genre)
        movie.actors.add(self.actor)

        url = detail_url(movie.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        for key in ["title", "description", "duration"]:
            self.assertEqual(res.data[key], getattr(movie, key))

        self.assertIn(
            self.genre.id, [genre["id"] for genre in res.data["genres"]]
        )
        self.assertIn(
            self.actor.id, [actor["id"] for actor in res.data["actors"]]
        )

    def test_create_movie(self) -> None:
        """Test creating a new movie"""
        payload = {
            "title": "New movie",
            "description": "New description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])

        for key in ["title", "description", "duration"]:
            self.assertEqual(payload[key], getattr(movie, key))

        genres = movie.genres.all()
        actors = movie.actors.all()
        self.assertEqual(len(genres), 1)
        self.assertEqual(len(actors), 1)
        self.assertEqual(genres[0].id, self.genre.id)
        self.assertEqual(actors[0].id, self.actor.id)

    def test_update_movie_not_allowed(self) -> None:
        """Test that PUT method is not allowed"""
        movie = sample_movie()
        movie.genres.add(self.genre)
        movie.actors.add(self.actor)

        payload = {
            "title": "Updated movie",
            "description": "Updated description",
            "duration": 150,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        url = detail_url(movie.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        movie.refresh_from_db()
        self.assertEqual(movie.title, "Sample movie")
        self.assertEqual(movie.description, "Sample description")
        self.assertEqual(movie.duration, 90)

    def test_partial_update_movie_not_allowed(self) -> None:
        """Test that PATCH method is not allowed"""
        movie = sample_movie()
        movie.genres.add(self.genre)
        movie.actors.add(self.actor)

        payload = {"title": "Updated movie title"}

        url = detail_url(movie.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        movie.refresh_from_db()
        self.assertEqual(movie.title, "Sample movie")

    def test_delete_movie_not_allowed(self) -> None:
        """Test that DELETE method is not allowed"""
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Movie.objects.filter(id=movie.id).exists())

    def test_create_movie_without_required_fields(self) -> None:
        """Test creating a movie without required fields fails"""
        payload = {
            "description": "New description",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            Movie.objects.filter(description=payload["description"]).exists()
        )

    def test_filter_movies_by_title(self) -> None:
        """Test filtering movies by title"""
        movie1 = sample_movie(title="Inception")
        sample_movie(title="The Dark Knight")

        res = self.client.get(MOVIE_URL, {"title": "inc"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["title"], movie1.title)

    def test_filter_movies_by_genres(self) -> None:
        """Test filtering movies by genres"""
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Comedy")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["title"], movie1.title)

    def test_filter_movies_by_actors(self) -> None:
        """Test filtering movies by actors"""
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        actor1 = sample_actor(first_name="Brad", last_name="Pitt")
        actor2 = sample_actor(first_name="Tom", last_name="Cruise")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["title"], movie1.title)

    def test_filter_movies_by_multiple_parameters(self) -> None:
        """Test filtering movies by multiple parameters"""
        movie1 = sample_movie(title="Action movie")
        movie2 = sample_movie(title="Drama movie")
        genre = sample_genre(name="Action")
        actor = sample_actor(first_name="Action", last_name="Star")

        movie1.genres.add(genre)
        movie1.actors.add(actor)
        movie2.genres.add(genre)

        res = self.client.get(
            MOVIE_URL,
            {
                "title": "action",
                "genres": f"{genre.id}",
                "actors": f"{actor.id}",
            },
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["title"], movie1.title)

    def test_create_movie_with_missing_duration(self) -> None:
        """Test creating a movie without duration fails"""
        payload = {
            "title": "New movie",
            "description": "New description",
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Movie.objects.filter(title=payload["title"]).exists())

    def test_create_movie_with_empty_title(self) -> None:
        """Test creating a movie with empty title fails"""
        payload = {
            "title": "",
            "description": "New description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            Movie.objects.filter(description=payload["description"]).exists()
        )

    def test_create_movie_with_non_existing_genre(self) -> None:
        """Test creating a movie with non-existing genre fails"""
        payload = {
            "title": "New movie",
            "description": "New description",
            "duration": 120,
            "genres": [9999],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Movie.objects.filter(title=payload["title"]).exists())

    def test_create_movie_with_non_existing_actor(self) -> None:
        """Test creating a movie with non-existing actor fails"""
        payload = {
            "title": "New movie",
            "description": "New description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [9999],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Movie.objects.filter(title=payload["title"]).exists())

    def test_unauthorized_user_cant_create_movie(self) -> None:
        """Test that unauthorized user can't create a movie"""
        self.client.force_authenticate(user=None)
        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Movie.objects.filter(title=payload["title"]).exists())

    def test_retrieve_returns_correct_serializer(self) -> None:
        """Test that retrieve action returns MovieDetailSerializer"""
        movie = sample_movie()
        movie.genres.add(self.genre)
        movie.actors.add(self.actor)

        url = detail_url(movie.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("genres", res.data)
        self.assertIsInstance(res.data["genres"], list)
        self.assertIn("name", res.data["genres"][0])
        self.assertIn("actors", res.data)
        self.assertIsInstance(res.data["actors"], list)
        self.assertIn("full_name", res.data["actors"][0])

    def test_create_movie_with_empty_genres(self) -> None:
        """Test creating a movie without genres fails"""
        payload = {
            "title": "New movie",
            "description": "New description",
            "duration": 120,
            "genres": [],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Movie.objects.filter(title=payload["title"]).exists())

    def test_create_movie_with_empty_actors(self) -> None:
        """Test creating a movie without actors fails"""
        payload = {
            "title": "New movie",
            "description": "New description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Movie.objects.filter(title=payload["title"]).exists())

    def test_create_movie_with_empty_description(self) -> None:
        """Test creating a movie with empty description fails"""
        payload = {
            "title": "New movie",
            "description": "",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Movie.objects.filter(title=payload["title"]).exists())

    def test_get_movie_detail_invalid_id(self) -> None:
        """Test getting movie details with invalid ID fails"""
        url = detail_url(9999)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
