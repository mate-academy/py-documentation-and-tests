import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

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
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieListTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com",
            "password",
        )

        self.client.force_authenticate(user=self.user)

        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()

    def test_get_movies(self):
        sample_movie(title="Movie 2")
        sample_movie(title="Movie 3")

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)

    def test_filter_movies_by_title(self):
        movie = sample_movie(title="Avengers")
        sample_movie(title="Batman")

        res = self.client.get(
            MOVIE_URL,
            {"title": "aveng"},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], movie.id)

    def test_filter_movies_by_genre(self):
        comedy = sample_genre(name="Comedy")

        drama_movie = sample_movie(title="Drama movie")
        comedy_movie = sample_movie(title="Comedy movie")

        drama_movie.genres.add(self.genre)
        comedy_movie.genres.add(comedy)

        res = self.client.get(
            MOVIE_URL,
            {"genres": self.genre.id},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(
            res.data[0]["id"],
            drama_movie.id,
        )

    def test_filter_movies_by_multiple_genres(self):
        comedy = sample_genre(name="Comedy")

        drama_movie = sample_movie(title="Drama movie")
        comedy_movie = sample_movie(title="Comedy movie")
        both_movie = sample_movie(title="Drama and comedy")

        drama_movie.genres.add(self.genre)
        comedy_movie.genres.add(comedy)
        both_movie.genres.add(self.genre, comedy)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{self.genre.id},{comedy.id}"},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)

    def test_filter_movies_by_actor(self):
        actor_1 = sample_actor(
            first_name="George",
            last_name="Clooney",
        )
        actor_2 = sample_actor(
            first_name="Brad",
            last_name="Pitt",
        )

        movie_1 = sample_movie(title="Movie 1")
        movie_2 = sample_movie(title="Movie 2")

        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": actor_1.id},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], movie_1.id)

    def test_filter_movies_by_multiple_actors(self):
        actor_1 = sample_actor(
            first_name="George",
            last_name="Clooney",
        )
        actor_2 = sample_actor(
            first_name="Brad",
            last_name="Pitt",
        )

        movie_1 = sample_movie(title="Movie 1")
        movie_2 = sample_movie(title="Movie 2")

        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_filter_movies_by_title_genre_and_actor(self):
        actor = sample_actor(
            first_name="Brad",
            last_name="Pitt",
        )

        matching_movie = sample_movie(title="Avengers")
        wrong_title_movie = sample_movie(title="Batman")
        wrong_actor_movie = sample_movie(title="Avengers 2")

        matching_movie.genres.add(self.genre)
        matching_movie.actors.add(self.actor)

        wrong_title_movie.genres.add(self.genre)
        wrong_title_movie.actors.add(self.actor)

        wrong_actor_movie.genres.add(self.genre)
        wrong_actor_movie.actors.add(actor)

        res = self.client.get(
            MOVIE_URL,
            {
                "title": "Avengers",
                "genres": self.genre.id,
                "actors": self.actor.id,
            },
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(
            res.data[0]["id"],
            matching_movie.id,
        )

    def test_authenticated_user_can_list_movies(self):
        user = get_user_model().objects.create_user(
            "user@example.com",
            "password",
        )
        self.client.force_authenticate(user=user)

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)


class MovieCreateTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.admin = get_user_model().objects.create_superuser(
            "admin@myproject.com",
            "password",
        )

        self.client.force_authenticate(user=self.admin)

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

        res = self.client.post(
            MOVIE_URL,
            payload,
            format="json",
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_201_CREATED,
        )

        movie = Movie.objects.get(title="New movie")

        self.assertEqual(movie.description, "New description")
        self.assertEqual(movie.duration, 120)
        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_authenticated_non_admin_cannot_create_movie(self):
        user = get_user_model().objects.create_user(
            "user@example.com",
            "password",
        )
        self.client.force_authenticate(user=user)

        payload = {
            "title": "New movie",
            "description": "Description",
            "duration": 120,
        }

        res = self.client.post(
            MOVIE_URL,
            payload,
            format="json",
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_403_FORBIDDEN,
        )


class MovieDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = get_user_model().objects.create_user(
            "user@example.com",
            "password",
        )

        self.client.force_authenticate(user=self.user)

        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()

        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_get_movie_detail(self):
        url = detail_url(self.movie.id)

        res = self.client.get(url)

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            res.data["id"],
            self.movie.id,
        )
        self.assertEqual(
            res.data["title"],
            self.movie.title,
        )

    def test_movie_detail_contains_genres(self):
        url = detail_url(self.movie.id)

        res = self.client.get(url)

        self.assertIn("genres", res.data)
        self.assertEqual(len(res.data["genres"]), 1)
        self.assertEqual(
            res.data["genres"][0]["name"],
            self.genre.name,
        )

    def test_movie_detail_contains_actors(self):
        url = detail_url(self.movie.id)

        res = self.client.get(url)

        self.assertIn("actors", res.data)
        self.assertEqual(len(res.data["actors"]), 1)
        self.assertEqual(
            res.data["actors"][0]["full_name"],
            self.actor.full_name,
        )

    def test_movie_not_found(self):
        url = detail_url(999999)

        res = self.client.get(url)

        self.assertEqual(
            res.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com",
            "password",
        )

        self.client.force_authenticate(user=self.user)

        self.movie = sample_movie()

    def tearDown(self):
        self.movie.refresh_from_db()

        if self.movie.image:
            self.movie.image.delete()

    def test_upload_image_to_movie(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            image = Image.new("RGB", (10, 10))
            image.save(ntf, format="JPEG")
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
        self.assertTrue(self.movie.image)

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

    def test_upload_image_to_nonexistent_movie(self):
        url = image_upload_url(999999)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            image = Image.new("RGB", (10, 10))
            image.save(ntf, format="JPEG")
            ntf.seek(0)

            res = self.client.post(
                url,
                {"image": ntf},
                format="multipart",
            )

        self.assertEqual(
            res.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            image = Image.new("RGB", (10, 10))
            image.save(ntf, format="JPEG")
            ntf.seek(0)

            self.client.post(
                url,
                {"image": ntf},
                format="multipart",
            )

        res = self.client.get(
            detail_url(self.movie.id)
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            image = Image.new("RGB", (10, 10))
            image.save(ntf, format="JPEG")
            ntf.seek(0)

            self.client.post(
                url,
                {"image": ntf},
                format="multipart",
            )

        res = self.client.get(MOVIE_URL)

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn("image", res.data[0])

    def test_image_url_is_shown_on_movie_session(self):
        cinema_hall = CinemaHall.objects.create(
            name="Blue",
            rows=20,
            seats_in_row=20,
        )

        MovieSession.objects.create(
            show_time="2022-06-02 14:00:00",
            movie=self.movie,
            cinema_hall=cinema_hall,
        )

        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            image = Image.new("RGB", (10, 10))
            image.save(ntf, format="JPEG")
            ntf.seek(0)

            self.client.post(
                url,
                {"image": ntf},
                format="multipart",
            )

        res = self.client.get(MOVIE_SESSION_URL)

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn("movie_image", res.data[0])
