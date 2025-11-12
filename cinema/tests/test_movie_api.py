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


class MovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@test.com",
            password="testpass123",
        )

    def test_list_movies_unauthenticated(self):
        """Test that unauthenticated users cannot list movies"""
        sample_movie(title="Movie 1")
        sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_movies_authenticated(self):
        """Test that authenticated users can list movies"""
        self.client.force_authenticate(self.user)
        sample_movie(title="Movie 1")
        sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_list_movies_with_genres_and_actors(self):
        """Test listing movies returns genres and actors as names"""
        self.client.force_authenticate(self.user)

        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Drama")
        actor1 = sample_actor(first_name="Tom", last_name="Hanks")
        actor2 = sample_actor(first_name="Brad", last_name="Pitt")

        movie = sample_movie(title="Test Movie")
        movie.genres.add(genre1, genre2)
        movie.actors.add(actor1, actor2)

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("genres", res.data[0])
        self.assertIn("actors", res.data[0])
        self.assertEqual(len(res.data[0]["genres"]), 2)
        self.assertEqual(len(res.data[0]["actors"]), 2)
        self.assertIn("Action", res.data[0]["genres"])
        self.assertIn("Tom Hanks", res.data[0]["actors"])

    def test_filter_movies_by_title(self):
        """Test filtering movies by title"""
        self.client.force_authenticate(self.user)
        sample_movie(title="The Matrix")
        sample_movie(title="The Godfather")
        sample_movie(title="Inception")

        res = self.client.get(MOVIE_URL, {"title": "the"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        titles = [movie["title"] for movie in res.data]
        self.assertIn("The Matrix", titles)
        self.assertIn("The Godfather", titles)
        self.assertNotIn("Inception", titles)

    def test_filter_movies_by_title_case_insensitive(self):
        """Test that title filtering is case insensitive"""
        self.client.force_authenticate(self.user)
        sample_movie(title="The Matrix")
        sample_movie(title="Inception")

        res = self.client.get(MOVIE_URL, {"title": "MATRIX"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "The Matrix")

    def test_filter_movies_by_genre(self):
        """Test filtering movies by a single genre"""
        self.client.force_authenticate(self.user)
        genre_action = sample_genre(name="Action")
        genre_drama = sample_genre(name="Drama")

        movie1 = sample_movie(title="Action Movie")
        movie1.genres.add(genre_action)

        movie2 = sample_movie(title="Drama Movie")
        movie2.genres.add(genre_drama)

        movie3 = sample_movie(title="Mixed Movie")
        movie3.genres.add(genre_action, genre_drama)

        res = self.client.get(MOVIE_URL, {"genres": str(genre_action.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        titles = [movie["title"] for movie in res.data]
        self.assertIn("Action Movie", titles)
        self.assertIn("Mixed Movie", titles)
        self.assertNotIn("Drama Movie", titles)

    def test_filter_movies_by_multiple_genres(self):
        """Test filtering movies by multiple genres"""
        self.client.force_authenticate(self.user)
        genre_action = sample_genre(name="Action")
        genre_drama = sample_genre(name="Drama")
        genre_comedy = sample_genre(name="Comedy")

        movie1 = sample_movie(title="Action Movie")
        movie1.genres.add(genre_action)

        movie2 = sample_movie(title="Drama Movie")
        movie2.genres.add(genre_drama)

        movie3 = sample_movie(title="Comedy Movie")
        movie3.genres.add(genre_comedy)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_action.id},{genre_drama.id}"}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        titles = [movie["title"] for movie in res.data]
        self.assertIn("Action Movie", titles)
        self.assertIn("Drama Movie", titles)
        self.assertNotIn("Comedy Movie", titles)

    def test_filter_movies_by_actor(self):
        """Test filtering movies by a single actor"""
        self.client.force_authenticate(self.user)
        actor1 = sample_actor(first_name="Tom", last_name="Hanks")
        actor2 = sample_actor(first_name="Brad", last_name="Pitt")

        movie1 = sample_movie(title="Movie with Tom")
        movie1.actors.add(actor1)

        movie2 = sample_movie(title="Movie with Brad")
        movie2.actors.add(actor2)

        movie3 = sample_movie(title="Movie with Both")
        movie3.actors.add(actor1, actor2)

        res = self.client.get(MOVIE_URL, {"actors": str(actor1.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        titles = [movie["title"] for movie in res.data]
        self.assertIn("Movie with Tom", titles)
        self.assertIn("Movie with Both", titles)
        self.assertNotIn("Movie with Brad", titles)

    def test_filter_movies_by_multiple_actors(self):
        """Test filtering movies by multiple actors"""
        self.client.force_authenticate(self.user)
        actor1 = sample_actor(first_name="Tom", last_name="Hanks")
        actor2 = sample_actor(first_name="Brad", last_name="Pitt")
        actor3 = sample_actor(first_name="Leonardo", last_name="DiCaprio")

        movie1 = sample_movie(title="Movie with Tom")
        movie1.actors.add(actor1)

        movie2 = sample_movie(title="Movie with Brad")
        movie2.actors.add(actor2)

        movie3 = sample_movie(title="Movie with Leo")
        movie3.actors.add(actor3)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor1.id},{actor2.id}"}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        titles = [movie["title"] for movie in res.data]
        self.assertIn("Movie with Tom", titles)
        self.assertIn("Movie with Brad", titles)
        self.assertNotIn("Movie with Leo", titles)

    def test_filter_movies_by_title_and_genres_and_actors(self):
        """Test filtering movies by combination of title, genres and actors"""
        self.client.force_authenticate(self.user)
        genre_action = sample_genre(name="Action")
        actor1 = sample_actor(first_name="Tom", last_name="Cruise")

        movie1 = sample_movie(title="Mission Impossible")
        movie1.genres.add(genre_action)
        movie1.actors.add(actor1)

        movie2 = sample_movie(title="Mission Impossible 2")
        movie2.genres.add(genre_action)

        movie3 = sample_movie(title="Top Gun")
        movie3.actors.add(actor1)

        res = self.client.get(
            MOVIE_URL,
            {
                "title": "mission",
                "genres": str(genre_action.id),
                "actors": str(actor1.id)
            }
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Mission Impossible")

    def test_retrieve_movie_detail_unauthenticated(self):
        """Test retrieving movie detail as unauthenticated user"""
        movie = sample_movie(title="Test Movie")

        url = detail_url(movie.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_movie_detail_authenticated(self):
        """Test retrieving movie detail as authenticated user"""
        self.client.force_authenticate(self.user)

        genre = sample_genre(name="Action")
        actor = sample_actor(first_name="Tom", last_name="Hanks")

        movie = sample_movie(title="Test Movie")
        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_url(movie.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], movie.title)
        self.assertIn("genres", res.data)
        self.assertIn("actors", res.data)
        self.assertEqual(len(res.data["genres"]), 1)
        self.assertEqual(res.data["genres"][0]["name"], "Action")
        self.assertEqual(len(res.data["actors"]), 1)
        self.assertEqual(res.data["actors"][0]["first_name"], "Tom")

    def test_retrieve_nonexistent_movie(self):
        """Test retrieving a nonexistent movie returns 404"""
        self.client.force_authenticate(self.user)
        url = detail_url(999)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_movie_as_admin(self):
        """Test that admin can create a movie"""
        self.client.force_authenticate(self.admin_user)

        genre = sample_genre(name="Action")
        actor = sample_actor(first_name="Tom", last_name="Hanks")

        payload = {
            "title": "New Movie",
            "description": "New movie description",
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
        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_create_movie_as_regular_user(self):
        """Test that regular authenticated user cannot create a movie"""
        self.client.force_authenticate(self.user)

        payload = {
            "title": "New Movie",
            "description": "New movie description",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movie_unauthenticated(self):
        """Test that unauthenticated user cannot create a movie"""
        payload = {
            "title": "New Movie",
            "description": "New movie description",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_with_invalid_data(self):
        """Test creating a movie with invalid data"""
        self.client.force_authenticate(self.admin_user)

        payload = {
            "title": "",
            "description": "Description",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_movie_missing_required_fields(self):
        """Test creating a movie without required fields"""
        self.client.force_authenticate(self.admin_user)

        payload = {
            "title": "New Movie",
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_movie_not_allowed(self):
        """Test that PUT method is not allowed for movies"""
        self.client.force_authenticate(self.admin_user)
        movie = sample_movie()

        url = detail_url(movie.id)
        payload = {"title": "Updated Title"}

        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_partial_update_movie_not_allowed(self):
        """Test that PATCH method is not allowed for movies"""
        self.client.force_authenticate(self.admin_user)
        movie = sample_movie()

        url = detail_url(movie.id)
        payload = {"title": "Updated Title"}

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_movie_not_allowed(self):
        """Test that DELETE method is not allowed for movies"""
        self.client.force_authenticate(self.admin_user)
        movie = sample_movie()

        url = detail_url(movie.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
