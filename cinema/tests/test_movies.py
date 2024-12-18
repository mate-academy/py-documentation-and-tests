from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Actor, Movie, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


class MovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@1234test", password="123123123"
        )
        self.superuser = get_user_model().objects.create_superuser(
            email="test3523@test", password="admin12345"
        )
        for i in range(0, 11):
            actor = Actor.objects.create(first_name=f"1{i}", last_name=f"2{i}")
            genre = Genre.objects.create(name=f"10{i}")
            movie = Movie.objects.create(
                title=f"Sample{i}", description="Sampleee", duration=i * 10
            )
            movie.actors.add(actor)
            movie.genres.add(genre)
        Movie.objects.get(id=2).genres.add(Genre.objects.get(id=2))
        Movie.objects.get(id=2).actors.add(Actor.objects.get(id=2))

    def test_deny_access(self):
        res = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res = self.client.post(reverse("cinema:movie-list"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res = self.client.get(reverse("cinema:movie-detail", args=[1]))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res = self.client.get(reverse("cinema:movie-upload-image", args=[1]))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res = self.client.delete(
            reverse(
                "cinema:movie-detail",
                args=[
                    1,
                ],
            )
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_access(self):
        self.client.force_authenticate(self.user)

        res = self.client.get(reverse("cinema:movie-upload-image", args=[1]))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        res = self.client.delete(
            reverse(
                "cinema:movie-detail",
                args=[
                    1,
                ],
            )
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_access(self):
        self.client.force_authenticate(self.superuser)

        res = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.client.get(reverse("cinema:movie-detail", args=[1]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.client.delete(
            reverse(
                "cinema:movie-detail",
                args=[
                    1,
                ],
            )
        )
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_movie_list(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("cinema:movie-list"))

        serializer = MovieListSerializer(Movie.objects.all(), many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_list_with_title_search(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("cinema:movie-list"), {"title": "Sample1"})

        serializer_movies = MovieListSerializer(
            Movie.objects.filter(title__icontains="Sample1"), many=True
        )

        self.assertEqual(res.data, serializer_movies.data)

    def test_movie_list_with_genres_search(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("cinema:movie-list"), {"genres": ["101", "102"]})

        serializer_movies = MovieListSerializer(
            Movie.objects.filter(genres__name__icontains=("101", "102")), many=True
        )
        self.assertEqual(res.data, serializer_movies.data)

    def test_movie_list_with_actors_search(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("cinema:movie-list"), {"actors": 1})

        serializer_movie1 = MovieListSerializer(
            Movie.objects.get(actors__id=1),
        )

        self.assertIn(serializer_movie1.data, res.data)

    def test_create_movie(self):
        data = {
            "id": 700,
            "title": "teeeest",
            "description": "teest12345",
            "duration": 125,
            "genres": 1,
            "actors": 1,
        }

        self.client.force_authenticate(self.user)
        res = self.client.post(reverse("cinema:movie-list"), data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.superuser)
        res = self.client.post(reverse("cinema:movie-list"), data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_movie_detail(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(
            reverse(
                "cinema:movie-detail",
                args=[
                    1,
                ],
            )
        )

        serializer = MovieDetailSerializer(Movie.objects.get(id=1))

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data, serializer.data)
