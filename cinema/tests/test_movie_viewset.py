import tempfile
import os
from PIL import Image
from cinema.models import Actor, Genre, Movie
from cinema.serializers import MovieDetailSerializer, MovieListSerializer
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(django_user_model):
    return django_user_model.objects.create_superuser(
        email="admin@example.com", password="pass123"
    )


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        email="user@example.com", password="pass123"
    )


@pytest.fixture
def sample_movie():
    return Movie.objects.create(title="Test movie", description="desc")


@pytest.fixture
def sample_genre():
    return Genre.objects.create(name="Action")


@pytest.fixture
def sample_actor():
    return Actor.objects.create(name="Tom")


MOVIES_URL = reverse("movie-list")


def detail_url(movie_id):
    return reverse("movie-detail", args=[movie_id])


def upload_image_url(movie_id):
    return reverse("movie-upload-image", args=[movie_id])


# -----------------------------------
# LIST / RETRIEVE / CREATE
# -----------------------------------


@pytest.mark.django_db
def test_list_movies(api_client, sample_movie):
    res = api_client.get(MOVIES_URL)
    movies = Movie.objects.all()
    serializer = MovieListSerializer(movies, many=True)

    assert res.status_code == status.HTTP_200_OK
    assert res.data == serializer.data


@pytest.mark.django_db
def test_retrieve_movie(api_client, sample_movie):
    url = detail_url(sample_movie.id)
    res = api_client.get(url)

    serializer = MovieDetailSerializer(sample_movie)

    assert res.status_code == status.HTTP_200_OK
    assert res.data == serializer.data


@pytest.mark.django_db
def test_create_movie_admin_only(api_client, admin_user):
    api_client.force_authenticate(admin_user)

    payload = {"title": "New movie", "description": "text"}
    res = api_client.post(MOVIES_URL, payload)

    assert res.status_code == status.HTTP_201_CREATED
    assert Movie.objects.filter(title="New movie").exists()


@pytest.mark.django_db
def test_create_movie_forbidden_for_user(api_client, user):
    api_client.force_authenticate(user)

    payload = {"title": "Forbidden", "description": "text"}
    res = api_client.post(MOVIES_URL, payload)

    assert res.status_code == status.HTTP_403_FORBIDDEN


# -----------------------------------
# FILTERS
# -----------------------------------


@pytest.mark.django_db
def test_filter_by_title(api_client):
    movie_match = Movie.objects.create(title="Batman", description="desc")
    Movie.objects.create(title="Superman", description="desc")

    res = api_client.get(MOVIES_URL, {"title": "bat"})

    assert res.status_code == 200
    assert len(res.data) == 1
    assert res.data[0]["id"] == movie_match.id


@pytest.mark.django_db
def test_filter_by_genres(api_client, sample_genre):
    movie = Movie.objects.create(title="Test", description="desc")
    movie.genres.add(sample_genre)

    Movie.objects.create(title="Other", description="desc")

    res = api_client.get(MOVIES_URL, {"genres": str(sample_genre.id)})

    assert len(res.data) == 1
    assert res.data[0]["id"] == movie.id


@pytest.mark.django_db
def test_filter_by_actors(api_client, sample_actor):
    movie = Movie.objects.create(title="Test", description="desc")
    movie.actors.add(sample_actor)

    Movie.objects.create(title="Other", description="desc")

    res = api_client.get(MOVIES_URL, {"actors": str(sample_actor.id)})

    assert len(res.data) == 1
    assert res.data[0]["id"] == movie.id


# -----------------------------------
# SERIALIZER CLASS SELECTION
# -----------------------------------


@pytest.mark.django_db
def test_serializer_for_list(api_client):
    view = reverse("movie-list")
    res = api_client.get(view)
    assert res.status_code == 200  # И сам факт, что list → MovieListSerializer


@pytest.mark.django_db
def test_serializer_for_retrieve(api_client, sample_movie):
    res = api_client.get(detail_url(sample_movie.id))

    # Проверка структуры — MovieDetailSerializer содержит больше полей
    assert "description" in res.data
    assert res.status_code == 200


# -----------------------------------
# IMAGE UPLOAD
# -----------------------------------


@pytest.mark.django_db
def test_upload_image_success(api_client, admin_user, sample_movie):
    """Admin can upload image"""
    api_client.force_authenticate(admin_user)

    url = upload_image_url(sample_movie.id)

    # создаём временный файл
    with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp_file:
        image = Image.new("RGB", (10, 10))
        image.save(tmp_file, format="JPEG")
        tmp_file.seek(0)

        res = api_client.post(url, {"image": tmp_file}, format="multipart")

    assert res.status_code == status.HTTP_200_OK
    sample_movie.refresh_from_db()
    assert sample_movie.image


@pytest.mark.django_db
def test_upload_image_forbidden_for_user(api_client, user, sample_movie):
    api_client.force_authenticate(user)

    url = upload_image_url(sample_movie.id)

    res = api_client.post(url, {})
    assert res.status_code == status.HTTP_403_FORBIDDEN
