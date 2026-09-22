from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


class UnauthenticatedMovieApiTests(TestCase):
    """Тести для неавторизованого користувача (гостя)"""

    def setUp(self) -> None:
        self.client = APIClient()
        # Створюємо базовий URL для списку фільмів
        self.url = reverse("cinema:movie-list")

    def test_auth_required_for_list(self) -> None:
        """Анонімний користувач не може бачити список (IsAdminOrIfAuthenticatedReadOnly)"""
        res = self.client.get(self.url)
        # Оскільки користувач не авторизований, очікуємо 401 Unauthorized
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    """Тести для звичайного авторизованого користувача"""

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com", password="testpassword123"
        )
        self.client.force_authenticate(self.user)

        # Створюємо тестові жанри та акторів
        self.genre_action = Genre.objects.create(name="Action")
        self.genre_drama = Genre.objects.create(name="Drama")
        self.actor_jack = Actor.objects.create(first_name="Jack", last_name="Nicholson")

        self.movie1 = Movie.objects.create(title="Avatar", duration=120)
        self.movie1.genres.add(self.genre_action)
        self.movie1.actors.add(self.actor_jack)

        self.movie2 = Movie.objects.create(title="Gladiator", duration=150)
        self.movie2.genres.add(self.genre_action)

        self.movie3 = Movie.objects.create(title="Titanic", duration=190)
        self.movie3.genres.add(self.genre_drama)

    def test_movies_list(self) -> None:
        """Перевірка отримання повного списку фільмів"""
        url = reverse("cinema:movie-list")
        res = self.client.get(url)

        # Отримуємо фільми з бази даних з урахуванням prefetch_related
        movies = Movie.objects.prefetch_related("genres", "actors")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_retrieve(self) -> None:
        """Перевірка отримання деталей одного конкретного фільму"""
        url = reverse("cinema:movie-detail", args=[self.movie1.id])
        res = self.client.get(url)

        serializer = MovieDetailSerializer(self.movie1)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self) -> None:
        """Перевірка фільтрації за назвою фільму (icontains)"""
        url = reverse("cinema:movie-list")
        # Передаємо query-параметр ?title=ava
        res = self.client.get(url, {"title": "ava"})

        # Очікуємо, що в базі знайдеться лише Avatar
        movies = Movie.objects.filter(title__icontains="ava")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres(self) -> None:
        """Перевірка фільтрації за ID жанрів (?genres=1,2)"""
        url = reverse("cinema:movie-list")
        # Передаємо ID жанру Action у форматі рядка через кому, як очікує ваш _params_to_ints
        res = self.client.get(url, {"genres": f"{self.genre_action.id}"})

        # Повинні повернутися тільки Avatar та Gladiator (у них жанр Action)
        movies = Movie.objects.filter(genres__id__in=[self.genre_action.id]).distinct()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
