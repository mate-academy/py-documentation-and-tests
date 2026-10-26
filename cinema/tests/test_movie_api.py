import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.cache import cache
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


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        cache.clear()  # reset throttling counters
        self.client = APIClient()
        self.movie = sample_movie()

    def test_list_requires_authentication(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_requires_authentication(self):
        res = self.client.get(detail_url(self.movie.id))

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_authentication(self):
        payload = {"title": "New", "description": "Desc", "duration": 100}
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Movie.objects.filter(title="New").exists())

    def test_upload_image_requires_authentication(self):
        res = self.client.post(image_upload_url(self.movie.id), {})

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        cache.clear()  # reset throttling counters
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie(title="B movie")
        sample_movie(title="A movie")

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.order_by("title")
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(
            [movie["title"] for movie in res.data], ["A movie", "B movie"]
        )

    def test_list_empty(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

    def test_list_shows_genre_names_and_actor_full_names(self):
        movie = sample_movie()
        movie.genres.add(sample_genre(name="Comedy"))
        movie.actors.add(sample_actor(first_name="Brad", last_name="Pitt"))

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.data[0]["genres"], ["Comedy"])
        self.assertEqual(res.data[0]["actors"], ["Brad Pitt"])

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="The Matrix")
        movie2 = sample_movie(title="Matrix Reloaded")
        movie3 = sample_movie(title="Titanic")

        res = self.client.get(MOVIE_URL, {"title": "matrix"})

        titles = [movie["title"] for movie in res.data]
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(movie1.title, titles)
        self.assertIn(movie2.title, titles)
        self.assertNotIn(movie3.title, titles)

    def test_filter_movies_by_title_no_match(self):
        sample_movie(title="Titanic")

        res = self.client.get(MOVIE_URL, {"title": "unknown"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

    def test_filter_movies_by_single_genre(self):
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Comedy")
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie3 = sample_movie(title="Movie 3")
        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        titles = [movie["title"] for movie in res.data]
        self.assertEqual(titles, [movie1.title])
        self.assertNotIn(movie2.title, titles)
        self.assertNotIn(movie3.title, titles)

    def test_filter_movies_by_multiple_genres(self):
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Comedy")
        genre3 = sample_genre(name="Horror")
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie3 = sample_movie(title="Movie 3")
        movie1.genres.add(genre1)
        movie2.genres.add(genre2)
        movie3.genres.add(genre3)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"}
        )

        titles = [movie["title"] for movie in res.data]
        self.assertEqual(titles, [movie1.title, movie2.title])

    def test_filter_movies_by_single_actor(self):
        actor1 = sample_actor(first_name="Brad", last_name="Pitt")
        actor2 = sample_actor(first_name="Tom", last_name="Hanks")
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        titles = [movie["title"] for movie in res.data]
        self.assertEqual(titles, [movie1.title])

    def test_filter_movies_by_multiple_actors(self):
        actor1 = sample_actor(first_name="Brad", last_name="Pitt")
        actor2 = sample_actor(first_name="Tom", last_name="Hanks")
        actor3 = sample_actor(first_name="Emma", last_name="Stone")
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie3 = sample_movie(title="Movie 3")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)
        movie3.actors.add(actor3)

        res = self.client.get(
            MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"}
        )

        titles = [movie["title"] for movie in res.data]
        self.assertEqual(titles, [movie1.title, movie2.title])

    def test_filter_does_not_return_duplicates(self):
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Comedy")
        movie = sample_movie()
        movie.genres.add(genre1, genre2)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"}
        )

        self.assertEqual(len(res.data), 1)

    def test_filter_by_title_genres_and_actors_combined(self):
        genre = sample_genre(name="Drama")
        actor = sample_actor()
        matching = sample_movie(title="Matching movie")
        wrong_title = sample_movie(title="Other")
        wrong_genre = sample_movie(title="Matching but no genre")
        for movie in (matching, wrong_title):
            movie.genres.add(genre)
            movie.actors.add(actor)
        wrong_genre.actors.add(actor)

        res = self.client.get(
            MOVIE_URL,
            {
                "title": "matching",
                "genres": f"{genre.id}",
                "actors": f"{actor.id}",
            },
        )

        titles = [movie["title"] for movie in res.data]
        self.assertEqual(titles, [matching.title])

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        res = self.client.get(detail_url(movie.id))

        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.data["genres"][0]["name"], "Drama")
        self.assertEqual(res.data["actors"][0]["full_name"], "George Clooney")

    def test_retrieve_nonexistent_movie_returns_404(self):
        res = self.client.get(detail_url(9999))

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_movie_forbidden_for_regular_user(self):
        payload = {"title": "New", "description": "Desc", "duration": 100}

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title="New").exists())

    def test_upload_image_forbidden_for_regular_user(self):
        movie = sample_movie()

        res = self.client.post(image_upload_url(movie.id), {})

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        cache.clear()  # reset throttling counters
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "New movie",
            "description": "New description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])
        self.assertEqual(list(movie.genres.all()), [genre])
        self.assertEqual(list(movie.actors.all()), [actor])

    def test_create_movie_without_genres_and_actors_is_invalid(self):
        payload = {"title": "New", "description": "Desc", "duration": 100}

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("genres", res.data)
        self.assertIn("actors", res.data)
        self.assertFalse(Movie.objects.filter(title="New").exists())

    def test_create_movie_missing_required_fields(self):
        res = self.client.post(MOVIE_URL, {})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        for field in ("title", "description", "duration"):
            self.assertIn(field, res.data)
        self.assertEqual(Movie.objects.count(), 0)

    def test_create_movie_with_invalid_duration(self):
        payload = {
            "title": "New",
            "description": "Desc",
            "duration": "long",
            "genres": [sample_genre().id],
            "actors": [sample_actor().id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("duration", res.data)

    def test_create_movie_with_nonexistent_genre(self):
        payload = {
            "title": "New",
            "description": "Desc",
            "duration": 100,
            "genres": [9999],
            "actors": [sample_actor().id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("genres", res.data)

    def test_admin_can_list_and_retrieve(self):
        movie = sample_movie()

        list_res = self.client.get(MOVIE_URL)
        detail_res = self.client.get(detail_url(movie.id))

        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)

    def test_upload_image_to_nonexistent_movie_returns_404(self):
        res = self.client.post(image_upload_url(9999), {})

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_patch_delete_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        for method in (self.client.put, self.client.patch, self.client.delete):
            res = method(url, {"title": "Changed"})
            self.assertEqual(
                res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
            )

        movie.refresh_from_db()
        self.assertEqual(movie.title, "Sample movie")
