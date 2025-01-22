from django.contrib.auth import get_user_model
from django.db.models import F, Count
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from django.test import TestCase
from cinema.models import MovieSession, Genre, Actor, Movie, CinemaHall
from cinema.serializers import MovieSessionListSerializer, MovieSessionDetailSerializer

MOVIE_SESSION_URL = reverse("cinema:moviesession-list")

def sample_movie_session(**params) -> MovieSession:
    genre1 = Genre.objects.create(name="Drama")
    genre2 = Genre.objects.create(name="Horror")

    actor1 = Actor.objects.create(first_name="Anton", last_name="Tuda")
    actor2 = Actor.objects.create(first_name="Ola", last_name="Suda")

    movie = Movie.objects.create(
        title="Movie Session 1",
        description="Movie Session 1",
        duration=120,
    )
    movie.genres.set([genre1, genre2])
    movie.actors.set([actor1, actor2])

    cinema_hall = CinemaHall.objects.create(
        name="Cinema Hall",
        rows=15,
        seats_in_row=20
    )
    default_data = {
        "show_time": "2024-10-08T13:00:00Z",
        "movie": movie,
        "cinema_hall": cinema_hall,
    }
    default_data.update(params)
    return MovieSession.objects.create(**default_data)

def movie_sessions_all_with_taken_tickets():
    return (
        MovieSession.objects.all()
        .select_related("movie", "cinema_hall")
        .annotate(
            tickets_available=(
                    F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
                    - Count("tickets")
            )
        )
    )

def detail_url(movie_session_id):
    return reverse("cinema:moviesession-detail", args=(movie_session_id,))


class UnauthenticatedMovieSessionApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSessionApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="password",
        )
        self.client.force_authenticate(user=self.user)

    def test_movie_session_list(self):
        sample_movie_session()
        response = self.client.get(MOVIE_SESSION_URL)
        movie_sessions =  (MovieSession.objects.all()
            .select_related("movie", "cinema_hall")
            .annotate(
                tickets_available=(
                        F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
                        - Count("tickets")
                )
            )
        )
        serializer = MovieSessionListSerializer(movie_sessions, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_sessions_date_movie_id(self):
        sample_movie_session()
        response = self.client.get(
            MOVIE_SESSION_URL,
            {
                "date": "2024-10-08",
                "movie": "1"
            }
        )
        movies_sessions = movie_sessions_all_with_taken_tickets()
        serializer = MovieSessionListSerializer(movies_sessions, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_retrieve_movie_session_detail(self):
        movie_session = sample_movie_session()

        url = detail_url(movie_session.id)

        response = self.client.get(url)
        serializer = MovieSessionDetailSerializer(movie_session)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_try_create_movie_session_forbidden(self):
        payload = {
            "show_time": "2024-10-08T13:00:00Z",
            "movie": "movie",
            "cinema_hall": "cinema_hall",
        }
        response = self.client.post(MOVIE_SESSION_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminBusTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test",
            password="adminpassword",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

        self.movie = Movie.objects.create(title="Test Movie", duration=120)
        self.cinema_hall = CinemaHall.objects.create(
            name="Hall 1",
            rows=15,
            seats_in_row=20
        )

    def test_create_movie_session(self):
        payload = {
            "show_time": "2024-10-08T13:00:00Z",
            "movie": self.movie.id,
            "cinema_hall": self.cinema_hall.id,
        }

        response = self.client.post(MOVIE_SESSION_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)

        movie_session = MovieSession.objects.get(pk=response.data["id"])
        for key in payload:
            if key == "show_time":
                expected_datetime = parse_datetime(payload[key])
                self.assertEqual(expected_datetime, getattr(movie_session, key))
            elif key == "movie":
                self.assertEqual(payload[key], movie_session.movie.id)
            elif key == "cinema_hall":
                self.assertEqual(payload[key], movie_session.cinema_hall.id)
            else:
                self.assertEqual(payload[key], getattr(movie_session, key))

    def test_delete_movie_session_not_allowed(self):
        movie_session = sample_movie_session()
        url = detail_url(movie_session.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
