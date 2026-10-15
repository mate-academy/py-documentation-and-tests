from django.contrib.auth import get_user_model

from cinema.models import Movie, Genre, Actor, CinemaHall, MovieSession


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_cinema_hall(**params):
    defaults = {"name": "Sample Cinema Hall", "rows": 44, "seats_in_row": 22}
    defaults.update(params)
    return CinemaHall.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = sample_cinema_hall()
    movie = sample_movie()

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "cinema_hall": cinema_hall,
        "movie": movie,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def sample_user(**params):
    defaults = {
        "email": "user1@test.com",
        "password": "1qazcde3",
    }
    defaults.update(params)
    return get_user_model().objects.create_user(**defaults)


def sample_admin_user(**params):
    defaults = {
        "email": "admin@test.com",
        "password": "1qazcde3",
    }
    defaults.update(params)
    return get_user_model().objects.create_superuser(**defaults)
