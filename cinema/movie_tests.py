import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from PIL import Image

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

TEST_MEDIA_ROOT = tempfile.mkdtemp()


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Movie Title",
        "description": "Movie Description",
        "duration": 100,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


class UnauthenticatedMovieViewTest(APITestCase):

    def test_unauthenticated(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieAuthorisedViewTest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@email.com",
            password="test_password1",
        )
        self.client.force_authenticate(user=self.user)

        self.genre_1 = Genre.objects.create(name="Genre1")
        self.genre_2 = Genre.objects.create(name="Genre2")

        self.actor1 = Actor.objects.create(
            first_name="Test Actor",
            last_name="Test Actor Last"
        )
        self.actor2 = Actor.objects.create(
            first_name="Test Actor two",
            last_name="Test Actor Last"
        )

        self.movie = sample_movie()
        self.movie_genres = sample_movie(
            title="Movie Genres",
            description="Movie Description",
            duration=100
        )
        self.movie_genres.genres.add(self.genre_1, self.genre_2)
        self.movie_actors = sample_movie(
            title="Movie Actors",
            description="Movie Description",
            duration=100
        )
        self.movie_actors.actors.add(self.actor1, self.actor2)
        self.movie_with_actors_genres = sample_movie(
            title="Movie Actors Genres",
            description="Movie Description",
            duration=100
        )
        self.movie_with_actors_genres.genres.add(self.genre_1, self.genre_2)
        self.movie_with_actors_genres.actors.add(self.actor1, self.actor2)

    def test_movies_list(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies(self):
        response = self.client.get(MOVIE_URL, data={"title": "Tit"})
        movie_serializer = MovieListSerializer(self.movie)
        movie_actors_serializer = MovieListSerializer(self.movie_actors)
        movie_genres_serializer = MovieListSerializer(self.movie_genres)
        movie_actors_genres_serializer = MovieListSerializer(
            self.movie_with_actors_genres
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(movie_serializer.data, response.data)
        self.assertNotIn(movie_actors_serializer.data, response.data)
        self.assertNotIn(movie_genres_serializer.data, response.data)
        self.assertNotIn(movie_actors_genres_serializer.data, response.data)

        filter_genres_response = self.client.get(
            MOVIE_URL,
            data={"genres": f"{self.genre_1.id}, {self.genre_2.id}"}
        )
        self.assertEqual(
            filter_genres_response.status_code,
            status.HTTP_200_OK
        )
        self.assertIn(
            movie_genres_serializer.data,
            filter_genres_response.data
        )
        self.assertIn(
            movie_actors_genres_serializer.data,
            filter_genres_response.data
        )
        self.assertNotIn(movie_serializer.data, filter_genres_response.data)
        self.assertNotIn(
            movie_actors_serializer.data,
            filter_genres_response.data
        )

        filter_actors_response = self.client.get(
            MOVIE_URL,
            data={"actors": f"{self.actor1.id}, {self.actor2.id}"}
        )
        self.assertEqual(
            filter_actors_response.status_code,
            status.HTTP_200_OK
        )
        self.assertIn(
            movie_actors_serializer.data,
            filter_actors_response.data
        )
        self.assertIn(
            movie_actors_genres_serializer.data,
            filter_actors_response.data
        )
        self.assertNotIn(
            movie_genres_serializer.data,
            filter_actors_response.data
        )
        self.assertNotIn(movie_serializer.data, filter_actors_response.data)

    def test_retrieve_movie(self):
        url = detail_url(self.movie_with_actors_genres.id)
        response = self.client.get(url)
        movie_serializer = MovieDetailSerializer(self.movie_with_actors_genres)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(movie_serializer.data, response.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Forbidden Title",
            "description": "Movie Description",
            "duration": 100,
        }
        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MovieAdminViewTest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="admin@movie.com",
            password="admin_T3st",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

        self.genre_1 = Genre.objects.create(name="Genre1")
        self.genre_2 = Genre.objects.create(name="Genre2")

        self.actor1 = Actor.objects.create(
            first_name="Test Actor",
            last_name="Test Actor Last"
        )
        self.actor2 = Actor.objects.create(
            first_name="Test Actor two",
            last_name="Test Actor Last"
        )

    def test_create_movie(self):
        payload = {
            "title": "Forbidden Title",
            "description": "Movie Description",
            "duration": 100,
        }
        payload_ = {
            "title": "Forbidden Title",
            "description": "Movie Description",
            "duration": 100,
            "genres": [self.genre_1.id, self.genre_2.id],
            "actors": [self.actor1.id, self.actor2.id],
        }
        response = self.client.post(MOVIE_URL, payload)
        response_ = self.client.post(MOVIE_URL, payload_)

        movie = Movie.objects.get(pk=response.data["id"])
        movie_ = Movie.objects.get(pk=response_.data["id"])
        genres = movie_.genres.all()
        actors = movie_.actors.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response_.status_code, status.HTTP_201_CREATED)

        for key, value in payload.items():
            self.assertEqual(getattr(movie, key), value)

        self.assertIn(self.genre_1, genres)
        self.assertIn(self.genre_2, genres)
        self.assertEqual(movie_.genres.count(), 2)

        self.assertIn(self.actor1, actors)
        self.assertIn(self.actor2, actors)
        self.assertEqual(movie_.actors.count(), 2)

    def test_delete_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        response = self.client.delete(url)
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_update_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        response = self.client.put(url, {
            "title": "Updated Title",
            "description": "Updated Description",
            "duration": 200,
        })
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_partial_update_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        response = self.client.put(url, {"title": "Updated Title"})
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class MovieImageUploadTest(APITestCase):

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="admin@movie.com",
            password="admin_T3st",
        )
        self.client.force_authenticate(user=self.user)
        self.movie = sample_movie()

    def test_upload_image(self):
        url = image_upload_url(movie_id=self.movie.id)
        image = Image.new("RGB", (100, 100))
        with tempfile.NamedTemporaryFile(
                suffix=".jpg", delete=False
        ) as tmp_file:
            image.save(tmp_file, format="JPEG")
            with open(tmp_file.name, "rb") as fp:
                response = self.client.post(
                    url, {"image": fp}, format="multipart"
                )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
