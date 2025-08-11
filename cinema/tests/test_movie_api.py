import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer, MovieSerializer

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


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "test_password"
        )
        self.client.force_authenticate(self.user)

    def test_filter_movies_by_actors(self):
        # Create two movies
        movie = sample_movie()
        movie_with_actors = sample_movie(description="Movie with actors")

        # Create actor
        actor1 = sample_actor()
        # Add actor to movie_with_actors
        movie_with_actors.actors.add(actor1)

        # Get movie list
        response = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        # Check without filters
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

        # Check without actors filter
        response = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        serializer1 = MovieListSerializer(movie)
        serializer2 = MovieListSerializer(movie_with_actors)

        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer1.data, response.data)

    def test_filter_movies_by_genres(self):
        # Create two movies
        movie = sample_movie()
        movie_with_genres = sample_movie(
            description="Movie with genres"
        )

        # Create two genres
        genre_1 = sample_genre(name="test1")
        genre_2 = sample_genre(name="test2")

        movie_with_genres.genres.add(genre_1, genre_2)

        serializer_for_movie_with_genres = MovieListSerializer(
            movie_with_genres
        )
        serializer_for_movie = MovieListSerializer(movie)

        response = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        self.assertIn(serializer_for_movie_with_genres.data, response.data)
        self.assertNotIn(serializer_for_movie.data, response.data)

    def test_filter_movies_by_title(self):
        # Create two movies
        movie = sample_movie()
        movie_with_title = sample_movie(
            title="inception"
        )

        serializer_for_movie_with_title = MovieListSerializer(
            movie_with_title
        )
        serializer_for_movie = MovieListSerializer(movie)

        response = self.client.get(
            MOVIE_URL,
            {"title": "cept"}
        )

        self.assertIn(serializer_for_movie_with_title.data, response.data)
        self.assertNotIn(serializer_for_movie.data, response.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        actor = sample_actor()
        genre = sample_genre()

        movie.actors.add(actor)
        movie.genres.add(genre)

        url = detail_url(movie.id)
        response = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        actor = sample_actor()
        genre = sample_genre()
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id]
        }

        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@admin.com", "password", is_staff=True
        )
        self.client.force_authenticate(self.user)
        self.actor = sample_actor()
        self.genre = sample_genre()
        self.genre_two = sample_genre(name="Genre 2")

    def test_create_movie(self):
        """
        genres = Genre.objects.values_list("id", flat=True)
        print(people)
        Result
        <QuerySet [1, 2, 3]>

        Example of ManyRelatedManager:
        movie = Movie.objects.get(id=1)
        genres_manager = movie.genres  # Access the ManyRelatedManager
        """

        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": [self.genre.id],  # TODO: Can't be empty
            # In order to change this, I can change genres = models.ManyToManyField(Genre)
            # to genres = models.ManyToManyField(Genre, blank=True)
            "actors": [self.actor.id]
        }

        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=response.data["id"])
        for key in payload:
            if key == "genres" or key == "actors":
                # when the key is "genres" or "actors", the ManyRelatedManager object
                # is converted to a list of IDs using the values_list() method.
                attribute = list(getattr(movie, key).values_list("id", flat=True))
                # If key == "genres", attribute will be ManyRelatedManager (movie.genres) converted to
                # list of IDs of related genres
            else:
                attribute = getattr(movie, key)
            self.assertEqual(payload[key], attribute)

    def test_delete_movie_is_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
