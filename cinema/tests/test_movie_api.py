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


class MovieApiTest(TestCase):
    def setUp(self) -> None:
        superuser = get_user_model().objects.create_superuser(
            email="superuser@example.com",
            password="123456"
        )
        self.client = APIClient()
        self.client.force_authenticate(superuser)

    def test_not_allowed_methods(self) -> None:
        movie = sample_movie()
        url = detail_url(movie.id)
        cases = [
            ["put", self.client.put],
            ["patch", self.client.patch],
            ["delete", self.client.delete],
        ]

        for name, request_method in cases:
            msg = f"'{name}' method should be not allowed"
            with self.subTest(msg, method=request_method):
                response = request_method(url)
                self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.movie = sample_movie()

    def test_unauthenticated_user_does_not_have_access(self) -> None:
        movie_detail_url = detail_url(self.movie.id)
        test_cases = [
            [MOVIE_URL, self.client.get],
            [MOVIE_URL, self.client.post],
            [movie_detail_url, self.client.get],
        ]

        for url, request_method in test_cases:
            with self.subTest(url=url, request_method=request_method):
                response = request_method(url)
                self.assertEqual(
                    response.status_code,
                    status.HTTP_401_UNAUTHORIZED
                )


class IsAuthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.movie = sample_movie()
        self.movie_with_parameter_1 = sample_movie(
            title="Movie_wit_parameter_1"
        )
        self.movie_with_parameter_2 = sample_movie(
            title="Movie_wit_parameter_2"
        )
        self.movie_with_parameter_3 = sample_movie(
            title="Movie_wit_parameter_3"
        )
        self.movie_with_parameter_1_and_3 = sample_movie(
            title="Movie_wit_parameter_1_and_3"
        )
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="123456"
        )
        self.client = APIClient()
        self.movie = sample_movie()

        self.client.force_authenticate(self.user)

    def test_get_list_movies(self) -> None:
        response = self.client.get(MOVIE_URL)

        expected_data = MovieListSerializer(
            Movie.objects.all(),
            many=True
        ).data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_retrieve_movie_detail(self) -> None:
        url = detail_url(self.movie.id)
        response = self.client.get(url)

        expected_data = MovieDetailSerializer(
            self.movie
        ).data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_filtering_by_actors(self) -> None:
        actor_1 = sample_actor(
            first_name="Test_1 name", last_name="Test_last_name"
        )
        actor_2 = sample_actor(
            first_name="Test_2 name", last_name="Test_last_name"
        )
        actor_3 = sample_actor(
            first_name="Test_3 name", last_name="Test_last_name"
        )

        self.movie_with_parameter_1.actors.add(actor_1)
        self.movie_with_parameter_2.actors.add(actor_2)
        self.movie_with_parameter_3.actors.add(actor_3)
        self.movie_with_parameter_1_and_3.actors.add(actor_1, actor_3)

        response = self.client.get(
            MOVIE_URL, data={"actors": f"{actor_1.id},{actor_2.id}"}
        )

        movies_qs = Movie.objects.filter(
            actors__id__in=[actor_1.id, actor_2.id]
        )
        expected_data = MovieListSerializer(movies_qs, many=True).data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_filtering_by_title(self) -> None:
        filter_param = "parameter_1"

        response = self.client.get(MOVIE_URL, data={"title": filter_param})

        movies_qs = Movie.objects.filter(title__icontains=filter_param)
        expected_data = MovieListSerializer(
            movies_qs, many=True
        ).data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_filtering_by_genres(self) -> None:
        genre_1 = sample_genre(
            name="Genre 1"
        )
        genre_2 = sample_genre(
            name="Genre 2"
        )
        genre_3 = sample_genre(
            name="Genre 3"
        )

        self.movie_with_parameter_1.genres.add(genre_1)
        self.movie_with_parameter_2.genres.add(genre_2)
        self.movie_with_parameter_3.genres.add(genre_3)
        self.movie_with_parameter_1_and_3.genres.add(genre_1, genre_3)

        response = self.client.get(
            MOVIE_URL, data={"genres": f"{genre_1.id},{genre_2.id}"}
        )

        movies_qs = Movie.objects.filter(
            genres__in=[genre_1, genre_2]
        )
        expected_data = MovieListSerializer(movies_qs, many=True).data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_post_method_forbidden(self) -> None:
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 90
        }

        response = self.client.post(MOVIE_URL, data=payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class IsAdminMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_superuser(
            email="super_user@example.com",
            password="123456"
        )
        self.movie = sample_movie()

        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_create_movie(self) -> None:
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 90
        }

        response = self.client.post(MOVIE_URL, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_movie = Movie.objects.get(id=response.data["id"])

        for key in payload:
            self.assertEqual(payload[key], getattr(created_movie, key))

    def test_create_movie_with_genres(self) -> None:
        genre_1 = sample_genre(name="Genre_1")
        genre_2 = sample_genre(name="Genre_2")
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 90,
            "genres": [genre_1.id, genre_2.id]
        }

        response = self.client.post(MOVIE_URL, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_movie = Movie.objects.get(id=response.data["id"])
        genres = created_movie.genres.all()

        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(len(genres), 2)

    def test_create_movie_with_actors(self) -> None:
        actor_1 = sample_actor(
            first_name="Test_first_name_1",
            last_name="Test_last_name_1"
        )
        actor_2 = sample_actor(
            first_name="Test_first_name_2",
            last_name="Test_last_name_2"
        )
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 90,
            "actors": [actor_1.id, actor_2.id]
        }

        response = self.client.post(MOVIE_URL, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_movie = Movie.objects.get(id=response.data["id"])
        actors = created_movie.actors.all()

        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(len(actors), 2)
