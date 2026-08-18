from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

MOVIE_URL = reverse(\"cinema:movie-list\")


def detail_url(movie_id):
    return reverse(\"cinema:movie-detail\", args=[movie_id])


class UnauthenticatedMovieTests(APITestCase):
    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)


class AdminMovieTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email=\"admin@admin.com\", password=\"password123\"
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            \"title\": \"Test Movie\",
            \"description\": \"Test description\",
            \"duration\": 120,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data[\"id\"])
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_filter_movies_by_title(self):
        m1 = Movie.objects.create(
            title=\"Avatar\", description=\"Sci-fi\", duration=160
        )
        m2 = Movie.objects.create(
            title=\"Titanic\", description=\"Drama\", duration=195
        )
        res = self.client.get(MOVIE_URL, {\"title\": \"Av\"})
        serializer = MovieListSerializer(m1)
        serializer2 = MovieListSerializer(m2)
        self.assertIn(serializer.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_genres(self):
        g1 = Genre.objects.create(name=\"Action\")
        g2 = Genre.objects.create(name=\"Comedy\")
        m1 = Movie.objects.create(
            title=\"Movie 1\", description=\"Desc\", duration=100
        )
        m2 = Movie.objects.create(
            title=\"Movie 2\", description=\"Desc\", duration=110
        )
        m1.genres.add(g1)
        m2.genres.add(g2)
        res = self.client.get(MOVIE_URL, {\"genres\": f\"{g1.id}\"})
        serializer = MovieListSerializer(m1)
        serializer2 = MovieListSerializer(m2)
        self.assertIn(serializer.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_actors(self):
        a1 = Actor.objects.create(first_name=\"Tom\", last_name=\"Cruise\")
        a2 = Actor.objects.create(first_name=\"Brad\", last_name=\"Pitt\")
        m1 = Movie.objects.create(
            title=\"Movie 1\", description=\"Desc\", duration=100
        )
        m2 = Movie.objects.create(
            title=\"Movie 2\", description=\"Desc\", duration=110
        )
        m1.actors.add(a1)
        m2.actors.add(a2)
        res = self.client.get(MOVIE_URL, {\"actors\": f\"{a1.id}\"})
        serializer = MovieListSerializer(m1)
        serializer2 = MovieListSerializer(m2)
        self.assertIn(serializer.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
