from django.urls import reverse
from rest_framework.exceptions import ErrorDetail
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from cinema.models import Movie, Genre, Actor
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from io import BytesIO
from PIL import Image

User = get_user_model()


def create_genre(name: str) -> Genre:
    return Genre.objects.create(name=name)


def create_actor(first_name: str, last_name: str) -> Actor:
    return Actor.objects.create(first_name=first_name, last_name=last_name)


def create_movie(title: str, genres=None, actors=None) -> Movie:
    movie = Movie.objects.create(
        title=title, description="Sample description", duration=120
    )
    if genres:
        movie.genres.set(genres)
    if actors:
        movie.actors.set(actors)
    return movie


def generate_image_file():
    image = Image.new("RGB", (100, 100))
    byte_arr = BytesIO()
    image.save(byte_arr, format="PNG")
    byte_arr.seek(0)
    return byte_arr

class MovieViewSetTestData(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="testuser@example.com", password="testpass"
        )
        self.admin_user = User.objects.create_superuser(
            email="adminuser@example.com", password="adminpass"
        )
        self.token = Token.objects.create(user=self.user)
        self.admin_token = Token.objects.create(user=self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        self.genre1 = create_genre("Action")
        self.genre2 = create_genre("Drama")

        self.actor1 = create_actor("John", "Doe")
        self.actor2 = create_actor("Jane", "Smith")

        self.movie1 = create_movie(
            "Movie One", genres=[self.genre1], actors=[self.actor1]
        )
        self.movie2 = create_movie(
            "Movie Two", genres=[self.genre2], actors=[self.actor2]
        )

class MovieViewSetTests(MovieViewSetTestData):

    def test_list_movies(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_movies_by_title(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url, {"title": "Movie One"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Movie One")

    def test_filter_movies_by_genres(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url, {"genres": f"{self.genre1.id}"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Movie One")

    def test_filter_movies_by_actors(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url, {"actors": f"{self.actor1.id}"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Movie One")

    def test_create_movie_as_authenticated_user(self):
        url = reverse("cinema:movie-list")
        data = {
            "title": "New Movie",
            "description": "A new movie description",
            "duration": 90,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id, self.actor2.id],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        expected_error = {
            "detail": ErrorDetail(
            string="You do not have permission to perform this action.",
            code="permission_denied"
            )
        }
        self.assertEqual(response.data, expected_error)

    def test_create_movie_as_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        url = reverse("cinema:movie-list")
        data = {
            "title": "New Movie",
            "description": "A new movie description",
            "duration": 90,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id, self.actor2.id],
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data["title"], "New Movie")

        movie = Movie.objects.get(title="New Movie")

        self.assertEqual(movie.description, "A new movie description")
        self.assertEqual(movie.duration, 90)
        self.assertEqual(list(movie.genres.values_list('id', flat=True)), [self.genre1.id])
        self.assertEqual(list(movie.actors.values_list('id', flat=True)), [self.actor1.id, self.actor2.id])

    def test_retrieve_movie(self):
        url = reverse("cinema:movie-detail", args=[self.movie1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Movie One")
        response_genre_ids = [genre['id'] for genre in response.data["genres"]]
        expected_genre_ids = [self.genre1.id]
        self.assertEqual(response_genre_ids, expected_genre_ids)
        response_actor_ids = [actor['id'] for actor in response.data["actors"]]
        expected_actor_ids = [self.actor1.id]
        self.assertEqual(response_actor_ids, expected_actor_ids)

    def test_upload_movie_image_as_authenticated_user(self):
        url = reverse(
            "cinema:movie-upload-image", args=[self.movie1.id]
        )  # Updated URL name
        image_file = generate_image_file()
        response = self.client.post(url, {"image": image_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_cannot_delete_movie(self):
        url = reverse("cinema:movie-detail", args=[self.movie1.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
