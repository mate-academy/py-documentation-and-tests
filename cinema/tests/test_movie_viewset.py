from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer
from user.models import User

BASE_URL = reverse("cinema:movie-list")
class MovieViewNotAuthenticatedTest(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_connection(self):
        url = reverse("cinema:movie-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 401)


class MovieViewAuthenticatedTest(APITestCase):
    def setUp(self):
        # assuming there is a user in User model
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@gmail.com",
            "123456admin"
        )
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    @classmethod
    def setUpTestData(cls):
        genres = []
        actors = []
        for i in range(10):
            genres.append(Genre.objects.create(
                name=f"{i}",
            ))
        for i in range(10):
            actors.append(Actor.objects.create(
                first_name=f"{i}",
                last_name=f"{i}"
            ))
        for i in range(10):
            movie = Movie.objects.create(
                title=f"{i}",
                description=f"{i}",
                duration=i,
            )
            movie.genres.add(genres[i])
            movie.actors.add(actors[i])

    def test_connection(self):
        res = self.client.get(BASE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_title_get_all_movies(self):
        res = self.client.get(BASE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.data, serializer.data)


    def test_filter_movies_by_title(self):
        res = self.client.get(BASE_URL, {
            "title": "1"
        })
        movies = Movie.objects.filter(title="1")
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres(self):
        res = self.client.get(BASE_URL, {
            "genres": "1"
        })
        movies = Movie.objects.filter(genres="1")
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_actors(self):
        res = self.client.get(BASE_URL, {
            "genres": "1"
        })
        movies = Movie.objects.filter(genres="1")
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.data, serializer.data)



class MovieViewAdminTest(APITestCase):
    def setUp(self):
        # assuming there is a user in User model
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="123456admin",
            is_staff=True
        )
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    @classmethod
    def setUpTestData(cls):
        cls.genres = []
        cls.actors = []
        for i in range(10):
            cls.genres.append(Genre.objects.create(
                name=f"{i}",
            ))
        for i in range(10):
            cls.actors.append(Actor.objects.create(
                first_name=f"{i}",
                last_name=f"{i}"
            ))
        for i in range(10):
            movie = Movie.objects.create(
                title=f"{i}",
                description=f"{i}",
                duration=i,
            )
            movie.genres.add(cls.genres[i])
            movie.actors.add(cls.actors[i])

    def test_create_movie(self):
        payload = {"title": "10", "description": "10", "duration": 10, "genres": [1, 2], "actors": [1, 2]}
        res = self.client.post(BASE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        payload = {"title": "10", "description": "10", "duration": 10}
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))
        self.assertIn(self.actors[1], movie.actors.all())
        self.assertIn(self.genres[1], movie.genres.all())
