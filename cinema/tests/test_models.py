from django.test import TestCase
from django.core.exceptions import ValidationError

from cinema.models import CinemaHall, Genre, Actor, Movie, MovieSession, Order, Ticket
from user.models import User


class CinemaHallModelTests(TestCase):
    def test_create_cinema_hall(self):
        hall = CinemaHall.objects.create(name="Hall 1", rows=10, seats_in_row=20)
        self.assertEqual(hall.name, "Hall 1")
        self.assertEqual(hall.rows, 10)
        self.assertEqual(hall.seats_in_row, 20)

    def test_capacity_property(self):
        hall = CinemaHall.objects.create(name="Hall 1", rows=10, seats_in_row=20)
        self.assertEqual(hall.capacity, 200)

    def test_str_representation(self):
        hall = CinemaHall.objects.create(name="Hall 1", rows=10, seats_in_row=20)
        self.assertEqual(str(hall), "Hall 1")


class GenreModelTests(TestCase):
    def test_create_genre(self):
        genre = Genre.objects.create(name="Drama")
        self.assertEqual(genre.name, "Drama")

    def test_str_representation(self):
        genre = Genre.objects.create(name="Comedy")
        self.assertEqual(str(genre), "Comedy")

    def test_unique_name(self):
        Genre.objects.create(name="Drama")
        with self.assertRaises(Exception):
            Genre.objects.create(name="Drama")


class ActorModelTests(TestCase):
    def test_create_actor(self):
        actor = Actor.objects.create(first_name="George", last_name="Clooney")
        self.assertEqual(actor.first_name, "George")
        self.assertEqual(actor.last_name, "Clooney")

    def test_full_name_property(self):
        actor = Actor.objects.create(first_name="George", last_name="Clooney")
        self.assertEqual(actor.full_name, "George Clooney")

    def test_str_representation(self):
        actor = Actor.objects.create(first_name="George", last_name="Clooney")
        self.assertEqual(str(actor), "George Clooney")


class MovieModelTests(TestCase):
    def setUp(self):
        self.genre = Genre.objects.create(name="Drama")
        self.actor = Actor.objects.create(first_name="George", last_name="Clooney")

    def test_create_movie(self):
        movie = Movie.objects.create(
            title="Test Movie",
            description="A test movie",
            duration=120,
        )
        movie.genres.add(self.genre)
        movie.actors.add(self.actor)
        self.assertEqual(movie.title, "Test Movie")
        self.assertEqual(movie.description, "A test movie")
        self.assertEqual(movie.duration, 120)
        self.assertEqual(movie.genres.count(), 1)
        self.assertEqual(movie.actors.count(), 1)

    def test_str_representation(self):
        movie = Movie.objects.create(
            title="Test Movie",
            description="A test movie",
            duration=120,
        )
        self.assertEqual(str(movie), "Test Movie")

    def test_ordering_by_title(self):
        Movie.objects.create(title="Zebra", description="desc", duration=90)
        Movie.objects.create(title="Apple", description="desc", duration=90)
        self.assertEqual(list(Movie.objects.all().values_list("title", flat=True)), ["Apple", "Zebra"])


class MovieSessionModelTests(TestCase):
    def setUp(self):
        self.movie = Movie.objects.create(
            title="Test Movie",
            description="A test movie",
            duration=120,
        )
        self.hall = CinemaHall.objects.create(name="Hall 1", rows=10, seats_in_row=20)

    def test_create_movie_session(self):
        from datetime import datetime
        session = MovieSession.objects.create(
            show_time=datetime(2022, 6, 2, 14, 0, 0),
            movie=self.movie,
            cinema_hall=self.hall,
        )
        self.assertEqual(session.movie, self.movie)
        self.assertEqual(session.cinema_hall, self.hall)

    def test_str_representation(self):
        from datetime import datetime
        session = MovieSession.objects.create(
            show_time=datetime(2022, 6, 2, 14, 0, 0),
            movie=self.movie,
            cinema_hall=self.hall,
        )
        self.assertIn("Test Movie", str(session))

    def test_ordering_by_show_time(self):
        from datetime import datetime
        MovieSession.objects.create(
            show_time=datetime(2022, 6, 2, 14, 0, 0),
            movie=self.movie,
            cinema_hall=self.hall,
        )
        MovieSession.objects.create(
            show_time=datetime(2022, 6, 1, 10, 0, 0),
            movie=self.movie,
            cinema_hall=self.hall,
        )
        sessions = list(MovieSession.objects.all().values_list("show_time", flat=True))
        self.assertEqual(sessions[0].year, 2022)
        self.assertEqual(sessions[0].month, 6)
        self.assertEqual(sessions[0].day, 2)


class OrderModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com", password="testpass123")

    def test_create_order(self):
        order = Order.objects.create(user=self.user)
        self.assertEqual(order.user, self.user)
        self.assertIsNotNone(order.created_at)

    def test_str_representation(self):
        order = Order.objects.create(user=self.user)
        self.assertEqual(str(order), str(order.created_at))


class TicketModelTests(TestCase):
    def setUp(self):
        self.movie = Movie.objects.create(
            title="Test Movie",
            description="A test movie",
            duration=120,
        )
        self.hall = CinemaHall.objects.create(name="Hall 1", rows=10, seats_in_row=20)
        from datetime import datetime
        self.session = MovieSession.objects.create(
            show_time=datetime(2022, 6, 2, 14, 0, 0),
            movie=self.movie,
            cinema_hall=self.hall,
        )
        self.user = User.objects.create_user(email="test@test.com", password="testpass123")
        self.order = Order.objects.create(user=self.user)

    def test_create_valid_ticket(self):
        ticket = Ticket.objects.create(
            movie_session=self.session,
            order=self.order,
            row=5,
            seat=10,
        )
        self.assertEqual(ticket.row, 5)
        self.assertEqual(ticket.seat, 10)

    def test_invalid_row_too_high(self):
        with self.assertRaises(ValidationError):
            Ticket.objects.create(
                movie_session=self.session,
                order=self.order,
                row=11,
                seat=10,
            )

    def test_invalid_row_too_low(self):
        with self.assertRaises(ValidationError):
            Ticket.objects.create(
                movie_session=self.session,
                order=self.order,
                row=0,
                seat=10,
            )

    def test_invalid_seat_too_high(self):
        with self.assertRaises(ValidationError):
            Ticket.objects.create(
                movie_session=self.session,
                order=self.order,
                row=5,
                seat=21,
            )

    def test_invalid_seat_too_low(self):
        with self.assertRaises(ValidationError):
            Ticket.objects.create(
                movie_session=self.session,
                order=self.order,
                row=5,
                seat=0,
            )

    def test_unique_together_constraint(self):
        Ticket.objects.create(
            movie_session=self.session,
            order=self.order,
            row=5,
            seat=10,
        )
        with self.assertRaises(Exception):
            Ticket.objects.create(
                movie_session=self.session,
                order=self.order,
                row=5,
                seat=10,
            )

    def test_str_representation(self):
        ticket = Ticket.objects.create(
            movie_session=self.session,
            order=self.order,
            row=5,
            seat=10,
        )
        self.assertIn("row: 5", str(ticket))
        self.assertIn("seat: 10", str(ticket))
