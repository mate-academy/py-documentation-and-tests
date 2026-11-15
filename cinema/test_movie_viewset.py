from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework.reverse import reverse
from cinema.models import Movie, Actor, Genre

MOVIE_LIST_URL = reverse("cinema:movie-list")
MOVIE_DETAIL_URL = reverse("cinema:movie-detail", args=[2])
MOVIE_IMAGE_URL = reverse("cinema:movie-upload-image", args=[1])


class UnAuthenticatedUserMovieVieset(APITestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth(self):
        response = self.client.get(MOVIE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        print(f"Test w/o auth got a status: {response.status_code}")

    def test_create_movie_no_auth(self):
        response = self.client.post(MOVIE_LIST_URL, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        print(f"Test create a movie w/o auth got a status: "
              f"{response.status_code}")

    def test_retrieve_movie_no_auth(self):
        response = self.client.get(MOVIE_DETAIL_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        print(f"Test retrieve a movie w/o auth got a status: "
              f"{response.status_code}")

    def test_upload_image_no_auth(self):
        response = self.client.post(MOVIE_IMAGE_URL, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        print(f"Test upload image w/o auth got a status: "
              f"{response.status_code}")


class AuthenticatedUserMovieVieset(APITestCase):
    def create_movie_sample(self, **kwargs):
        default_values = {"title": "Inception", "duration": 105}
        default_values.update(**kwargs)
        return Movie.objects.create(**default_values)

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin.user@cinema.com",
            password="1qazcde3"
        )
        self.client.force_authenticate(self.user)

        self.movie = self.create_movie_sample()
        self.actor = Actor.objects.create(
            first_name="Leonardo",
            last_name="DiCaprio"
        )
        self.genre = Genre.objects.create(
            name="Sci-Fi"
        )
        self.movie.actors.add(self.actor)
        self.movie.genres.add(self.genre)

    def test_movie_list(self):
        response = self.client.get(MOVIE_LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(f"Test movie list with auth got a status: "
              f"{response.status_code}")

    def test_movie_retrieve(self):
        response = self.client.get(
            reverse("cinema:movie-detail", args=[self.movie.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Inception")
        print(f"Test retrieve movie with auth got a status: "
              f"{response.status_code}")

    def test_upload_image_forbidden(self):
        response = self.client.post(reverse(
            "cinema:movie-upload-image",
            args=[self.movie.id]
        ))

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )
        print(f"Test uload image with auth got a status: "
              f"{response.status_code}")

    def test_filter_movies_by_title(self):
        response = self.client.get(
            MOVIE_LIST_URL,
            {"title": "Inception"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Inception")
        print(f"Test filter by title got a status: {response.status_code}")

    def test_filter_movies_by_genre(self):
        response = self.client.get(
            MOVIE_LIST_URL,
            {"genres": self.genre.id}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        print(f"Test filter by genres with auth got a status: "
              f"{response.status_code}")

    def test_filter_movies_by_actor(self):
        response = self.client.get(
            MOVIE_LIST_URL,
            {"actors": self.actor.id}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        print(f"Test filter by actors with auth got a status: "
              f"{response.status_code}")
