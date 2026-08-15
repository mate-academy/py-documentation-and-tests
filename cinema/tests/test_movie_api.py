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


MOVIE_URL = reverse("cinema:movie-list")

class UnauthenticateMovieApiTests(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEquals(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticateMovieApiTests(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email = "testuser@test.user",
            password = "testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        movie_with_genres_and_actors = sample_movie()

        genre_1 = sample_genre()
        genre_2 = sample_genre(name="Comedy")
        actor_1 = sample_actor()
        actor_2 = sample_actor(first_name="Mat", last_name="Damon")

        movie_with_genres_and_actors.genres.add(genre_1, genre_2)
        movie_with_genres_and_actors.actors.add(actor_1, actor_2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEquals(res.data, serializer.data)

    def test_filter_by_genres(self):
         movie_without_genre = sample_movie()
         movie_with_genre_drama = sample_movie(title="Schindler's List")
         movie_with_genre_comedy = sample_movie(title="Groundhog Day")

         genre_drame = sample_genre()
         genre_comedy = sample_genre(name="Comedy")

         movie_with_genre_drama.genres.add(genre_drame)
         movie_with_genre_comedy.genres.add(genre_comedy)

         res = self.client.get(
             MOVIE_URL,
             data={"genres": f"{genre_drame.id},{genre_comedy.id}"}
         )
         serializer_without_genre = MovieListSerializer(movie_without_genre)
         serializer_with_genre_drama = MovieListSerializer(movie_with_genre_drama)
         serializer_with_genre_comedy = MovieListSerializer(movie_with_genre_comedy)

         self.assertIn(serializer_with_genre_comedy.data, res.data)
         self.assertIn(serializer_with_genre_drama.data, res.data)
         self.assertNotIn(serializer_without_genre.data, res.data)

    def test_filter_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actor_1 = sample_movie(title="Schindler's List")
        movie_with_actor_2 = sample_movie(title="Groundhog Day")

        actor_1 = sample_actor()
        actor_2 = sample_actor(first_name="Mat", last_name="Damon")

        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        res = self.client.get(
            MOVIE_URL,
            data={"actors": f"{actor_1.id},{actor_2.id}"}
        )
        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_with_actor_1 = MovieListSerializer(movie_with_actor_1)
        serializer_with_actor_2 = MovieListSerializer(movie_with_actor_2)

        self.assertIn(serializer_with_actor_1.data, res.data)
        self.assertIn(serializer_with_actor_2.data, res.data)
        self.assertNotIn(serializer_without_actors.data, res.data)

    def test_filter_by_title(self):
        default_movie = sample_movie()
        movie_with_title = sample_movie(title="Schindler's List")

        res = self.client.get(
            MOVIE_URL,
            data={"title": f"{movie_with_title.title}"}
        )
        serializer_default_movie = MovieListSerializer(default_movie)
        serializer_movie_with_title = MovieListSerializer(movie_with_title)

        self.assertIn(serializer_movie_with_title.data, res.data)
        self.assertNotIn(serializer_default_movie.data, res.data)

    def test_retrieve_movie_detail(self):
        movie_with_genres_and_actors = sample_movie()

        genre_1 = sample_genre()
        genre_2 = sample_genre(name="Comedy")
        actor_1 = sample_actor()
        actor_2 = sample_actor(first_name="Mat", last_name="Damon")

        movie_with_genres_and_actors.genres.add(genre_1, genre_2)
        movie_with_genres_and_actors.actors.add(actor_1, actor_2)

        serializer = MovieDetailSerializer(movie_with_genres_and_actors)

        url = detail_url(movie_with_genres_and_actors.id)

        res = self.client.get(url)

        self.assertEquals(res.status_code, status.HTTP_200_OK)
        self.assertEquals(serializer.data, res.data)

    def test_create_movie_401_status_code(self):
        res = self.client.post(
            MOVIE_URL,
            data = {}
        )

        self.assertEquals(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email = "admin.user@test.admin",
            password = "testpassword",
            is_staff = True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_with_genres_and_actors(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "actors": [actor.id, ],
            "genres": [genre.id, ],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEquals(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])

        for key in {"title", "description", "duration"}:
            self.assertEquals(
                payload[key], getattr(movie, key)
            )
        genre_ids = [genre.id for genre in movie.genres.all()]
        actors_ids = [actor.id for actor in movie.actors.all()]

        self.assertEquals(payload["genres"], genre_ids)
        self.assertEquals(payload["actors"], actors_ids)
