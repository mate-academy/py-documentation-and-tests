import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieSerializer, MovieListSerializer

MOVIE_LIST_URL = reverse("cinema:movie-list")

class UnAuthenticatedUserViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_user(self):
        response = self.client.get(MOVIE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUserViewTest(APITestCase):
    def create_sample_movie(self, **kwargs):
        data = {
            "title": "TestMovie",
            "description": "TestMovie description",
            "duration": 30,
        }
        data.update(kwargs)
        return Movie.objects.create(**data)

    def setUp(self):
        self.client = APIClient()
        user = get_user_model().objects.create_user(
            email="test@test.test",
            password="password"
        )
        self.client.force_authenticate(user=user)

    def test_authenticated_user(self):
        movie = self.create_sample_movie()
        response = self.client.get(MOVIE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], movie.title)

    def test_movie_filtering(self):
        movie_title = self.create_sample_movie(
            title="MovieTitle",
        )
        movie_actors = self.create_sample_movie(
            title="MovieActors",
        )
        movie_genres = self.create_sample_movie(
            title="MovieGenres",
        )

        actor = Actor.objects.create(
            first_name="TestActor",
            last_name="TestActor",
        )
        genre = Genre.objects.create(
            name="TestGenre",
        )

        movie_actors.actors.add(actor)
        movie_genres.genres.add(genre)

        filtering_params_title = {
            "title": f"{movie_title.title}",
        }
        filtering_params_actor = {
            "actors": f"{actor.id}",
        }
        filtering_params_genre = {
            "genres": f"{genre.id}",
        }

        response = self.client.get(MOVIE_LIST_URL, filtering_params_title)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], movie_title.title)

        response = self.client.get(MOVIE_LIST_URL, filtering_params_actor)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], movie_actors.title)

        response = self.client.get(MOVIE_LIST_URL, filtering_params_genre)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], movie_genres.title)

    def test_single_movie(self):
        movie = self.create_sample_movie()
        url = reverse("cinema:movie-detail", args=[movie.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], movie.title)

    def test_create_movie_not_allowed(self):
        payload = {
            "title": "TestMovie",
            "description": "TestMovie description",
            "duration": 20,
        }
        response = self.client.post(MOVIE_LIST_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title=payload["title"]).exists())


class AdminMovieApiTestCase(APITestCase):

    def setUp(self):
        admin_user = get_user_model().objects.create_user(
            email="admin@test.test",
            password="password",
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=admin_user)

    def test_create_movie_by_admin(self):
        actor = Actor.objects.create(
            first_name="TestActor",
            last_name="TestActor",
        )
        genre = Genre.objects.create(
            name="TestGenre",
        )

        data = {
            "title": "TestMovie",
            "description": "TestMovie description",
            "duration": 30,
            "actors": [actor.id],
            "genres": [genre.id],
        }
        response = self.client.post(MOVIE_LIST_URL, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["title"], data["title"])
        self.assertTrue(Movie.objects.filter(title=data["title"]).exists())


class MovieSerializerTestCase(APITestCase):
    def test_serializer_fields(self):
        movie = Movie.objects.create(
            title="TestMovie",
            description="TestMovie description",
            duration=30,
        )
        serializer = MovieListSerializer(movie)
        self.assertEqual(serializer.data["title"], movie.title)
        self.assertEqual(serializer.data["description"], movie.description)
        self.assertEqual(serializer.data["duration"], movie.duration)

class ImageUploadTestCase(APITestCase):
    def movie_sample_create(self):
        movie = Movie.objects.create(
            title="TestMovie",
            description="TestMovie description",
            duration=30,
        )
        actor = Actor.objects.create(
            first_name="TestActor",
            last_name="TestActor",
        )
        genre = Genre.objects.create(
            name="TestGenre",
        )
        movie.actors.add(actor)
        movie.genres.add(genre)
        return movie

    def setUp(self):
        self.client = APIClient()
        user = get_user_model().objects.create_user(
            email="test@test.test",
            password="password",
            is_staff=True,
        )
        self.client.force_authenticate(user=user)

    def test_upload_image(self):
        movie = self.movie_sample_create()
        url = reverse("cinema:movie-upload-image", args=[movie.id])

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)

            response = self.client.post(
                url,
                {"image": image_file},
                format="multipart"
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("image", response.json())
        movie.refresh_from_db()
        self.assertTrue(movie.image)

    def tearDown(self):
        for movie in Movie.objects.all():
            if movie.image:
                movie.image.delete()