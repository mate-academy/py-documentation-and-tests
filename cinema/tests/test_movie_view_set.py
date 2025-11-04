import os
from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import (
    APIClient,
    APITestCase
)

from cinema.models import (
    Movie,
    Actor,
    Genre
)
from cinema.serializers import MovieListSerializer

CINEMA_URL = reverse("cinema:movie-list")

class UnauthorizedMovieTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthorized(self):
        res = self.client.get(CINEMA_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "The Titanic",
        "description": "The movie description",
        "duration": 109,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)

def detail_movie(movie_id) -> str:
    return reverse("cinema:movie-detail", args=(movie_id,))


class AuthorizedMovieTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test.user@example.ie",
            password="password.test.user",
        )
        self.client.force_authenticate(user=self.user)

    def test_authorized_movie_list(self):
        sample_movie()
        movie_with_actors_genres = sample_movie(title="The Devil Wears Prada")

        actor_1 = Actor.objects.create(first_name="Anne", last_name="Hathaway")
        actor_2 = Actor.objects.create(first_name="Emily", last_name="Blunt")
        genre = Genre.objects.create(name="Comedy")

        movie_with_actors_genres.actors.add(actor_1)
        movie_with_actors_genres.actors.add(actor_2)
        movie_with_actors_genres.genres.add(genre)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        res = self.client.get(CINEMA_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_authorized_movie_filters(self):
        the_titanic = sample_movie()
        the_devil_wears_prada = sample_movie(title="The Devil Wears Prada")
        interstellar = sample_movie(title="Interstellar")

        actor_anne_hathaway = Actor.objects.create(
            first_name="Anne", last_name="Hathaway"
        )
        actor_emily_blunt = Actor.objects.create(
            first_name="Emily", last_name="Blunt"
        )
        genre_comedy = Genre.objects.create(name="Comedy")
        genre_scifi = Genre.objects.create(name="Sci-Fi")

        the_devil_wears_prada.actors.add(
            actor_anne_hathaway, actor_emily_blunt
        )
        the_devil_wears_prada.genres.add(genre_comedy)
        interstellar.actors.add(actor_anne_hathaway)
        interstellar.genres.add(genre_scifi)

        serializer_without_actors_genres = MovieListSerializer(
            [the_titanic], many=True
        )
        serializer_comedy = MovieListSerializer(
            [the_devil_wears_prada], many=True
        )
        serializer_interstellar = MovieListSerializer(
            [interstellar], many=True
        )
        serializer_emily_blunt = MovieListSerializer(
            [the_devil_wears_prada], many=True
        )
        res_comedy = self.client.get(
            CINEMA_URL, {"genres": genre_comedy.id}
        )
        res_anne_hathaway = self.client.get(
            CINEMA_URL, {"actors": actor_anne_hathaway.id}
        )
        res_scifi = self.client.get(
            CINEMA_URL,
            {"genres": genre_scifi.id}
        )
        self.assertEqual(res_comedy.data, serializer_comedy.data)
        self.assertIn(serializer_interstellar.data[0], res_anne_hathaway.data)
        self.assertIn(serializer_interstellar.data[0], res_scifi.data)
        self.assertNotIn(serializer_emily_blunt.data, res_scifi.data)
        self.assertNotIn(
            serializer_without_actors_genres.data, res_anne_hathaway.data
        )

    def test_authorized_movie_retrieve(self):
        movie = sample_movie()
        movie.actors.add(
            Actor.objects.create(first_name="Anne", last_name="Hathaway")
        )
        movie.genres.add(Genre.objects.create(name="Comedy"))
        url = detail_movie(movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class AdminMovieViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test.admin@example.ie",
            password="password.test.user",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_admin_movie_create(self):
        payload = {
            "title": "Hitch",
            "description": "The Hitch description",
            "duration": 109,
        }
        res = self.client.post(CINEMA_URL, payload)
        movie = Movie.objects.get(pk=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_admin_create_movie_with_actors(self):
        payload = {
            "title": "Mr. & Mrs. Smith",
            "description": "The Mr. & Mrs. Smith description",
            "duration": 120,
            "actors": [
                Actor.objects.create(first_name="Brad", last_name="Pitt").id,
                Actor.objects.create(
                    first_name="Angelina", last_name="Jolie"
                ).id
            ],
            "genres": [
                Genre.objects.create(name="Action").id,
                Genre.objects.create(name="Comedy").id
            ],
        }
        res = self.client.post(CINEMA_URL, payload)
        movie = Movie.objects.get(pk=res.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(actors.count(), 2)
        self.assertEqual(genres.count(), 2)

    def test_admin_movie_update(self):
        movie = sample_movie()
        url = detail_movie(movie.id)
        payload = {
            "id": movie.id,
            "title": "Mr. & Mrs. Smith",
            "description": "The Mr. & Mrs. Smith description",
            "duration": 120,
            "actors": [
                Actor.objects.create(first_name="Brad", last_name="Pitt").id,
                Actor.objects.create(
                    first_name="Angelina", last_name="Jolie"
                ).id
            ],
            "genres": [
                Genre.objects.create(name="Action").id,
                Genre.objects.create(name="Comedy").id
            ],
        }
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_admin_movie_delete(self):
        movie = sample_movie()
        url = detail_movie(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_upload_image(self):
        movie = sample_movie()
        image = Image.new("RGB", (100, 100), color="pink")
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)
        image_file = SimpleUploadedFile(
            name="test-image.jpg",
            content=buffer.read(),
            content_type="image/jpeg"
        )
        payload = {
            "image": image_file,
        }
        url = detail_movie(movie.id) + "upload-image/"
        res = self.client.post(url, payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        self.assertTrue(movie.image)
        if movie.image:
            if os.path.exists(movie.image.path):
                os.remove(movie.image.path)
            movie.image.delete(save=False)
