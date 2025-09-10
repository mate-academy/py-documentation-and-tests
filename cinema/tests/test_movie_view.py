from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from cinema.models import Movie, Genre, Actor


User = get_user_model()


def sample_genres():
    genres = [
        Genre(name="genre1"),
        Genre(name="genre2"),
        Genre(name="genre3"),
    ]
    return Genre.objects.bulk_create(genres)


def sample_actors():
    actors = [
        Actor(first_name="actor1", last_name="test"),
        Actor(first_name="actor2", last_name="test"),
        Actor(first_name="actor3", last_name="test"),
        Actor(first_name="actor4", last_name="test"),
    ]
    return Actor.objects.bulk_create(actors)


def sample_movies():
    movies = [
        Movie(title="movie1", description="description1", duration=100),
        Movie(title="movie2", description="description2", duration=100),
        Movie(title="movie3", description="description3", duration=100),
        Movie(title="movie4", description="description4", duration=100),
    ]
    return Movie.objects.bulk_create(movies)


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
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@admin.com", password="p", is_staff=True
        )
        self.user = User.objects.create_user(
            email="user@user.com", password=""
        )
        self.client.force_authenticate(user=self.admin)
        self.movies = sample_movies()
        self.genres = sample_genres()
        self.actors = sample_actors()
        set_actors(self.movies, self.actors)
        set_genres(self.movies, self.genres)

    def test_list_action(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        titles = [movie["title"] for movie in response.data]
        for movie in self.movies:
            self.assertIn(movie.title, titles)

    def test_unauthorized_list_action(self):
        self.client.logout()
        url = reverse("cinema:movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_list_action(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("cinema:movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_action(self):
        movie_id = self.movies[0].id
        url = reverse("cinema:movie-detail", args=[movie_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.movies[0].title)

    def test_unauthorized_retrieve_action(self):
        self.client.logout()
        movie_id = self.movies[0].id
        url = reverse("cinema:movie-detail", args=[movie_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_retrieve_action(self):
        self.client.force_authenticate(self.user)
        movie_id = self.movies[0].id
        url = reverse("cinema:movie-detail", args=[movie_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.movies[0].title)

    def test_create_action(self):
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
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], payload["title"])

    def test_unauthorized_create_action(self):
        self.client.logout()
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
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_create_action(self):
        self.client.force_authenticate(self.user)
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
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_title(self):
        url = reverse("cinema:movie-list") + "?title=movie1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "movie1")

    def test_filter_by_non_exist_title(self):
        url = reverse("cinema:movie-list") + "?title=lkadgahoshgkadlkajfdoihag"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_filter_by_genres(self):
        url = reverse("cinema:movie-list") + "?genres=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # movie1 and movie2 have genre1
        titles = [movie["title"] for movie in response.data]
        self.assertIn("movie1", titles)
        self.assertIn("movie2", titles)

    def test_filter_by_couple_genres(self):
        url = reverse("cinema:movie-list") + "?genres=1,2"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # movie1 and movie2 have genre1
        # movie2 and movie4 have genre2
        self.assertEqual(len(response.data), 3)
        titles = [movie["title"] for movie in response.data]
        self.assertIn("movie1", titles)
        self.assertIn("movie2", titles)
        self.assertIn("movie4", titles)

    def test_filter_by_non_exist_genres(self):
        url = reverse("cinema:movie-list") + "?genres=25,78"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_filter_by_actors(self):
        url = reverse("cinema:movie-list") + "?actors=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # movie1 and movie2 have actor1
        titles = [movie["title"] for movie in response.data]
        self.assertIn("movie1", titles)
        self.assertIn("movie2", titles)

    def test_filter_by_couple_actors(self):
        url = reverse("cinema:movie-list") + "?actors=1,3"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        # movie1 and movie2 have actor1
        # movie3 have actor3
        titles = [movie["title"] for movie in response.data]
        self.assertIn("movie1", titles)
        self.assertIn("movie2", titles)
        self.assertIn("movie3", titles)

    def test_filter_by_non_exist_actors(self):
        url = reverse("cinema:movie-list") + "?actors=124,123"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
