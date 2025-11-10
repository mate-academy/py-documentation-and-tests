import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.template.defaultfilters import title
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieSerializer, MovieListSerializer, MovieDetailSerializer

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


class UnauthenticatedMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()


    def test_movie_list(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_movie_detail(self):
        movie = sample_movie()
        res = self.client.get(reverse("cinema:movie-detail", args=[movie.id]))

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="test1234"
        )
        self.client = APIClient()
        self.client.force_authenticate(user)


    def test_movie_list(self):
        sample_movie()
        sample_movie(title="Test1")
        sample_movie(title="test2")

        serializer = MovieListSerializer(Movie.objects.all(), many=True)
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_detail(self):
        movie = sample_movie()
        serializer = MovieDetailSerializer(movie)
        res = self.client.get(reverse("cinema:movie-detail", args=[movie.id]))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_post_method(self):
        actor = sample_actor()
        genre = sample_genre()
        info = {
            "title": "Test",
            "description": "Test",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, info)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_movie_put_method(self):
        movie = sample_movie()
        actor = sample_actor()
        genre = sample_genre()
        info = {
            "title": "Test",
            "description": "Test",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        url = reverse("cinema:movie-detail", args=[movie.id])
        res = self.client.put(url, info)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_movie_delete_method(self):
        movie = sample_movie()

        url = reverse("cinema:movie-detail", args=[movie.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_movie_list_with_params(self):
        actor_1 = sample_actor()
        actor_2 = sample_actor(first_name="John", last_name="Doe")
        actor_3 = sample_actor(first_name="Tom", last_name="Crosoo")
        actor_4 = sample_actor(first_name="Robert", last_name="Downy Jn")

        genre_1 = sample_genre()
        genre_2 = sample_genre(name="Fiction")
        genre_3 = sample_genre(name="Horror")
        genre_4 = sample_genre(name="Comedy")

        movie_1 = sample_movie()
        movie_1.genres.add(genre_1)
        movie_1.actors.add(actor_1)
        movie_2 = sample_movie(title="It")
        movie_2.genres.add(genre_2)
        movie_2.actors.add(actor_2)
        movie_3 = sample_movie(title="Tomorrow war")
        movie_3.genres.add(genre_3)
        movie_3.actors.add(actor_3)
        movie_4 = sample_movie(title="Iron man")
        movie_4.genres.add(genre_4)
        movie_4.actors.add(actor_4)
        movie_5 = sample_movie(title="Iron Man 2")
        movie_5.genres.add(genre_4)
        movie_5.actors.add(actor_3)

        movies_1 = Movie.objects.filter(title__icontains="war")
        serializer_1 = MovieListSerializer(movies_1, many=True)

        res_1 = self.client.get(f"{MOVIE_URL}?title=war")
        self.assertEqual(res_1.data, serializer_1.data)

        movies_2 = Movie.objects.filter(genres__name=genre_2.name)
        serializer_2 = MovieListSerializer(movies_2, many=True)

        res_2 = self.client.get(f"{MOVIE_URL}?genres={genre_2.id}")
        self.assertEqual(res_2.data, serializer_2.data)

        movies_3 = Movie.objects.filter(actors__id=actor_3.id)
        serializer_3 = MovieListSerializer(movies_3, many=True)

        res_3 = self.client.get(f"{MOVIE_URL}?actors={actor_3.id}")
        self.assertEqual(res_3.data, serializer_3.data)

        movies_4 = Movie.objects.filter(Q(actors__id=actor_4.id)&Q(genres=genre_3.id))
        serializer_4 = MovieListSerializer(movies_4, many=True)

        res_4 = self.client.get(f"{MOVIE_URL}?actors={actor_4.id}&genres={genre_3.id}")
        self.assertEqual(res_4.data, serializer_4.data)

        movies_5 = Movie.objects.filter(Q(actors__id=actor_3.id) & Q(genres=genre_4.id))
        serializer_5 = MovieListSerializer(movies_5, many=True)

        res_5 = self.client.get(f"{MOVIE_URL}?actors={actor_3.id}&genres={genre_4.id}")
        self.assertEqual(res_5.data, serializer_5.data)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        sample_movie(title="Test1")
        sample_movie(title="test2")

        serializer = MovieListSerializer(Movie.objects.all(), many=True)
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_detail(self):
        movie = sample_movie()
        serializer = MovieDetailSerializer(movie)
        res = self.client.get(reverse("cinema:movie-detail", args=[movie.id]))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_post_method(self):
        actor = sample_actor()
        genre = sample_genre()
        info = {
            "title": "Test",
            "description": "Test",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, info)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_movie_put_method(self):
        movie = sample_movie()
        actor = sample_actor()
        genre = sample_genre()
        info = {
            "title": "Test",
            "description": "Test",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        url = reverse("cinema:movie-detail", args=[movie.id])
        res = self.client.put(url, info)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_movie_delete_method(self):
        movie = sample_movie()

        url = reverse("cinema:movie-detail", args=[movie.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

