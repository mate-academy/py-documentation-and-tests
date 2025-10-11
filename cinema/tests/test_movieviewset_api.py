from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieSerializer


def get_movie_list_url():
    return reverse("cinema:movie-list")


def movie_detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    genres = params.pop("genres", [])
    actors = params.pop("actors", [])
    defaults = {"title": "test_movie", "duration": 111}
    defaults.update(params)
    movie = Movie.objects.create(**defaults)
    if genres:
        movie.genres.set(genres)
    if actors:
        movie.actors.set(actors)
    return movie


def sample_genre(name="Action"):
    return Genre.objects.create(name=name)


def sample_actor(name="John Doe"):
    return Actor.objects.create(name=name)


class UnauthenticatedMovieApiTests(TestCase):
    """Tests for unauthenticated access"""

    def setUp(self):
        self.client = APIClient()
        self.movie_url = get_movie_list_url()

    def test_auth_not_required_for_readonly(self):
        """Public can view movies (read-only)"""
        res = self.client.get(self.movie_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class AuthenticatedMovieApiTests(TestCase):
    """Tests for authenticated user actions"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword"
        )
        self.client.force_authenticate(self.user)
        self.movie_url = get_movie_list_url()

    def test_movie_list(self):
        sample_movie()
        res = self.client.get(self.movie_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movies = Movie.objects.all()
        serializer = MovieSerializer(movies, many=True)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        url = movie_detail_url(movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        serializer = MovieSerializer(movie)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_with_relations(self):
        genre = sample_genre("Thriller")
        actor = sample_actor("Tom Hanks")
        payload = {
            "title": "New Movie",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(self.movie_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_full_update_movie_put(self):
        movie = sample_movie()
        payload = {"title": "Updated Movie", "duration": 150}
        url = movie_detail_url(movie.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.duration, payload["duration"])

    def test_partial_update_movie_patch(self):
        movie = sample_movie()
        payload = {"title": "Partial Update"}
        url = movie_detail_url(movie.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        self.assertEqual(movie.title, payload["title"])

    def test_delete_movie(self):
        movie = sample_movie()
        url = movie_detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Movie.objects.filter(id=movie.id).exists())

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Alpha")
        sample_movie(title="Beta")
        res = self.client.get(self.movie_url, {"title": "Alpha"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data["results"] if isinstance(res.data, dict) else res.data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Alpha")

    def test_filter_movies_by_genres(self):
        genre1 = sample_genre("Action")
        genre2 = sample_genre("Comedy")
        movie1 = sample_movie(title="M1", genres=[genre1])
        sample_movie(title="M2", genres=[genre2])
        res = self.client.get(self.movie_url, {"genres": str(genre1.id)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data["results"] if isinstance(res.data, dict) else res.data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "M1")

    def test_filter_movies_by_actors(self):
        actor1 = sample_actor("Actor1")
        actor2 = sample_actor("Actor2")
        movie1 = sample_movie(title="M1", actors=[actor1])
        sample_movie(title="M2", actors=[actor2])
        res = self.client.get(self.movie_url, {"actors": str(actor1.id)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data["results"] if isinstance(res.data, dict) else res.data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "M1")
