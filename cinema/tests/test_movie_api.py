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
            email="test@test.test",
            password="test_password"
        )
        self.client.force_login(self.user)

    def test_movies_list(self):
        sample_movie()
        movie_with_genres_and_actors = sample_movie()
        movie_with_genres_and_actors.genres.add(
            sample_genre(),
            sample_genre(name="Comedy"),
        )
        movie_with_genres_and_actors.actors.add(
            sample_actor(),
            sample_actor(first_name="Jim", last_name="Carrey"),

        )

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        print(serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genre(self):
        drama_genre = sample_genre(name="Drama")
        movie_without_genres = sample_movie(
            title="Movie without genres"
        )
        movie_with_genres = sample_movie(
            title="Movie with genres",
        )
        movie_with_genres.genres.add(drama_genre)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{drama_genre.id}"}
        )
        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_with_genres = MovieListSerializer(movie_with_genres)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer_without_genres.data, res.data)
        self.assertIn(serializer_with_genres.data, res.data)

    def test_filter_movies_by_actor(self):
        actor = sample_actor(
            first_name="Tom",
            last_name="Hanks"
        )
        movie_with_actor = sample_movie(title="With Actor")
        movie_with_actor.actors.add(actor)

        movie_without_actor = sample_movie(title="Without Actor")

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor.id}"}
        )

        serializer_with_actor = MovieListSerializer(movie_with_actor)
        serializer_without_actor = MovieListSerializer(movie_without_actor)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_with_actor.data, res.data)
        self.assertNotIn(serializer_without_actor.data, res.data)

    def test_filter_movies_by_title(self):
        movie_match = sample_movie(title="The Great Adventure")
        movie_no_match = sample_movie(title="Some Random Movie")

        res = self.client.get(
            MOVIE_URL,
            {"title": "Great"}
        )

        serializer_match = MovieListSerializer(movie_match)
        serializer_no_match = MovieListSerializer(movie_no_match)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_match.data, res.data)
        self.assertNotIn(serializer_no_match.data, res.data)

    def test_filter_movies_by_all_criteria(self):
        actor = sample_actor(
            first_name="Tom",
            last_name="Hanks"
        )
        genre = sample_genre(name="Action")

        matching_movie = sample_movie(title="Mission Possible")
        matching_movie.actors.add(actor)
        matching_movie.genres.add(genre)

        wrong_actor_movie = sample_movie(title="Wrong Actor")
        wrong_actor_movie.genres.add(genre)

        wrong_genre_movie = sample_movie(title="Wrong Genre")
        wrong_genre_movie.actors.add(actor)

        wrong_title_movie = sample_movie(title="Random Movie")
        wrong_title_movie.actors.add(actor)
        wrong_title_movie.genres.add(genre)

        res = self.client.get(
            MOVIE_URL,
            {
                "title": "Mission",
                "actors": str(actor.id),
                "genres": str(genre.id),
            },
        )

        serializer_match = MovieListSerializer(matching_movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_match.data, res.data)
        self.assertEqual(len(res.data), 1)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Movie Title",
            "description": "Movie Description",
            "duration": 90
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.admin",
            password="test_password",
            is_staff=True,
        )
        self.client.force_login(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Movie Title",
            "description": "Movie Description",
            "duration": 90
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self):
        actor_1 = sample_actor(
            first_name="Tom",
            last_name="Hanks"
        )
        actor_2 = sample_actor(
            first_name="Jim",
            last_name="Carrey"
        )
        genre_1 = sample_genre(name="Comedy")
        genre_2 = sample_genre(name="Action")

        payload = {
            "title": "Movie Title",
            "description": "Movie Description",
            "duration": 90,
            "genres": [genre_1.id, genre_2.id],
            "actors": [actor_1.id, actor_2.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(movie.genres.count(), 2)
        self.assertEqual(actors.count(), 2)

        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


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
