from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIClient

from cinema.models import Movie, Genre, Actor

MOVIE_LIST_URL = reverse("cinema:movies-list")

def create_sample_movie(**kwargs):
    default_values = {"title": "test_movie", "duration": 15}
    default_values.update(kwargs)
    return Movie.objects.create(**default_values)

class UnauthenticatedMovieApiTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required_list(self):
        response = self.client.get(MOVIE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_detail(self):
        movie = create_sample_movie()
        url = reverse("cinema:movies-detail", args=[movie.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        user = get_user_model().objects.create_user(email="test@test.test", password="password")
        self.client.force_authenticate(user=user)

    def test_movie_list(self):
        movie = create_sample_movie()
        response = self.client.get(MOVIE_LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], movie.title)

    def test_movie_detail(self):
        movie = create_sample_movie()
        url = reverse("cinema:movies-detail", args=[movie.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], movie.title)

    def test_movie_filtering_by_titles(self):
        movie_1 = create_sample_movie(title="test_movie_1")
        movie_2 = create_sample_movie(title="test_movie_2")
        movie_3 = create_sample_movie(title="test_movie_2")

        filtering_params_1 = {"title": movie_1.title}
        filtering_params_2 = {"title": movie_2.title}

        response = self.client.get(MOVIE_LIST_URL, filtering_params_1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], movie_1.title)

        response = self.client.get(MOVIE_LIST_URL, filtering_params_2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]["title"], movie_2.title)
        self.assertEqual(response.json()[1]["title"], movie_3.title)

    def test_movie_filtering_by_genres(self):
        movie_1 = create_sample_movie(title="test_movie_1")
        movie_2 = create_sample_movie(title="test_movie_2")
        movie_3 = create_sample_movie(title="test_movie_3")

        genre_1 = Genre.objects.create(name="test_genre_1")
        genre_2 = Genre.objects.create(name="test_genre_2")

        movie_1.genres.add(genre_1)
        movie_2.genres.add(genre_2)
        movie_3.genres.add(genre_2)

        filtering_params_1 = {"genres": f"{genre_1.id}"}
        filtering_params_2 = {"genres": f"{genre_2.id}"}

        response = self.client.get(MOVIE_LIST_URL, filtering_params_1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], movie_1.title)

        response = self.client.get(MOVIE_LIST_URL, filtering_params_2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]["title"], movie_2.title)
        self.assertEqual(response.json()[1]["title"], movie_3.title)

    def test_movie_filtering_by_actors(self):
        movie_1 = create_sample_movie(title="test_movie_1")
        movie_2 = create_sample_movie(title="test_movie_2")
        movie_3 = create_sample_movie(title="test_movie_3")

        actor_1 = Actor.objects.create(first_name="test_first_name_1", last_name="test_last_name_1")
        actor_2 = Actor.objects.create(first_name="test_first_name_2", last_name="test_last_name_2")

        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_2)
        movie_3.actors.add(actor_2)

        filtering_params_1 = {"actors": f"{actor_1.id}"}
        filtering_params_2 = {"actors": f"{actor_2.id}"}

        response = self.client.get(MOVIE_LIST_URL, filtering_params_1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], movie_1.title)

        response = self.client.get(MOVIE_LIST_URL, filtering_params_2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]["title"], movie_2.title)
        self.assertEqual(response.json()[1]["title"], movie_3.title)

    def test_movie_filtering_by_multiple(self):
        movie_1 = create_sample_movie(title="test_movie_1")
        movie_2 = create_sample_movie(title="test_movie_2")
        movie_3 = create_sample_movie(title="test_movie_2")

        genre_1 = Genre.objects.create(name="test_genre_1")
        genre_2 = Genre.objects.create(name="test_genre_2")

        movie_1.genres.add(genre_1)
        movie_2.genres.add(genre_2)
        movie_3.genres.add(genre_2)

        actor_1 = Actor.objects.create(first_name="test_first_name_1", last_name="test_last_name_1")
        actor_2 = Actor.objects.create(first_name="test_first_name_2", last_name="test_last_name_2")

        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_1)
        movie_3.actors.add(actor_2)

        filtering_params = {"title": movie_2.title, "genres": f"{genre_2.id}", "actors": f"{actor_1.id}"}

        response = self.client.get(MOVIE_LIST_URL, filtering_params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], movie_2.title)
        self.assertEqual(response.json()[0]["genres"], [movie_2.genres.all()[0].__str__()])
        self.assertEqual(response.json()[0]["actors"], [movie_2.actors.all()[0].__str__()])

    def test_create_movie_not_allowed(self):
        actor = Actor.objects.create(first_name="test_first_name", last_name="test_last_name")
        genre = Genre.objects.create(name="test_genre")
        payload = {"title": "test_movie", "description": "Test description", "duration": 15, "actors": [actor.id], "genres": [genre.id]}
        response = self.client.post(MOVIE_LIST_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title=payload["title"]).exists())


class AdminBusApiTestCase(APITestCase):
    def setUp(self):
        admin_user = get_user_model().objects.create_superuser(email="admin@admin,com", password="password", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(user=admin_user)

    def test_create_movie(self):
        actor = Actor.objects.create(first_name="test_first_name", last_name="test_last_name")
        genre = Genre.objects.create(name="test_genre")
        payload = {"title": "test_movie", "description": "Test description", "duration": 15, "actors": [actor.id], "genres": [genre.id]}
        response = self.client.post(MOVIE_LIST_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["title"], payload["title"])
        self.assertTrue(Movie.objects.filter(title=payload["title"]).exists())
