from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_LIST_URL = reverse("cinema:movie-list")


def movie_detail_url(movie_id: int = 1):
    return reverse("cinema:movie-detail", args=[movie_id])


def fast_movie_create(name: str = "TestMovieName", time: int = 20) -> Movie:
    return Movie.objects.create(
        title=f"{name} Title",
        description=f"Description for {name}",
        duration=time,
    )


def fast_actor_create(name: str = "TestActorName") -> Actor:
    return Actor.objects.create(
        first_name=f"{name} Name",
        last_name=f"{name} Surname",
    )


def fast_genre_create(name: str = "TestGenre") -> Genre:
    return Genre.objects.create(
        name=f"{name} Name"
    )


class UnauthenticatedMovieListTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required_for_list(self):
        result = self.client.get(MOVIE_LIST_URL)
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieListTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        movie1 = fast_movie_create("Harry", 30)
        movie2 = fast_movie_create("Potter", 45)
        fast_movie_create("Voldemort", 45)

        actor1 = fast_actor_create("John")
        actor2 = fast_actor_create("Emma")

        genre1 = fast_genre_create("Mystic")
        genre2 = fast_genre_create("Magic")

        movie1.genres.add(genre1, genre2)
        movie2.actors.add(actor1, actor2)

        result = self.client.get(MOVIE_LIST_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = fast_movie_create("Harry", 30)
        movie2 = fast_movie_create("Potter", 45)
        movie3 = fast_movie_create("Voldemort", 45)

        actor1 = fast_actor_create("John")
        actor2 = fast_actor_create("Emma")

        genre1 = fast_genre_create("Mystic")
        genre2 = fast_genre_create("Magic")

        movie1.actors.add(actor1)
        movie2.actors.add(actor1, actor2)
        movie3.genres.add(genre1, genre2)

        result = self.client.get(MOVIE_LIST_URL, {
            "actors": f"{actor1.id}"
        })

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, result.data)
        self.assertIn(serializer2.data, result.data)
        self.assertNotIn(serializer3.data, result.data)

        result = self.client.get(MOVIE_LIST_URL, {
            "actors": f"{actor2.id}"
        })

        self.assertNotIn(serializer1.data, result.data)
        self.assertIn(serializer2.data, result.data)
        self.assertNotIn(serializer3.data, result.data)

    def test_retrieve_movie_detail(self):
        movie = fast_movie_create()
        movie.actors.add(fast_actor_create())
        movie.genres.add(fast_genre_create())

        url = movie_detail_url(movie.id)

        result = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_create_movie_forbidden(self):
        data = {
            "title": "Test Title",
            "description": "Description for Test",
            "duration": 20,
        }

        result = self.client.post(MOVIE_LIST_URL, data)
        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieListTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "adminpass",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        data = {
            "title": "Test Title",
            "description": "Description for Test",
            "duration": 20,
        }

        result = self.client.post(MOVIE_LIST_URL, data)

        movie = Movie.objects.get(id=result.data["id"])

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)

        for key in data:
            self.assertEqual(data[key], getattr(movie, key))

    def test_admin_can_not_delete_movie(self):
        movie = fast_movie_create()

        response = self.client.delete(
            reverse("cinema:movie-detail", args=[movie.id])
        )
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Movie.objects.filter(pk=movie.id).exists())

    def test_create_movie_with_genres(self):
        actor = fast_actor_create("Actor")
        genre1 = fast_genre_create("Test1")
        genre2 = fast_genre_create("Test2")

        data = {
            "title": "Test Title",
            "description": "Description for Test",
            "duration": 20,
            "genres": [genre1.id, genre2.id],
            "actors": [actor.id],
        }

        result = self.client.post(MOVIE_LIST_URL, data)

        movie = Movie.objects.get(id=result.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)

        self.assertEqual(actors.count(), 1)
        self.assertEqual(genres.count(), 2)

        self.assertIn(actor, actors)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
