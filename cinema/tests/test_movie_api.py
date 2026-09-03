import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor

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

def movie_session_detail_url(movie_session_id):
    return reverse(
        "cinema:moviesession-detail",
        args=[movie_session_id],
    )


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
        res = self.client.get(
            movie_session_detail_url(self.movie_session.id)
        )

        self.assertIn("movie_image", res.data)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required_for_movie_list(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_movie_detail(self):
        movie = sample_movie()

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_creating_movie(self):
        payload = {
            "title": "Test movie",
            "description": "Test description",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@example.com",
            "password",
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        first_movie = sample_movie(title="First movie")
        second_movie = sample_movie(title="Second movie")

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        returned_ids = {movie["id"] for movie in res.data}

        self.assertEqual(
            returned_ids,
            {first_movie.id, second_movie.id},
        )

    def test_movie_detail(self):
        movie = sample_movie(title="Detail movie")

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], movie.id)
        self.assertEqual(res.data["title"], movie.title)
        self.assertEqual(res.data["description"], movie.description)
        self.assertEqual(res.data["duration"], movie.duration)

    def test_nonexistent_movie_returns_404(self):
        res = self.client.get(detail_url(999999))

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_movies_by_title(self):
        expected_movie = sample_movie(title="The Matrix")
        sample_movie(title="Interstellar")

        res = self.client.get(MOVIE_URL, {"title": "matrix"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        returned_ids = {movie["id"] for movie in res.data}

        self.assertEqual(returned_ids, {expected_movie.id})

    def test_title_filter_is_case_insensitive(self):
        expected_movie = sample_movie(title="The Matrix")
        sample_movie(title="Interstellar")

        res = self.client.get(MOVIE_URL, {"title": "MATRIX"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        returned_ids = {movie["id"] for movie in res.data}

        self.assertEqual(returned_ids, {expected_movie.id})

    def test_filter_movies_by_genre(self):
        drama = sample_genre(name="Drama")
        comedy = sample_genre(name="Comedy")

        drama_movie = sample_movie(title="Drama movie")
        comedy_movie = sample_movie(title="Comedy movie")

        drama_movie.genres.add(drama)
        comedy_movie.genres.add(comedy)

        res = self.client.get(MOVIE_URL, {"genres": str(drama.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        returned_ids = {movie["id"] for movie in res.data}

        self.assertEqual(returned_ids, {drama_movie.id})

    def test_filter_movies_by_multiple_genres(self):
        drama = sample_genre(name="Drama")
        comedy = sample_genre(name="Comedy")
        horror = sample_genre(name="Horror")

        drama_movie = sample_movie(title="Drama movie")
        comedy_movie = sample_movie(title="Comedy movie")
        horror_movie = sample_movie(title="Horror movie")

        drama_movie.genres.add(drama)
        comedy_movie.genres.add(comedy)
        horror_movie.genres.add(horror)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{drama.id},{comedy.id}"},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        returned_ids = {movie["id"] for movie in res.data}

        self.assertEqual(
            returned_ids,
            {drama_movie.id, comedy_movie.id},
        )
        self.assertNotIn(horror_movie.id, returned_ids)

    def test_filter_movies_by_actor(self):
        expected_actor = sample_actor(
            first_name="George",
            last_name="Clooney",
        )
        other_actor = sample_actor(
            first_name="Brad",
            last_name="Pitt",
        )

        expected_movie = sample_movie(title="Expected movie")
        other_movie = sample_movie(title="Other movie")

        expected_movie.actors.add(expected_actor)
        other_movie.actors.add(other_actor)

        res = self.client.get(
            MOVIE_URL,
            {"actors": str(expected_actor.id)},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        returned_ids = {movie["id"] for movie in res.data}

        self.assertEqual(returned_ids, {expected_movie.id})

    def test_filter_movies_by_multiple_actors(self):
        first_actor = sample_actor(
            first_name="George",
            last_name="Clooney",
        )
        second_actor = sample_actor(
            first_name="Brad",
            last_name="Pitt",
        )
        third_actor = sample_actor(
            first_name="Tom",
            last_name="Cruise",
        )

        first_movie = sample_movie(title="First movie")
        second_movie = sample_movie(title="Second movie")
        third_movie = sample_movie(title="Third movie")

        first_movie.actors.add(first_actor)
        second_movie.actors.add(second_actor)
        third_movie.actors.add(third_actor)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{first_actor.id},{second_actor.id}"},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        returned_ids = {movie["id"] for movie in res.data}

        self.assertEqual(
            returned_ids,
            {first_movie.id, second_movie.id},
        )
        self.assertNotIn(third_movie.id, returned_ids)

    def test_filter_movies_by_title_genre_and_actor(self):
        drama = sample_genre(name="Drama")
        comedy = sample_genre(name="Comedy")

        george = sample_actor(
            first_name="George",
            last_name="Clooney",
        )
        brad = sample_actor(
            first_name="Brad",
            last_name="Pitt",
        )

        expected_movie = sample_movie(title="Ocean Eleven")
        wrong_genre_movie = sample_movie(title="Ocean Comedy")
        wrong_actor_movie = sample_movie(title="Ocean Twelve")

        expected_movie.genres.add(drama)
        expected_movie.actors.add(george)

        wrong_genre_movie.genres.add(comedy)
        wrong_genre_movie.actors.add(george)

        wrong_actor_movie.genres.add(drama)
        wrong_actor_movie.actors.add(brad)

        res = self.client.get(
            MOVIE_URL,
            {
                "title": "ocean",
                "genres": str(drama.id),
                "actors": str(george.id),
            },
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        returned_ids = {movie["id"] for movie in res.data}

        self.assertEqual(returned_ids, {expected_movie.id})

    def test_authenticated_user_cannot_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()

        payload = {
            "title": "Forbidden movie",
            "description": "Description",
            "duration": 100,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            Movie.objects.filter(title="Forbidden movie").exists()
        )


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "admin@example.com",
            "password",
        )
        self.client.force_authenticate(self.admin)

    def test_admin_can_create_movie(self):
        # твій наявний код
        ...

    def test_create_movie_with_invalid_data(self):
        # твій наявний код
        ...

    def test_update_method_is_not_allowed(self):
        movie = sample_movie()

        res = self.client.put(
            detail_url(movie.id),
            {
                "title": "Updated title",
                "description": movie.description,
                "duration": movie.duration,
            },
            format="json",
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_delete_method_is_not_allowed(self):
        movie = sample_movie()

        res = self.client.delete(detail_url(movie.id))

        self.assertEqual(
            res.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertTrue(Movie.objects.filter(id=movie.id).exists())
