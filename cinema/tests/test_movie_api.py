import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
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


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
    
    def test_movie_list_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_movie_detail_auth_required(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_movie_create_auth_required(self):
        payload = {
            "title": "New Movie",
            "description": "New movie description",
            "duration": 120,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="testpass"   
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        movie_with_genre = sample_movie()
        movie_with_actor = sample_movie()

        movie_with_genre.genres.add(sample_genre())
        movie_with_actor.actors.add(sample_actor())

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres(self):
        movie_1 = sample_movie(title="Movie 1")
        movie_2 = sample_movie(title="Movie 2")
        genre_1 = sample_genre(name="Action")
        genre_2 = sample_genre(name="Comedy")
        movie_1.genres.add(genre_1)
        movie_2.genres.add(genre_2)
        movie_3 = sample_movie(title="Movie 3")

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"},
        )

        serializer1 = MovieListSerializer(movie_1)
        serializer2 = MovieListSerializer(movie_2)
        serializer3 = MovieListSerializer(movie_3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_movies_by_actors(self):
        movie_1 = sample_movie(title="Movie 1")
        movie_2 = sample_movie(title="Movie 2")
        actor_1 = sample_actor(first_name="Robert", last_name="Downey Jr.")
        actor_2 = sample_actor(first_name="Scarlett", last_name="Johansson")
        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_2)
        movie_3 = sample_movie(title="Movie 3")

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"},
        )

        serializer1 = MovieListSerializer(movie_1)
        serializer2 = MovieListSerializer(movie_2)
        serializer3 = MovieListSerializer(movie_3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_movies_by_title(self):
        movie_1 = sample_movie(title="The Great Adventure")
        movie_2 = sample_movie(title="Romantic Comedy")
        movie_3 = sample_movie(title="Adventure in the Mountains")

        res = self.client.get(MOVIE_URL, {"title": "Adventure"})

        serializer1 = MovieListSerializer(movie_1)
        serializer3 = MovieListSerializer(movie_3)
        serializer2 = MovieListSerializer(movie_2)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer3.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "New Movie",
            "description": "New movie description",
            "duration": 120,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image_to_movie_forbidden(self):
        movie = sample_movie()
        url = image_upload_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)



class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@test.test", password="adminpass"
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_successful(self):
        genre1 = sample_genre(name="Horror")
        genre2 = sample_genre(name="Thriller")
        actor1 = sample_actor(first_name="Brad", last_name="Pitt")
        actor2 = sample_actor(first_name="Angelina", last_name="Jolie")
        payload = {
            "title": "Admin Movie",
            "description": "Admin movie description",
            "duration": 110,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        for key in payload:
            if key in ["genres", "actors"]:
                self.assertEqual(
                    set(getattr(movie, key).values_list("id", flat=True)),
                    set(payload[key]),
                )
            else:
                self.assertEqual(payload[key], getattr(movie, key))

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)
        payload = {"title": "Updated Title"}
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_partial_update_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)
        payload = {"title": "Partially Updated Title"}
        res = self.client.patch(url, payload)

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
