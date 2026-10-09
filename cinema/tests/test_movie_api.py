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


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, res.status_code)


class TestMovieApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="passwordtest",
        )
        self.client.force_authenticate(user=self.user)

    def test_movie_list(self):
        movie = sample_movie()
        genre = sample_genre()
        actor = sample_actor()
        movie.actors.add(actor)
        movie.genres.add(genre)
        all_movies = Movie.objects.all()
        serializer = MovieListSerializer(all_movies, many=True)
        res = self.client.get(MOVIE_URL)

        self.assertEqual(status.HTTP_200_OK, res.status_code)
        self.assertEqual(serializer.data, res.data)

    def test_filter_movie_list_by_title(self):
        movie_1 = sample_movie(title="Unbreakable")
        movie_2 = sample_movie(title="Looper")
        actor = sample_actor()
        genre = sample_genre()

        for movie in (movie_1, movie_2):
            movie.actors.add(actor)
            movie.genres.add(genre)

        all_movies = Movie.objects.all().filter(title__icontains="looper")
        serializer = MovieListSerializer(all_movies, many=True)
        res = self.client.get(MOVIE_URL, {"title": "looper"})

        self.assertEqual(status.HTTP_200_OK, res.status_code)
        self.assertEqual(serializer.data, res.data)
        self.assertNotIn(MovieListSerializer(movie_1, many=False), res.data)

    def test_filter_movie_list_by_genres(self):
        movie_1 = sample_movie(title="Unbreakable")
        movie_2 = sample_movie(title="Looper")
        actor = sample_actor()
        drama = sample_genre()
        thriller = sample_genre(name="Thriller")
        action = sample_genre(name="Action")

        for movie in (movie_1, movie_2):
            if movie is movie_1:
                movie.genres.add(drama, action)
            if movie is movie_2:
                movie.genres.add(thriller)
            movie.actors.add(actor)

        all_movies = Movie.objects.all().filter(genres__id__in=[drama.pk, action.pk]).distinct()
        serializer = MovieListSerializer(all_movies, many=True)
        res = self.client.get(MOVIE_URL, {"genres": f"{drama.pk},{action.pk}"})

        self.assertEqual(status.HTTP_200_OK, res.status_code)
        self.assertEqual(serializer.data, res.data)
        self.assertNotIn(MovieListSerializer(movie_2, many=False), res.data)

    def test_filter_movie_list_by_actors(self):
        movie_1 = sample_movie(title="Unbreakable")
        movie_2 = sample_movie(title="Looper")
        movie_3 = sample_movie(title="test")
        genre = sample_genre()
        actor_1 = sample_actor()
        actor_2 = sample_actor()
        actor_3 = sample_actor()
        actor_4 = sample_actor()

        for movie in (movie_1, movie_2):
            if movie is movie_1:
                movie.actors.add(actor_1, actor_2)
                movie_3.actors.add(actor_1, actor_4)
            if movie is movie_2:
                movie.actors.add(actor_4, actor_3)
            movie.genres.add(genre)

        all_movies = Movie.objects.all().filter(actors__id__in=[actor_1.pk, actor_2.pk]).distinct()
        serializer = MovieListSerializer(all_movies, many=True)
        res = self.client.get(MOVIE_URL, {"actors": f"{actor_1.pk},{actor_2.pk}"})

        self.assertEqual(status.HTTP_200_OK, res.status_code)
        self.assertEqual(serializer.data, res.data)
        self.assertNotIn(MovieListSerializer(movie_2, many=False), res.data)

    def test_movie_detail(self):
        movie = sample_movie(title="Unbreakable")
        genre = sample_genre()
        actor = sample_actor()
        movie.actors.add(actor)
        movie.genres.add(genre)

        serializer = MovieDetailSerializer(movie, many=False)
        res = self.client.get(reverse("cinema:movie-detail", kwargs={"pk": movie.pk}))

        self.assertEqual(status.HTTP_200_OK, res.status_code)
        self.assertEqual(serializer.data, res.data)


class PermissionMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_user(
            email="admim@example.com",
            password="passwordtest",
            is_staff=True,
        )
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="passwordtest",
        )
        self.actor = sample_actor()
        self.genre = sample_genre()
        self.payload = {
            "title": "string",
            "description": "string",
            "duration": 90,
            "genres": [self.genre.pk],
            "actors": [self.actor.pk]
        }

    def test_not_allowed_to_create_movie_for_user(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.post(MOVIE_URL, self.payload)

        self.assertEqual(status.HTTP_403_FORBIDDEN, res.status_code)
        self.assertEqual(0, Movie.objects.count())

    def test_allowed_to_create_movie_for_admin(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(MOVIE_URL, self.payload)
        movie = Movie.objects.get(pk=res.data["id"])
        serializer = MovieSerializer(movie, many=False)

        self.assertEqual(status.HTTP_201_CREATED, res.status_code)
        self.assertEqual(serializer.data, res.data)

    def test_required_actors(self):
        self.client.force_authenticate(user=self.admin)
        self.payload.pop("actors")
        res = self.client.post(MOVIE_URL, self.payload)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, res.status_code)

    def test_required_genres(self):
        self.client.force_authenticate(user=self.admin)
        self.payload.pop("genres")
        res = self.client.post(MOVIE_URL, self.payload)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, res.status_code)

    def test_not_allowed_to_mutate_movie(self):
        self.client.force_authenticate(user=self.admin)
        movie = sample_movie()
        url = reverse("cinema:movie-detail", kwargs={"pk": movie.pk})
        res_put = self.client.put(url, self.payload)
        res_patch = self.client.patch(url, {"title": "string"})

        self.assertEqual(status.HTTP_405_METHOD_NOT_ALLOWED, res_put.status_code)
        self.assertEqual(status.HTTP_405_METHOD_NOT_ALLOWED, res_patch.status_code)

    def test_not_allowed_to_delete_movie(self):
        self.client.force_authenticate(user=self.admin)
        movie = sample_movie()
        url = reverse("cinema:movie-detail", kwargs={"pk": movie.pk})
        res = self.client.delete(url)

        self.assertEqual(status.HTTP_405_METHOD_NOT_ALLOWED, res.status_code)

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
