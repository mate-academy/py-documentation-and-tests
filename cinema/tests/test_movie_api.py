import os
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Actor, CinemaHall, Genre, Movie, MovieSession
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
        self.client = APIClient()

    def test_auth_required(self):
        result = self.client.get(MOVIE_URL)
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "address@test.com",
            "password_test"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        genre = sample_genre()
        actor = sample_actor()
        sample_movie()
        movie_with_genre = sample_movie(title="test_one")
        movie_with_actor = sample_movie(title="test_two")

        movie_with_genre.genres.add(genre)
        movie_with_actor.actors.add(actor)

        result = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="test one")
        movie2 = sample_movie(title="test two")
        movie3 = sample_movie(title="test three")

        result_1 = self.client.get(MOVIE_URL, {"title": "one"})
        result_2 = self.client.get(MOVIE_URL, {"title": "test"})

        serializer_1 = MovieListSerializer(movie1)
        serializer_2 = MovieListSerializer(movie2)
        serializer_3 = MovieListSerializer(movie3)

        self.assertIn(serializer_1.data, result_1.data)
        self.assertNotIn(serializer_2.data, result_1.data)
        self.assertNotIn(serializer_3.data, result_1.data)
        self.assertEqual(len(result_2.data), 3)

    def test_filter_movies_by_genres(self):
        movie1 = sample_movie(title="test one")
        movie2 = sample_movie(title="test two")
        movie3 = sample_movie(title="test three")

        genre1 = sample_genre(name="horror")
        genre2 = sample_genre(name="comedy")
        genre3 = sample_genre(name="western")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)
        movie3.genres.add(genre3)

        result = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, result.data)
        self.assertIn(serializer2.data, result.data)
        self.assertNotIn(serializer3.data, result.data)

    def test_filter_movies_by_actors(self):
        movie1 = sample_movie(title="test one")
        movie2 = sample_movie(title="test two")
        movie3 = sample_movie(title="test three")

        actor1 = sample_actor(first_name="Jessica")
        actor2 = sample_actor(first_name="Adam")
        actor3 = sample_actor(first_name="Patricia")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)
        movie3.actors.add(actor3)

        result = self.client.get(MOVIE_URL, {"actors": f"{actor2.id},{actor3.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertNotIn(serializer1.data, result.data)
        self.assertIn(serializer2.data, result.data)
        self.assertIn(serializer3.data, result.data)

    def test_filter_movies_by_title_and_actors_and_genres(self):
        movie1 = sample_movie(title="test one")
        movie2 = sample_movie(title="test two")

        genre1 = sample_genre(name="horror")
        genre2 = sample_genre(name="comedy")

        actor1 = sample_actor(first_name="Jessica")
        actor2 = sample_actor(first_name="Adam")

        movie1.genres.add(genre1)
        movie1.actors.add(actor1)

        movie2.genres.add(genre2)
        movie2.actors.add(actor2)

        result_1 = self.client.get(MOVIE_URL, data={
            "title": "one",
            "genres": str(genre1.id),
            "actors": str(actor1.id),
        })
        result_2 = self.client.get(MOVIE_URL, data={
            "title": "test",
            "genres": str(genre1.id),
            "actors": str(actor2.id),
        })

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, result_1.data)
        self.assertNotIn(serializer2.data, result_1.data)
        self.assertNotIn(serializer1.data, result_2.data)
        self.assertNotIn(serializer2.data, result_2.data)
        self.assertEqual(len(result_2.data), 0)

    def test_retrieve_movie_detail(self):
        movie = sample_movie(title="test")
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        url = detail_url(movie_id=movie.id)
        result = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_create_movie_forbidden(self):
        data = {
            "title": "Hobbit",
            "description": "journey",
            "duration": 180,
        }

        result = self.client.post(MOVIE_URL, data)

        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@test.com",
            "password_admin_test",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "Hobbit",
            "description": "journey",
            "duration": 180,
            "genres": genre.id,
            "actors": actor.id
        }

        result = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=result.data["id"])

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)

        self.assertEqual(payload["title"], getattr(movie, "title"))
        self.assertEqual(payload["description"], getattr(movie, "description"))
        self.assertEqual(payload["duration"], getattr(movie, "duration"))
        self.assertEqual(payload["genres"], getattr(movie, "genres").first().id)
        self.assertEqual(payload["actors"], getattr(movie, "actors").first().id)

    def test_create_movie_without_actors_and_genres(self):
        payload = {
            "title": "Hobbit",
            "description": "journey",
            "duration": 180,
            "genres": [],
            "actors": []
        }
        result = self.client.post(MOVIE_URL, payload)

        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_movie_not_allowed(self):
        movie = sample_movie(
            title="Hobbit",
            description="journey",
            duration=180
        )
        payload = {
            "title": "Hobbit 2",
            "description": "Great journey",
            "duration": 190
        }
        url = detail_url(movie_id=movie.id)

        result = self.client.put(url, payload)

        self.assertEqual(result.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie_id=movie.id)

        result = self.client.delete(url)

        self.assertEqual(result.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
