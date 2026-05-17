from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from cinema.models import Movie, Genre, Actor

MOVIE_LIST_URL = reverse("cinema:movie-list")

class UnauthenticatedUserMovieTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUserMovieApiTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        user = get_user_model().objects.create_user(email='test@test.pl', password='password')
        self.client.force_authenticate(user)

    def create_movie_sample(self, **kwargs):
        default={"title": "one", "description": "ajaj", "duration":111}
        genres = kwargs.pop("genres", None)
        actors = kwargs.pop("actors", None)
        default.update(**kwargs)
        movie = Movie.objects.create(**default)

        if genres:
            if isinstance(genres, (list, tuple)):
                movie.genres.add(*genres)
            else:
                movie.genres.add(genres)

        if actors:
            if isinstance(actors, (list, tuple)):
                movie.actors.add(*actors)
            else:
                movie.actors.add(actors)
        return movie

    def test_movie_list(self):
        movie = self.create_movie_sample()
        response = self.client.get(MOVIE_LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], movie.title)

    def test_movie_filtering_by_actor_and_genres(self):
        actor = Actor.objects.create(first_name="Adam", last_name="Smith")
        genre = Genre.objects.create(name="horror")

        movie_nothing = self.create_movie_sample(title="movie_nothing")
        movie_genre = self.create_movie_sample(genres=genre.id,)
        movie_actor = self.create_movie_sample(actors=actor.id)

        movie_genre.genres.add(genre)
        movie_actor.actors.add(actor)


        response_without_filtering = self.client.get(MOVIE_LIST_URL)
        self.assertEqual(len(response_without_filtering.json()), 3)


        filtering_params_actor = {'actors': f"{actor.id}"}
        response = self.client.get(MOVIE_LIST_URL, filtering_params_actor)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], movie_actor.title)

        filtering_params_wc = {'genres': f"{genre.id}"}
        response = self.client.get(MOVIE_LIST_URL, filtering_params_wc)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], movie_genre.title)

    def test_single_movie(self):
        movie = self.create_movie_sample()
        url = reverse("cinema:movie-detail", args=[movie.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], movie.title)

    def test_create_movie(self):
        payload = {'title': "movie_title", "description": "some description","duration":122}
        response = self.client.post(MOVIE_LIST_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title=payload["title"]).exists())


class AdminMovieApiTestCase(APITestCase):
    def setUp(self):
        admin_user = get_user_model().objects.create_user(email='admin@test.pl', password='password', is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(admin_user)

    def test_create_movie(self):
        actor = Actor.objects.create(first_name="Adam", last_name="Smith")
        payload = {
            "title": "movie_name2",
            "description": "abc",
            "duration": 120
        }
        response = self.client.post(MOVIE_LIST_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["title"], payload["title"])
        self.assertTrue(Movie.objects.filter(title=payload["title"]).exists())