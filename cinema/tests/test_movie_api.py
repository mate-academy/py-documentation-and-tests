import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import (APIClient,
                                 APITestCase)

from cinema.models import (Movie,
                           MovieSession,
                           CinemaHall,
                           Genre,
                           Actor)

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


class MovieViewSetAPITestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="example@example.com",
            password="test123",
        )
        self.admin = get_user_model().objects.create_user(
            email="admin@example.com",
            password="admin123",
            is_staff=True,
        )
        self.url = reverse("cinema:movie-list")
        self.client.force_authenticate(user=self.user)

    def test_authenticated_user_can_list_movies(self):
        movie = sample_movie()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [item["id"] for item in response.data],
            [movie.pk],
        )

    def test_authenticated_user_can_retrieve_movie(self):
        movie = sample_movie(title="matrix")
        url = reverse("cinema:movie-detail", kwargs={"pk": movie.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], movie.title)
        self.assertEqual(response.data["id"], movie.pk)

    def test_non_staff_user_cannot_create_movie(self):
        actor = sample_actor()
        genre = sample_genre()
        count_before = Movie.objects.count()

        response = self.client.post(
            self.url,
            {
                "title": "Matrix",
                "description": "example",
                "duration": 150,
                "genres": [genre.pk],
                "actors": [actor.pk],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(Movie.objects.count(), count_before)

    def test_staff_user_can_create_movie_with_relations(self):
        self.client.force_authenticate(user=self.admin)
        actor = sample_actor()
        genre = sample_genre()
        count_before = Movie.objects.count()

        response = self.client.post(
            self.url,
            {
                "title": "Matrix",
                "description": "example",
                "duration": 150,
                "genres": [genre.pk],
                "actors": [actor.pk],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )
        self.assertEqual(Movie.objects.count(), count_before + 1)
        self.assertEqual(response.data["genres"], [genre.pk])
        self.assertEqual(response.data["actors"], [actor.pk])

        movie = Movie.objects.get(pk=response.data["id"])
        self.assertEqual(movie.title, "Matrix")
        self.assertEqual(movie.description, "example")
        self.assertEqual(movie.duration, 150)
        self.assertCountEqual(movie.genres.all(), [genre])
        self.assertCountEqual(movie.actors.all(), [actor])

    def test_filter_movies_by_title_ignores_case(self):
        matrix = sample_movie(title="matrix")
        sample_movie(title="test1")
        sample_movie(title="test2")

        response = self.client.get(
            self.url,
            data={"title": "MATRIX"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [item["id"] for item in response.data],
            [matrix.pk],
        )

    def test_filter_movies_by_partial_title(self):
        sample_movie(title="matrix")
        first_movie = sample_movie(title="test1")
        second_movie = sample_movie(title="test2")

        response = self.client.get(
            self.url,
            data={"title": "tes"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [item["id"] for item in response.data],
            [first_movie.pk, second_movie.pk],
        )

    def test_filter_movies_by_genre(self):
        drama = sample_genre(name="drama")
        horror = sample_genre(name="horror")

        drama_movie = sample_movie(title="Drama movie")
        drama_movie.genres.add(drama)

        horror_movie = sample_movie(title="Horror movie")
        horror_movie.genres.add(horror)

        response = self.client.get(
            self.url,
            data={"genres": str(drama.pk)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [item["id"] for item in response.data],
            [drama_movie.pk],
        )

    def test_filter_movies_by_multiple_genres_returns_unique_matches(self):
        drama = sample_genre(name="drama")
        horror = sample_genre(name="horror")

        drama_movie = sample_movie(title="Drama movie")
        drama_movie.genres.add(drama)

        horror_movie = sample_movie(title="Horror movie")
        horror_movie.genres.add(horror)

        both_genres_movie = sample_movie(title="Drama and horror")
        both_genres_movie.genres.add(drama, horror)

        sample_movie(title="Unrelated movie")

        response = self.client.get(
            self.url,
            data={"genres": f"{drama.pk},{horror.pk}"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [item["id"] for item in response.data],
            [drama_movie.pk, horror_movie.pk, both_genres_movie.pk],
        )

    def test_filter_movies_by_actor(self):
        ryan = sample_actor(first_name="Ryan")
        olise = sample_actor(first_name="Olise")

        ryan_movie = sample_movie(title="Ryan movie")
        ryan_movie.actors.add(ryan)

        olise_movie = sample_movie(title="Olise movie")
        olise_movie.actors.add(olise)

        response = self.client.get(
            self.url,
            data={"actors": str(ryan.pk)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [item["id"] for item in response.data],
            [ryan_movie.pk],
        )

    def test_filter_movies_by_multiple_actors_returns_unique_matches(self):
        ryan = sample_actor(first_name="Ryan")
        olise = sample_actor(first_name="Olise")

        ryan_movie = sample_movie(title="Ryan movie")
        ryan_movie.actors.add(ryan)

        olise_movie = sample_movie(title="Olise movie")
        olise_movie.actors.add(olise)

        both_actors_movie = sample_movie(title="Ryan and Olise")
        both_actors_movie.actors.add(ryan, olise)

        sample_movie(title="Unrelated movie")

        response = self.client.get(
            self.url,
            data={"actors": f"{ryan.pk},{olise.pk}"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [item["id"] for item in response.data],
            [ryan_movie.pk, olise_movie.pk, both_actors_movie.pk],
        )

    def test_unauthenticated_user_cannot_list_movies(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_user_cannot_retrieve_movie(self):
        self.client.force_authenticate(user=None)
        movie = sample_movie(title="matrix")

        url = reverse("cinema:movie-detail", kwargs={"pk": movie.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_user_cannot_create_movie(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(self.url, data={"title": "matrix",
                                                    "description": "superb",
                                                    "duration": 50})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Movie.objects.count(), 0)

    def test_unauthenticated_user_cannot_upload_movie_image(self):
        self.client.force_authenticate(user=None)
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", kwargs={"pk": movie.pk})

        response = self.client.post(url, data={}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_staff_user_cannot_upload_movie_image(self):
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", kwargs={"pk": movie.pk})

        response = self.client.post(url, data={}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_movies_without_filters_returns_all_movies(self):
        for i in range(5):
            sample_movie(title=f"movie {i}")

        response = self.client.get(self.url, data={})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)

    def test_filter_movies_by_unmatched_title_returns_empty_list(self):
        for i in range(5):
            sample_movie(title=f"movie {i}")

        response = self.client.get(self.url, data={"title": "anime"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_filter_movies_combines_title_genres_and_actors(self):
        drama = sample_genre(name="Drama")
        horror = sample_genre(name="Horror")
        ryan = sample_actor(first_name="Ryan")
        keanu = sample_actor(first_name="Keanu")

        matching_movie = sample_movie(title="Matrix")
        matching_movie.genres.add(drama)
        matching_movie.actors.add(ryan)

        wrong_title = sample_movie(title="another movie")
        wrong_title.genres.add(drama)
        wrong_title.actors.add(ryan)

        wrong_genre = sample_movie(title="matrix Reloaded")
        wrong_genre.genres.add(horror)
        wrong_genre.actors.add(ryan)

        wrong_actor = sample_movie(title="Matrix Revolutions")
        wrong_actor.genres.add(drama)
        wrong_actor.actors.add(keanu)

        response = self.client.get(
            self.url,
            data={
                "title": "MATRIX",
                "genres": str(drama.pk),
                "actors": str(ryan.pk),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [movie["id"] for movie in response.data],
            [matching_movie.pk],
        )

    def test_filter_movies_by_nonexistent_genre_returns_empty_list(self):
        genre = sample_genre()
        movie = sample_movie()
        movie.genres.add(genre)
        missing_id = genre.pk + 1
        self.assertFalse(Genre.objects.filter(pk=missing_id).exists())

        response = self.client.get(
            self.url, data={"genres": str(missing_id)}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_create_movie_without_duration_returns_400(self):
        self.client.force_authenticate(user=self.admin)
        actor = sample_actor()
        genre = sample_genre()

        response = self.client.post(
            self.url,
            data={
                "title": "Matrix",
                "description": "Example description",
                "genres": [genre.pk],
                "actors": [actor.pk],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("duration", response.data)
        self.assertEqual(Movie.objects.count(), 0)

    def test_create_movie_with_non_numeric_duration_returns_400(self):
        self.client.force_authenticate(user=self.admin)
        actor = sample_actor()
        genre = sample_genre()

        response = self.client.post(
            self.url,
            data={
                "title": "Matrix",
                "description": "Example description",
                "duration": "abc",
                "genres": [genre.pk],
                "actors": [actor.pk],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("duration", response.data)
        self.assertEqual(Movie.objects.count(), 0)

    def test_create_movie_with_nonexistent_genre_returns_400(self):
        self.client.force_authenticate(user=self.admin)
        actor = sample_actor()
        genre = sample_genre()
        missing_id = genre.pk + 1
        self.assertFalse(Genre.objects.filter(pk=missing_id).exists())

        response = self.client.post(
            self.url,
            data={
                "title": "Matrix",
                "description": "Example description",
                "duration": 150,
                "genres": [missing_id],
                "actors": [actor.pk],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("genres", response.data)
        self.assertEqual(Movie.objects.count(), 0)

    def test_create_movie_with_nonexistent_actor_returns_400(self):
        self.client.force_authenticate(user=self.admin)
        actor = sample_actor()
        genre = sample_genre()
        missing_id = actor.pk + 1
        self.assertFalse(Actor.objects.filter(pk=missing_id).exists())

        response = self.client.post(
            self.url,
            data={
                "title": "Matrix",
                "description": "Example description",
                "duration": 150,
                "genres": [genre.pk],
                "actors": [missing_id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("actors", response.data)
        self.assertEqual(Movie.objects.count(), 0)

    def test_list_movies_returns_empty_list_when_database_is_empty(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_retrieve_nonexistent_movie_returns_404(self):
        url = reverse("cinema:movie-detail", kwargs={"pk": 99999})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_user_cannot_update_movie_with_put(self):
        self.client.force_authenticate(user=self.admin)
        movie = sample_movie()
        original_title = movie.title
        url = reverse("cinema:movie-detail", kwargs={"pk": movie.pk})

        response = self.client.put(url, data={"title": "matrix"})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        movie.refresh_from_db()
        self.assertEqual(movie.title, original_title)

    def test_staff_user_cannot_delete_movie(self):
        self.client.force_authenticate(user=self.admin)
        movie = sample_movie()
        url = reverse("cinema:movie-detail", kwargs={"pk": movie.pk})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Movie.objects.filter(pk=movie.pk).exists())

    def test_staff_user_cannot_update_movie_with_patch(self):
        self.client.force_authenticate(user=self.admin)
        movie = sample_movie()
        original_title = movie.title
        url = reverse("cinema:movie-detail", kwargs={"pk": movie.pk})

        response = self.client.patch(url, data={"title": "matrix"})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        movie.refresh_from_db()
        self.assertEqual(movie.title, original_title)
