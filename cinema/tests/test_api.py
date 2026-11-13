from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor, Order


MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")
GENRE_URL = reverse("cinema:genre-list")
ACTOR_URL = reverse("cinema:actor-list")
CINEMA_HALL_URL = reverse("cinema:cinemahall-list")
ORDER_URL = reverse("cinema:order-list")


def detail_url(kind, movie_id):
    return reverse("cinema:{}-detail".format(kind), args=[movie_id])


class UnauthenticatedTests(TestCase):
    """Test that unauthenticated users cannot access protected endpoints."""

    def setUp(self):
        self.client = APIClient()

    def test_get_movies_requires_auth(self):
        res = self.client.get(MOVIE_URL)
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_create_movie_requires_auth(self):
        res = self.client.post(MOVIE_URL, {"title": "Test"})
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class MovieListApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.genre = Genre.objects.create(name="Drama")
        self.actor = Actor.objects.create(first_name="George", last_name="Clooney")
        self.movie = Movie.objects.create(
            title="Sample movie",
            description="Sample description",
            duration=90,
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_list_movies(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_filter_movies_by_title(self):
        Movie.objects.create(
            title="Another movie",
            description="Another description",
            duration=100,
        )
        res = self.client.get(MOVIE_URL, {"title": "Sample"})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Sample movie")

    def test_filter_movies_by_genre(self):
        genre2 = Genre.objects.create(name="Comedy")
        movie2 = Movie.objects.create(
            title="Comedy movie",
            description="A comedy",
            duration=90,
        )
        movie2.genres.add(genre2)
        res = self.client.get(MOVIE_URL, {"genres": str(self.genre.id)})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Sample movie")

    def test_filter_movies_by_actor(self):
        actor2 = Actor.objects.create(first_name="Brad", last_name="Pitt")
        movie2 = Movie.objects.create(
            title="Brad movie",
            description="A Brad movie",
            duration=90,
        )
        movie2.actors.add(actor2)
        res = self.client.get(MOVIE_URL, {"actors": str(self.actor.id)})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Sample movie")


class MovieDetailApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.genre = Genre.objects.create(name="Drama")
        self.actor = Actor.objects.create(first_name="George", last_name="Clooney")
        self.movie = Movie.objects.create(
            title="Sample movie",
            description="Sample description",
            duration=90,
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_retrieve_movie(self):
        url = detail_url("movie", self.movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Sample movie")
        self.assertEqual(res.data["description"], "Sample description")
        self.assertEqual(res.data["duration"], 90)
        self.assertIn("genres", res.data)
        self.assertIn("actors", res.data)


class MovieCreateApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.admin)
        self.genre = Genre.objects.create(name="Drama")
        self.actor = Actor.objects.create(first_name="George", last_name="Clooney")

    def test_create_movie(self):
        res = self.client.post(MOVIE_URL, {
            "title": "New Movie",
            "description": "New description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, "New Movie")
        self.assertEqual(movie.genres.count(), 1)
        self.assertEqual(movie.actors.count(), 1)


class MovieUpdateApiTests(TestCase):
    """Test that updating movies is not supported."""

    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.admin)
        self.genre = Genre.objects.create(name="Drama")
        self.actor = Actor.objects.create(first_name="George", last_name="Clooney")
        self.movie = Movie.objects.create(
            title="Sample movie",
            description="Sample description",
            duration=90,
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_update_movie_not_supported(self):
        url = detail_url("movie", self.movie.id)
        res = self.client.put(
            url,
            {
                "title": "Updated Movie",
                "description": "Updated description",
                "duration": 120,
                "genres": [self.genre.id],
                "actors": [self.actor.id],
            },
        )
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_partial_update_movie_not_supported(self):
        url = detail_url("movie", self.movie.id)
        res = self.client.patch(url, {"title": "Partially Updated"})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class MovieDeleteApiTests(TestCase):
    """Test that deleting movies is not supported."""

    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.admin)
        self.movie = Movie.objects.create(
            title="Sample movie",
            description="Sample description",
            duration=90,
        )

    def test_delete_movie_not_supported(self):
        url = detail_url("movie", self.movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class UnauthenticatedMovieModifyTests(TestCase):
    """Test that unauthenticated users cannot update or delete movies."""

    def setUp(self):
        self.client = APIClient()
        self.movie = Movie.objects.create(
            title="Sample movie",
            description="Sample description",
            duration=90,
        )

    def test_update_movie_requires_auth(self):
        url = detail_url("movie", self.movie.id)
        res = self.client.put(url, {"title": "Updated"})
        self.assertIn(
            res.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_partial_update_movie_requires_auth(self):
        url = detail_url("movie", self.movie.id)
        res = self.client.patch(url, {"title": "Updated"})
        self.assertIn(
            res.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_delete_movie_requires_auth(self):
        url = detail_url("movie", self.movie.id)
        res = self.client.delete(url)
        self.assertIn(
            res.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )


class GenreApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.admin = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )

    def test_list_genres(self):
        Genre.objects.create(name="Drama")
        Genre.objects.create(name="Comedy")
        res = self.client.get(GENRE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_create_genre_as_admin(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(GENRE_URL, {"name": "Action"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Genre.objects.count(), 1)
        self.assertEqual(Genre.objects.get().name, "Action")

    def test_create_genre_as_regular_user(self):
        res = self.client.post(GENRE_URL, {"name": "Action"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class ActorApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.admin = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )

    def test_list_actors(self):
        Actor.objects.create(first_name="George", last_name="Clooney")
        res = self.client.get(ACTOR_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_create_actor_as_admin(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(ACTOR_URL, {"first_name": "Brad", "last_name": "Pitt"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Actor.objects.count(), 1)

    def test_create_actor_as_regular_user(self):
        res = self.client.post(ACTOR_URL, {"first_name": "Brad", "last_name": "Pitt"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class CinemaHallApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.admin = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )

    def test_list_cinema_halls(self):
        CinemaHall.objects.create(name="Hall 1", rows=10, seats_in_row=20)
        res = self.client.get(CINEMA_HALL_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_create_cinema_hall_as_admin(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(CINEMA_HALL_URL, {"name": "Hall 1", "rows": 10, "seats_in_row": 20})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CinemaHall.objects.count(), 1)

    def test_create_cinema_hall_as_regular_user(self):
        res = self.client.post(CINEMA_HALL_URL, {"name": "Hall 1", "rows": 10, "seats_in_row": 20})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class MovieSessionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.admin = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.movie = Movie.objects.create(
            title="Test Movie",
            description="A test movie",
            duration=120,
        )
        self.hall = CinemaHall.objects.create(name="Hall 1", rows=10, seats_in_row=20)
        self.client.force_authenticate(self.admin)

    def test_list_movie_sessions(self):
        MovieSession.objects.create(
            show_time=datetime(2022, 6, 2, 14, 0, 0),
            movie=self.movie,
            cinema_hall=self.hall,
        )
        res = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_filter_movie_sessions_by_date(self):
        MovieSession.objects.create(
            show_time=datetime(2022, 6, 2, 14, 0, 0),
            movie=self.movie,
            cinema_hall=self.hall,
        )
        MovieSession.objects.create(
            show_time=datetime(2022, 6, 3, 14, 0, 0),
            movie=self.movie,
            cinema_hall=self.hall,
        )
        res = self.client.get(MOVIE_SESSION_URL, {"date": "2022-06-02"})
        self.assertEqual(len(res.data), 1)

    def test_filter_movie_sessions_by_movie(self):
        movie2 = Movie.objects.create(
            title="Another Movie",
            description="Another movie",
            duration=90,
        )
        MovieSession.objects.create(
            show_time=datetime(2022, 6, 2, 14, 0, 0),
            movie=self.movie,
            cinema_hall=self.hall,
        )
        MovieSession.objects.create(
            show_time=datetime(2022, 6, 2, 15, 0, 0),
            movie=movie2,
            cinema_hall=self.hall,
        )
        res = self.client.get(MOVIE_SESSION_URL, {"movie": self.movie.id})
        self.assertEqual(len(res.data), 1)

    def test_create_movie_session_as_admin(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(MOVIE_SESSION_URL, {
            "show_time": "2022-06-02 14:00:00",
            "movie": self.movie.id,
            "cinema_hall": self.hall.id,
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_movie_session_as_regular_user(self):
        self.client.force_authenticate(self.user)
        res = self.client.post(MOVIE_SESSION_URL, {
            "show_time": "2022-06-02 14:00:00",
            "movie": self.movie.id,
            "cinema_hall": self.hall.id,
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class OrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = Movie.objects.create(
            title="Test Movie",
            description="A test movie",
            duration=120,
        )
        self.hall = CinemaHall.objects.create(name="Hall 1", rows=10, seats_in_row=20)
        self.session = MovieSession.objects.create(
            show_time=datetime(2022, 6, 2, 14, 0, 0),
            movie=self.movie,
            cinema_hall=self.hall,
        )

    def test_create_order_with_tickets(self):
        data = {
            "tickets": [
                {"movie_session": self.session.id, "row": 1, "seat": 1},
            ]
        }
        res = self.client.post(ORDER_URL, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()
        self.assertEqual(order.tickets.count(), 1)
        self.assertEqual(order.user, self.user)

    def test_create_order_invalid_seat(self):
        data = {
            "tickets": [
                {"movie_session": self.session.id, "row": 1, "seat": 21},
            ]
        }
        res = self.client.post(ORDER_URL, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_empty_tickets(self):
        data = {
            "tickets": []
        }
        res = self.client.post(ORDER_URL, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_orders(self):
        Order.objects.create(user=self.user)
        res = self.client.get(ORDER_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

    def test_user_cannot_see_other_users_orders(self):
        Order.objects.create(user=self.user)
        other_user = get_user_model().objects.create_user(
            "other@myproject.com", "password"
        )
        Order.objects.create(user=other_user)
        self.client.force_authenticate(other_user)
        res = self.client.get(ORDER_URL)
        self.assertEqual(len(res.data["results"]), 1)
