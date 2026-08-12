import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Actor, CinemaHall, Genre, Movie, MovieSession


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
    defaults = {
        "first_name": "George",
        "last_name": "Clooney",
    }
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue",
        rows=20,
        seats_in_row=20,
    )

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    return reverse(
        "cinema:movie-upload-image",
        args=[movie_id],
    )


def detail_url(movie_id):
    return reverse(
        "cinema:movie-detail",
        args=[movie_id],
    )


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com",
            "password",
        )
        self.client.force_authenticate(self.user)

        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(
            movie=self.movie,
        )

    def tearDown(self):
        if self.movie.image and getattr(self.movie.image, "name", None):
            self.movie.image.delete(save=False)

    def test_upload_image_to_movie(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)

            res = self.client.post(
                url,
                {"image": ntf},
                format="multipart",
            )

        self.movie.refresh_from_db()

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn("image", res.data)
        self.assertTrue(
            os.path.exists(self.movie.image.path),
        )

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.movie.id)

        res = self.client.post(
            url,
            {"image": "not image"},
            format="multipart",
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_post_image_to_movie_list(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)

            res = self.client.post(
                MOVIE_URL,
                {
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [self.genre.id],
                    "actors": [self.actor.id],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(
            res.status_code,
            status.HTTP_201_CREATED,
        )

        movie = Movie.objects.get(title="Title")

        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)

            self.client.post(
                url,
                {"image": ntf},
                format="multipart",
            )

        res = self.client.get(
            detail_url(self.movie.id),
        )

        self.assertIn(
            "image",
            res.data,
        )

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)

            self.client.post(
                url,
                {"image": ntf},
                format="multipart",
            )

        res = self.client.get(MOVIE_URL)

        self.assertIn(
            "image",
            res.data[0],
        )

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)

            self.client.post(
                url,
                {"image": ntf},
                format="multipart",
            )

        res = self.client.get(
            MOVIE_SESSION_URL,
        )

        self.assertIn(
            "movie_image",
            res.data[0],
        )


class PublicMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertIn(
            res.status_code,
            (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ),
        )


class PrivateMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = get_user_model().objects.create_superuser(
            "admin@cinema.com",
            "password",
        )

        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie(title="Movie 1")
        sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL)

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            len(res.data),
            2,
        )

        titles = [movie["title"] for movie in res.data]

        self.assertIn("Movie 1", titles)
        self.assertIn("Movie 2", titles)

    def test_retrieve_movie(self):
        genre = sample_genre()
        actor = sample_actor()

        movie = sample_movie(
            title="Movie 1",
            description="Description 1",
            duration=120,
        )

        movie.genres.add(genre)
        movie.actors.add(actor)

        res = self.client.get(
            detail_url(movie.id),
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            res.data["title"],
            movie.title,
        )
        self.assertEqual(
            res.data["description"],
            movie.description,
        )
        self.assertEqual(
            res.data["duration"],
            movie.duration,
        )

        self.assertEqual(
            res.data["genres"][0]["name"],
            genre.name,
        )

        self.assertEqual(
            res.data["actors"][0]["first_name"],
            actor.first_name,
        )

        self.assertEqual(
            res.data["actors"][0]["last_name"],
            actor.last_name,
        )

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()

        payload = {
            "title": "New movie",
            "description": "New movie description",
            "duration": 110,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(
            MOVIE_URL,
            payload,
            format="json",
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_201_CREATED,
        )

        movie = Movie.objects.get(
            id=res.data["id"],
        )

        self.assertEqual(
            movie.title,
            payload["title"],
        )
        self.assertEqual(
            movie.description,
            payload["description"],
        )
        self.assertEqual(
            movie.duration,
            payload["duration"],
        )

        self.assertIn(
            genre,
            movie.genres.all(),
        )
        self.assertIn(
            actor,
            movie.actors.all(),
        )


    def test_filter_movies_by_title(self):
        movie_1 = sample_movie(
            title="Spider-Man",
        )
        movie_2 = sample_movie(
            title="Batman",
        )

        res = self.client.get(
            MOVIE_URL,
            {"title": "spider"},
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            len(res.data),
            1,
        )

        self.assertEqual(
            res.data[0]["id"],
            movie_1.id,
        )
        self.assertNotEqual(
            res.data[0]["id"],
            movie_2.id,
        )

    def test_filter_movies_by_genres(self):
        drama = sample_genre(
            name="Drama",
        )
        comedy = sample_genre(
            name="Comedy",
        )

        drama_movie = sample_movie(
            title="Drama movie",
        )
        comedy_movie = sample_movie(
            title="Comedy movie",
        )

        drama_movie.genres.add(drama)
        comedy_movie.genres.add(comedy)

        res = self.client.get(
            MOVIE_URL,
            {"genres": drama.id},
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            len(res.data),
            1,
        )

        self.assertEqual(
            res.data[0]["id"],
            drama_movie.id,
        )

    def test_filter_movies_by_multiple_genres(self):
        drama = sample_genre(
            name="Drama",
        )
        comedy = sample_genre(
            name="Comedy",
        )
        action = sample_genre(
            name="Action",
        )

        drama_movie = sample_movie(
            title="Drama movie",
        )
        comedy_movie = sample_movie(
            title="Comedy movie",
        )
        action_movie = sample_movie(
            title="Action movie",
        )

        drama_movie.genres.add(drama)
        comedy_movie.genres.add(comedy)
        action_movie.genres.add(action)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{drama.id},{comedy.id}"},
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )

        movie_ids = {
            movie["id"]
            for movie in res.data
        }

        self.assertIn(
            drama_movie.id,
            movie_ids,
        )
        self.assertIn(
            comedy_movie.id,
            movie_ids,
        )
        self.assertNotIn(
            action_movie.id,
            movie_ids,
        )

    def test_filter_movies_by_actors(self):
        clooney = sample_actor(
            first_name="George",
            last_name="Clooney",
        )
        dicaprio = sample_actor(
            first_name="Leonardo",
            last_name="DiCaprio",
        )

        clooney_movie = sample_movie(
            title="Clooney movie",
        )
        dicaprio_movie = sample_movie(
            title="DiCaprio movie",
        )

        clooney_movie.actors.add(clooney)
        dicaprio_movie.actors.add(dicaprio)

        res = self.client.get(
            MOVIE_URL,
            {"actors": clooney.id},
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            len(res.data),
            1,
        )

        self.assertEqual(
            res.data[0]["id"],
            clooney_movie.id,
        )

    def test_filter_movies_by_multiple_actors(self):
        actor_1 = sample_actor(
            first_name="George",
            last_name="Clooney",
        )
        actor_2 = sample_actor(
            first_name="Leonardo",
            last_name="DiCaprio",
        )
        actor_3 = sample_actor(
            first_name="Tom",
            last_name="Hanks",
        )

        movie_1 = sample_movie(
            title="Movie 1",
        )
        movie_2 = sample_movie(
            title="Movie 2",
        )
        movie_3 = sample_movie(
            title="Movie 3",
        )

        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_2)
        movie_3.actors.add(actor_3)

        res = self.client.get(
            MOVIE_URL,
            {
                "actors": f"{actor_1.id},{actor_2.id}",
            },
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )

        movie_ids = {
            movie["id"]
            for movie in res.data
        }

        self.assertIn(
            movie_1.id,
            movie_ids,
        )
        self.assertIn(
            movie_2.id,
            movie_ids
        )
        self.assertNotIn(
            movie_3.id,
            movie_ids,
        )

    def test_list_movie_contains_expected_fields(self):
        movie = sample_movie()

        res = self.client.get(MOVIE_URL)

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )

        movie_data = next(
            item
            for item in res.data
            if item["id"] == movie.id
        )

        expected_fields = {
            "id",
            "title",
            "description",
            "duration",
            "genres",
            "actors",
            "image",
        }

        self.assertEqual(
            set(movie_data.keys()),
            expected_fields,
        )

    def test_detail_movie_contains_expected_fields(self):
        movie = sample_movie()

        res = self.client.get(
            detail_url(movie.id),
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )

        expected_fields = {
            "id",
            "title",
            "description",
            "duration",
            "genres",
            "actors",
            "image",
        }

        self.assertEqual(
            set(res.data.keys()),
            expected_fields,
        )

    def test_movie_list_returns_movies_in_title_order(self):
        movie_b = sample_movie(
            title="B movie",
        )
        movie_a = sample_movie(
            title="A movie",
        )

        res = self.client.get(MOVIE_URL)

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )

        movie_ids = [
            movie["id"]
            for movie in res.data
        ]

        self.assertLess(
            movie_ids.index(movie_a.id),
            movie_ids.index(movie_b.id),
        )
