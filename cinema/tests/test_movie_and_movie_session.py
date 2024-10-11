import datetime

from django.db.models import Count, F
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.reverse import reverse

from cinema.models import Movie, MovieSession, Actor, Genre, CinemaHall
from cinema.serializers import MovieListSerializer, MovieSessionListSerializer
from user.models import User

MOVIE_LIST_URL = reverse("cinema:movie-list")
MOVIE_SESSION_LIST_URL = reverse("cinema:moviesession-list")


class MovieAndMovieSessionTestCaseForAnonimUser(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_movie_if_anonim_user(self):
        movie_response = self.client.get(MOVIE_LIST_URL)

        self.assertEqual(movie_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_movie_sessions_if_anonim_user(self):
        movie_sessions_response = self.client.get(MOVIE_SESSION_LIST_URL)

        self.assertEqual(
            movie_sessions_response.status_code, status.HTTP_401_UNAUTHORIZED
        )


class MovieAndMovieSessionTestCaseForSimpleUser(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="<EMAIL>",
            password="<PASSWORD>",
        )
        self.client.force_authenticate(user=self.user)

        self.actor_John = Actor.objects.create(
            first_name="John",
            last_name="Doe",
        )
        self.actor_Illia = Actor.objects.create(
            first_name="illia",
            last_name="Doe",
        )

        self.genre_horror = Genre.objects.create(name="horror")
        self.genre_drama = Genre.objects.create(name="drama")

        self.cinema_hall = CinemaHall.objects.create(
            name="Cinema Hall",
            rows=12,
            seats_in_row=4,
        )
        self.movie_vinston = Movie.objects.create(
            title="vinston",
            description="Test movie",
            duration=6,
        )
        self.movie_apalon = Movie.objects.create(
            title="apalon",
            description="Test movie",
            duration=6,
        )
        self.movie_japon = Movie.objects.create(
            title="japon",
            description="Test movie",
            duration=6,
        )

        self.movie_apalon.actors.add(self.actor_John)
        self.movie_apalon.genres.add(self.genre_horror)

        self.movie_vinston.actors.add(self.actor_Illia)
        self.movie_vinston.genres.add(self.genre_drama)

        self.movie_japon.actors.add(self.actor_John)
        self.movie_japon.genres.add(self.genre_drama)

        self.movie_session_2024 = MovieSession.objects.create(
            show_time=datetime.datetime(2024, 1, 1, 12, 0, 0),
            movie=self.movie_apalon,
            cinema_hall=self.cinema_hall,
        )
        self.movie_session_2023 = MovieSession.objects.create(
            show_time=datetime.datetime(2023, 1, 1, 12, 0, 0),
            movie=self.movie_vinston,
            cinema_hall=self.cinema_hall,
        )

    def test_movie_if_simple_user(self):
        movie_response = self.client.get(MOVIE_LIST_URL)

        movies = Movie.objects.all()

        movie_serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(movie_response.status_code, status.HTTP_200_OK)

        self.assertEqual(movie_serializer.data, movie_response.data)

    def test_movie_session_if_simple_user(self):
        movie_sessions_response = self.client.get(MOVIE_SESSION_LIST_URL)

        movie_sessions = (
            MovieSession.objects.all()
            .select_related("movie", "cinema_hall")
            .annotate(
                tickets_available=(
                    F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
                    - Count("tickets")
                )
            )
        )

        movie_session_serializer = MovieSessionListSerializer(movie_sessions, many=True)

        self.assertEqual(movie_sessions_response.status_code, status.HTTP_200_OK)
        self.assertEqual(movie_session_serializer.data, movie_sessions_response.data)

    def test_filter_movie_by_title(self):
        movie_response_apalon = self.client.get(MOVIE_LIST_URL, {"title": "apalon"})
        movie_response_vinston = self.client.get(MOVIE_LIST_URL, {"title": "vinston"})
        movie_response_lolipops = self.client.get(MOVIE_LIST_URL, {"title": "lolipops"})

        movie_serializer_apalon = MovieListSerializer(self.movie_apalon, many=False)
        movie_serializer_vinston = MovieListSerializer(self.movie_vinston, many=False)
        movie_serializer_japon = MovieListSerializer(self.movie_japon, many=False)

        self.assertIn(movie_serializer_apalon.data, movie_response_apalon.data)
        self.assertIn(movie_serializer_vinston.data, movie_response_vinston.data)

        self.assertNotIn(movie_serializer_japon.data, movie_response_apalon.data)
        self.assertNotIn(movie_serializer_apalon.data, movie_response_vinston.data)

        self.assertEqual(movie_response_lolipops.status_code, status.HTTP_200_OK)
        self.assertEqual(movie_response_lolipops.data, [])

    def test_filter_movie_by_actors(self):
        movie_responce_Illia = self.client.get(
            MOVIE_LIST_URL, {"actors": f"{self.actor_Illia.id}"}
        )
        movie_responce_Jonh = self.client.get(
            MOVIE_LIST_URL, {"actors": f"{self.actor_John.id}"}
        )
        movie_responce_qeuty = self.client.get(
            MOVIE_LIST_URL, {"actors": f"918"}
        )

        movie_serializer_Jonh = MovieListSerializer(self.movie_apalon, many=False)
        movie_serializer_Illia = MovieListSerializer(self.movie_vinston, many=False)


        self.assertEqual(
            movie_serializer_Illia.data["actors"],
            movie_responce_Illia.data[0]["actors"],
        )
        self.assertEqual(
            movie_serializer_Jonh.data["actors"], movie_responce_Jonh.data[0]["actors"]
        )

        self.assertNotEqual(
            movie_serializer_Jonh.data["actors"], movie_responce_Illia.data[0]["actors"]
        )

        self.assertEqual(movie_responce_qeuty.status_code, status.HTTP_200_OK)
        self.assertEqual(movie_responce_qeuty.data, [])

    def test_filter_movie_by_genres(self):
        movie_response_horror = self.client.get(
            MOVIE_LIST_URL, {"genres": f"{self.genre_horror.id}"}
        )
        movie_response_drama = self.client.get(
            MOVIE_LIST_URL, {"genres": f"{self.genre_drama.id}"}
        )
        movie_response_something = self.client.get(
            MOVIE_LIST_URL, {"genres": f"89982"}
        )

        movie_serializer_horror = MovieListSerializer(self.movie_apalon, many=False)
        movie_serializer_drama = MovieListSerializer(self.movie_vinston, many=False)

        self.assertEqual(
            movie_serializer_horror.data["genres"],
            movie_response_horror.data[0]["genres"],
        )
        self.assertEqual(
            movie_serializer_drama.data["genres"],
            movie_response_drama.data[0]["genres"],
        )
        self.assertNotEqual(
            movie_serializer_drama.data["genres"],
            movie_response_horror.data[0]["genres"],
        )
        self.assertEqual(movie_response_something.status_code, status.HTTP_200_OK)
        self.assertEqual(movie_response_something.data, [])

    def test_filter_movie_session_by_date(self):
        movie_session_response_2023 = self.client.get(
            MOVIE_SESSION_LIST_URL,
            {
                "date": f"{self.movie_session_2023.show_time.year}-"
                f"{self.movie_session_2023.show_time.month}-"
                f"{self.movie_session_2023.show_time.day}"
            },
        )

        movie_session_response_2024 = self.client.get(
            MOVIE_SESSION_LIST_URL,
            {
                "date": f"{self.movie_session_2024.show_time.year}-"
                f"{self.movie_session_2024.show_time.month}-"
                f"{self.movie_session_2024.show_time.day}"
            },
        )
        movie_session_response_1762 = self.client.get(
            MOVIE_SESSION_LIST_URL,
            {
                "date": "1762-01-01",
            },
        )

        movie_session_serializer_2023 = MovieSessionListSerializer(
            self.movie_session_2023, many=False
        )

        movie_session_serializer_2024 = MovieSessionListSerializer(
            self.movie_session_2024, many=False
        )

        self.assertEqual(
            movie_session_response_2023.data[0]["show_time"],
            movie_session_serializer_2023.data["show_time"],
        )

        self.assertEqual(
            movie_session_response_2024.data[0]["show_time"],
            movie_session_serializer_2024.data["show_time"],
        )

        self.assertNotEqual(
            movie_session_response_2024.data[0]["show_time"],
            movie_session_serializer_2023.data["show_time"],
        )

        self.assertEqual(movie_session_response_1762.status_code, status.HTTP_200_OK)
        self.assertEqual(movie_session_response_1762.data, [])

    def test_filter_movie_session_by_movie_title(self):
        movie_session_response_vinston = self.client.get(
            MOVIE_SESSION_LIST_URL, {"movie": f"{self.movie_session_2023.movie.id}"}
        )
        movie_session_response_apalon = self.client.get(
            MOVIE_SESSION_LIST_URL, {"movie": f"{self.movie_session_2024.movie.id}"}
        )
        movie_session_response_with_doesnt_exist_movie = self.client.get(
            MOVIE_SESSION_LIST_URL, {"movie": "1929323"}
        )

        movie_session_serializer_vinston = MovieSessionListSerializer(
            self.movie_session_2023, many=False
        )

        movie_session_serializer_apalon = MovieSessionListSerializer(
            self.movie_session_2024, many=False
        )

        self.assertEqual(
            movie_session_serializer_vinston.data["id"],
            movie_session_response_vinston.data[0]["id"],
        )
        self.assertEqual(
            movie_session_serializer_apalon.data["id"],
            movie_session_response_apalon.data[0]["id"],
        )
        self.assertNotEqual(
            movie_session_serializer_apalon.data["id"],
            movie_session_response_vinston.data[0]["id"],
        )
        self.assertEqual(movie_session_response_with_doesnt_exist_movie.status_code, status.HTTP_200_OK)
        self.assertEqual(movie_session_response_with_doesnt_exist_movie.data, [])
