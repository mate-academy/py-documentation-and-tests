import tempfile

from django.contrib.auth import get_user_model
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from cinema.models import Actor, Genre, Movie
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def image_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_genre(name="Drama"):
    return Genre.objects.create(name=name)


def sample_actor(first_name="George", last_name="Clooney"):
    return Actor.objects.create(first_name=first_name, last_name=last_name)


class UnauthenticatedMovieApiTests(APITestCase):
    def test_list_requires_auth(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_requires_auth(self):
        movie = sample_movie()
        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="pass12345"
        )
        self.client.force_authenticate(self.user)

    # ---------- list ----------

    def test_list_movies(self):
        sample_movie(title="First")
        sample_movie(title="Second")

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.order_by("id")
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    # ---------- filters ----------

    def test_filter_by_title_is_case_insensitive_and_partial(self):
        movie1 = sample_movie(title="The Matrix")
        movie2 = sample_movie(title="Inception")

        res = self.client.get(MOVIE_URL, {"title": "matr"})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)

    def test_filter_by_genres(self):
        drama, comedy = sample_genre("Drama"), sample_genre("Comedy")
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie3 = sample_movie(title="Movie 3")
        movie1.genres.add(drama)
        movie2.genres.add(comedy)

        res = self.client.get(MOVIE_URL, {"genres": f"{drama.id},{comedy.id}"})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertIn(MovieListSerializer(movie2).data, res.data)
        self.assertNotIn(MovieListSerializer(movie3).data, res.data)

    def test_filter_by_actors(self):
        actor1 = sample_actor("Brad", "Pitt")
        actor2 = sample_actor("Tom", "Hanks")
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": str(actor1.id)})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)

    def test_filter_combined(self):
        genre = sample_genre()
        actor = sample_actor()
        match = sample_movie(title="Space Drama")
        match.genres.add(genre)
        match.actors.add(actor)
        wrong_title = sample_movie(title="Other")
        wrong_title.genres.add(genre)
        wrong_title.actors.add(actor)

        res = self.client.get(
            MOVIE_URL,
            {"title": "space", "genres": str(genre.id), "actors": str(actor.id)},
        )

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0], MovieListSerializer(match).data)

    def test_filter_returns_no_duplicates(self):
        genre1, genre2 = sample_genre("Drama"), sample_genre("Comedy")
        movie = sample_movie()
        movie.genres.add(genre1, genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})

        self.assertEqual(len(res.data), 1)

    # ---------- retrieve ----------

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, MovieDetailSerializer(movie).data)

    def test_retrieve_not_found(self):
        res = self.client.get(detail_url(9999))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ---------- forbidden for regular user ----------

    def test_create_movie_forbidden(self):
        payload = {"title": "New", "description": "Desc", "duration": 100}

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title="New").exists())

    def test_upload_image_forbidden(self):
        movie = sample_movie()
        res = self.client.post(image_url(movie.id), {}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_and_delete_forbidden_for_regular_user(self):
        movie = sample_movie()

        res_put = self.client.put(detail_url(movie.id), {})
        res_delete = self.client.delete(detail_url(movie.id))

        self.assertEqual(res_put.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res_delete.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com", password="pass12345"
        )
        self.client.force_authenticate(self.admin)
        self.movie = sample_movie()

    def tearDown(self):
        # прибираємо завантажені файли, щоб не засмічувати media/
        self.movie.image.delete()

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "New movie",
            "description": "Desc",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_create_movie_invalid_data(self):
        res = self.client.post(MOVIE_URL, {"title": ""})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_image(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            Image.new("RGB", (10, 10)).save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                image_url(self.movie.id), {"image": ntf}, format="multipart"
            )

        self.movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(self.movie.image)

    def test_upload_invalid_image(self):
        res = self.client.post(
            image_url(self.movie.id), {"image": "not an image"}, format="multipart"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_image_to_nonexistent_movie(self):
        res = self.client.post(image_url(9999), {}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_image_not_shown_in_list(self):
        # list використовує MovieListSerializer, а не MovieImageSerializer
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)