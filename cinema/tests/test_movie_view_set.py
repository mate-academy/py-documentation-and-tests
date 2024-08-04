from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from cinema.models import Movie, Genre, Actor


def get_movie_list_url():
    return reverse("cinema:movie-list")


def get_movie_detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])

def get_movie_upload_image_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def get_setup_data(is_staff: bool):
    user_data = {
        "email": "email@example.com",
        "password": "testpassword"
    }
    if is_staff:
        user_data["is_staff"] = True

    movie_data = {
        "title": "Test movie",
        "description": "Test movie",
        "duration": 90
    }
    return (
        get_user_model().objects.create_user(**user_data),
        Movie.objects.create(**movie_data)
    )


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(get_movie_list_url())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user, self.movie = get_setup_data(is_staff=False)
        self.client.force_authenticate(self.user)

    def test_list_movies_authenticated(self):
        response = self.client.get(get_movie_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_movie_authenticated(self):
        response = self.client.get(get_movie_detail_url(self.movie.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_genres_authenticated(self):
        genre = Genre.objects.create(name="Comedy")
        self.movie.genres.add(genre)
        response = self.client.get(get_movie_list_url(), {"genres": genre.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.movie.title, response.data[0]["title"])


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user, self.movie = get_setup_data(is_staff=True)
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Genre")
        actor_1 = Actor.objects.create(
            first_name="First name 1", last_name="Last name 1"
        )
        actor_2 = Actor.objects.create(
            first_name="First name 2", last_name="Last name 2"
        )
        payload = {
            "title": "Title",
            "description": "Description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor_1.id, actor_2.id],
        }

        result = self.client.post(get_movie_list_url(), payload, format='json')

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=result.data["id"])

        genres = movie.genres.all()
        self.assertIn(genre, genres)
        self.assertEqual(genres.count(), 1)

        actors = movie.actors.all()
        self.assertEqual(actors.count(), 2)

    def test_update_movie(self):
        payload = {
            "title": "Updated Title",
            "description": "Updated Description",
            "duration": 120
        }

        result = self.client.patch(
            get_movie_detail_url(self.movie.id), payload, format='json'
        )

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.movie.refresh_from_db()
        for key in payload:
            self.assertEqual(payload[key], getattr(self.movie, key))

    def test_delete_movie(self):
        result = self.client.delete(get_movie_detail_url(self.movie.id))

        self.assertEqual(
            result.status_code, status.HTTP_200_OK
        )
