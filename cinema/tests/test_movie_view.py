from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from rest_framework.views import APIView

from cinema.models import Movie, Genre, Actor


User = get_user_model()


def sample_genres():
    genres = [
        Genre(name="genre1"),
        Genre(name="genre2"),
        Genre(name="genre3"),
    ]
    return list(Genre.objects.bulk_create(genres))


def sample_actors():
    actors = [
        Actor(first_name="actor1", last_name="test"),
        Actor(first_name="actor2", last_name="test"),
        Actor(first_name="actor3", last_name="test"),
        Actor(first_name="actor4", last_name="test"),
    ]
    return list(Actor.objects.bulk_create(actors))


def sample_movies():
    movies = [
        Movie(title="movie1", description="description1", duration=100),
        Movie(title="movie2", description="description2", duration=100),
        Movie(title="movie3", description="description3", duration=100),
        Movie(title="movie4", description="description4", duration=100),
    ]
    return list(Movie.objects.bulk_create(movies))


def set_actors(movies: list[Movie], actors):
    movies[0].actors.set([actors[0]])
    movies[1].actors.set([actors[0], actors[1]])
    movies[2].actors.set([actors[1], actors[2], actors[3]])
    movies[3].actors.set([actors[1], actors[3]])


def set_genres(movies: list[Movie], genres):
    movies[0].genres.set([genres[0]])
    movies[1].genres.set([genres[0], genres[1]])
    movies[2].genres.set([genres[2]])
    movies[3].genres.set([genres[1], genres[2]])


class TestMovieView(APITestCase):
    @classmethod
    def setUpTestData(cls):
        APIView.throttle_classes = []

        cls.admin = User.objects.create_user(
            email="admin@admin.com", password="p", is_staff=True
        )
        cls.user = User.objects.create_user(
            email="user@user.com", password="p"
        )
        cls.headers = {}
        cls.movies = sample_movies()
        cls.genres = sample_genres()
        cls.actors = sample_actors()
        set_actors(cls.movies, cls.actors)
        set_genres(cls.movies, cls.genres)

    def authenticate(self, user = None):
        if not user:
            self.client.logout()
            self.headers = {}
            return True

        url = reverse("token-obtain-pair")
        data = {"email": user.email, "password": "p"}
        response = self.client.post(url, data=data)
        if response.status_code != status.HTTP_200_OK:
            print(response.data)
            return False
        
        self.headers = {
            "Authorization": f"Bearer {response.data["access"]}"
        }
        return True

    def test_list_action(self):
        self.authenticate(self.admin)
        url = reverse("cinema:movie-list")
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        titles = [movie["title"] for movie in response.data]
        for movie in self.movies:
            self.assertIn(movie.title, titles)

    def test_unauthorized_list_action(self):
        self.authenticate()
        url = reverse("cinema:movie-list")
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_list_action(self):
        self.authenticate(self.user)
        url = reverse("cinema:movie-list")
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_action(self):
        self.authenticate(self.admin)
        movie_id = self.movies[0].id
        url = reverse("cinema:movie-detail", args=[movie_id])
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.movies[0].title)

    def test_unauthorized_retrieve_action(self):
        self.authenticate()
        movie_id = self.movies[0].id
        url = reverse("cinema:movie-detail", args=[movie_id])
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_retrieve_action(self):
        self.authenticate(self.user)
        movie_id = self.movies[0].id
        url = reverse("cinema:movie-detail", args=[movie_id])
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.movies[0].title)

    def test_create_action(self):
        self.authenticate(self.admin)
        genre_ids = [genre.id for genre in self.genres[:2]]
        actor_ids = [actor.id for actor in self.actors[:2]]
        payload = {
            "title": "new movie",
            "description": "new description",
            "duration": 120,
            "genres": genre_ids,
            "actors": actor_ids,
        }
        url = reverse("cinema:movie-list")
        response = self.client.post(url, payload, format="json", headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], payload["title"])

    def test_unauthorized_create_action(self):
        self.authenticate()
        genre_ids = [genre.id for genre in self.genres[:2]]
        actor_ids = [actor.id for actor in self.actors[:2]]
        payload = {
            "title": "new movie",
            "description": "new description",
            "duration": 120,
            "genres": genre_ids,
            "actors": actor_ids,
        }
        url = reverse("cinema:movie-list")
        response = self.client.post(url, payload, format="json", headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_create_action(self):
        self.authenticate(self.user)
        genre_ids = [genre.id for genre in self.genres[:2]]
        actor_ids = [actor.id for actor in self.actors[:2]]
        payload = {
            "title": "new movie",
            "description": "new description",
            "duration": 120,
            "genres": genre_ids,
            "actors": actor_ids,
        }
        url = reverse("cinema:movie-list")
        response = self.client.post(url, payload, format="json", headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_title(self):
        self.authenticate(self.admin)
        url = reverse("cinema:movie-list") + f"?title={self.movies[0].title}"
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.movies[0].title)

    def test_filter_by_non_exist_title(self):
        self.authenticate(self.admin)
        url = reverse("cinema:movie-list") + "?title=lkadgahoshgkadlkajfdoihag"
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_filter_by_genres(self):
        self.authenticate(self.admin)
        url = reverse("cinema:movie-list") + f"?genres={self.genres[0].id}"
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # movie1 and movie2 have genre1
        titles = [movie["title"] for movie in response.data]
        self.assertIn(self.movies[0].title, titles)
        self.assertIn(self.movies[1].title, titles)

    def test_filter_by_couple_genres(self):
        self.authenticate(self.admin)
        genre_ids = f"{self.genres[0].id},{self.genres[1].id}"
        url = reverse("cinema:movie-list") + f"?genres={genre_ids}"
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # movie1 and movie2 have genre1
        # movie2 and movie4 have genre2
        self.assertEqual(len(response.data), 3)
        titles = [movie["title"] for movie in response.data]
        self.assertIn(self.movies[0].title, titles)
        self.assertIn(self.movies[1].title, titles)
        self.assertIn(self.movies[3].title, titles)

    def test_filter_by_non_exist_genres(self):
        self.authenticate(self.admin)
        non_exist_ids = f"43523,53452"
        url = reverse("cinema:movie-list") + f"?genres={non_exist_ids}"
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_filter_by_actors(self):
        self.authenticate(self.admin)
        actor_id = self.actors[0].id
        url = reverse("cinema:movie-list") + f"?actors={actor_id}"
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # movie1 and movie2 have actor1
        titles = [movie["title"] for movie in response.data]
        self.assertIn(self.movies[0].title, titles)
        self.assertIn(self.movies[1].title, titles)

    def test_filter_by_couple_actors(self):
        self.authenticate(self.admin)
        actor_ids = f"{self.actors[0].id},{self.actors[2].id}"
        url = reverse("cinema:movie-list") + f"?actors={actor_ids}"
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        # movie1 and movie2 have actor1
        # movie3 have actor3
        titles = [movie["title"] for movie in response.data]
        self.assertIn(self.movies[0].title, titles)
        self.assertIn(self.movies[1].title, titles)
        self.assertIn(self.movies[2].title, titles)

    def test_filter_by_non_exist_actors(self):
        self.authenticate(self.admin)
        non_exist_ids = f"3452,235231"
        url = reverse("cinema:movie-list") + f"?actors={non_exist_ids}"
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
