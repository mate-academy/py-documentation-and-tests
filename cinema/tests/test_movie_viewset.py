import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from user.models import User


pytestmark = pytest.mark.django_db


MOVIE_URL = reverse("cinema:movie-list")


@pytest.fixture
def user():
    return User.objects.create_user(
        email="user@test.com",
        password="testpass123",
    )


@pytest.fixture
def admin():
    return User.objects.create_superuser(
        email="admin@test.com",
        password="adminpass123",
    )


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_client(admin):
    client = APIClient()
    client.force_authenticate(user=admin)
    return client


@pytest.fixture
def genre():
    return Genre.objects.create(name="Action")


@pytest.fixture
def actor():
    return Actor.objects.create(first_name="Tom", last_name="Hanks")


@pytest.fixture
def movie(genre, actor):
    movie = Movie.objects.create(title="Test Movie")
    movie.genres.add(genre)
    movie.actors.add(actor)
    return movie


def test_list_movies(client, movie):
    res = client.get(MOVIE_URL)
    assert res.status_code == status.HTTP_200_OK
    assert len(res.data) >= 1


def test_retrieve_movie(client, movie):
    url = reverse("cinema:movie-detail", args=[movie.id])
    res = client.get(url)
    assert res.status_code == status.HTTP_200_OK
    assert res.data["id"] == movie.id


def test_create_movie_admin(admin_client):
    payload = {"title": "New Movie"}
    res = admin_client.post(MOVIE_URL, payload)
    assert res.status_code == status.HTTP_201_CREATED
    assert Movie.objects.filter(title="New Movie").exists()


def test_create_movie_forbidden(auth_client):
    payload = {"title": "Bad Movie"}
    res = auth_client.post(MOVIE_URL, payload)
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_create_movie_anon(client):
    payload = {"title": "Anon Movie"}
    res = client.post(MOVIE_URL, payload)
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_filter_by_title(client, movie):
    res = client.get(MOVIE_URL, {"title": "Test"})
    assert res.status_code == status.HTTP_200_OK
    assert len(res.data) >= 1


def test_filter_by_genre(client, movie, genre):
    res = client.get(MOVIE_URL, {"genres": genre.id})
    assert res.status_code == status.HTTP_200_OK
    assert len(res.data) >= 1


def test_filter_by_actor(client, movie, actor):
    res = client.get(MOVIE_URL, {"actors": actor.id})
    assert res.status_code == status.HTTP_200_OK
    assert len(res.data) >= 1
