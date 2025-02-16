import tempfile
import os

import pytest
from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieSerializer,
    MovieListSerializer,
    MovieDetailSerializer
)


MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


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


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    """Return URL for recipe image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        self.movie.image.delete()

    def test_upload_image_to_movie(self):
        """Test uploading an image to movie"""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list(self):
        url = MOVIE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [1],
                    "actors": [1],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regular_user():
    user = get_user_model().objects.create_user(
        email="regular@user.com", password="testpass", is_staff=False
    )
    return user


@pytest.fixture
def staff_user():
    user = get_user_model().objects.create_user(
        email="staff@user.com", password="testpass", is_staff=True
    )
    return user


@pytest.fixture
def api_client_staff(api_client, staff_user):
    api_client.force_authenticate(staff_user)
    return api_client


@pytest.fixture
def api_client_regular(api_client, regular_user):
    api_client.force_authenticate(regular_user)
    return api_client


@pytest.fixture(scope="module")
def movie_list_url():
    return reverse("cinema:movie-list")


@pytest.fixture(scope="function")
def single_movie_url():
    def _movie_url(pk):
        return reverse("cinema:movie-detail", kwargs={"pk": pk})

    return _movie_url


@pytest.fixture(scope="function")
def create_movies():
    genre1 = Genre.objects.create(name="Genre1")
    genre2 = Genre.objects.create(name="Genre2")

    actor1 = Actor.objects.create(first_name="Actor", last_name="One")
    actor2 = Actor.objects.create(first_name="Actor", last_name="Two")

    movie1 = Movie.objects.create(
        title="Title 1",
        description="Desc 1",
        duration=100
    )
    movie2 = Movie.objects.create(
        title="Title 2",
        description="Desc 2",
        duration=120
    )
    movie3 = Movie.objects.create(
        title="Title 3",
        description="Desc 3",
        duration=90
    )

    movie1.genres.add(genre1)
    movie2.genres.add(genre1, genre2)
    movie3.genres.add(genre2)

    movie1.actors.add(actor1)
    movie2.actors.add(actor1, actor2)
    movie3.actors.add(actor2)


@pytest.fixture
def movie_data():
    return {
        "title": "New Movie",
        "description": "New Movie Description",
        "duration": 120,
        "genres": [1],
        "actors": [1],
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "client_fixture, expected_status",
    [
        ("api_client_staff", 200),
        ("api_client_regular", 200),
        ("api_client", 401),
    ],
)
def test_movie_list_get(
        client_fixture,
        expected_status,
        request,
        movie_list_url,
        create_movies
):
    client = request.getfixturevalue(client_fixture)
    response = client.get(movie_list_url)

    assert response.status_code == expected_status
    if response.status_code == 200:
        movies = Movie.objects.all()

        serializer = MovieListSerializer(
            movies,
            many=True,
            context={"request": request}
        )

        assert response.data == serializer.data


@pytest.mark.django_db
@pytest.mark.parametrize(
    "client_fixture, expected_status",
    [
        ("api_client_staff", 201),
        ("api_client_regular", 403),
        ("api_client", 401),
    ],
)
def test_movie_list_post(
        client_fixture,
        expected_status,
        request,
        create_movies,
        movie_data,
        movie_list_url
):
    client = request.getfixturevalue(client_fixture)
    response = client.post(movie_list_url, movie_data)
    assert response.status_code == expected_status

    if expected_status == 201:
        movie = Movie.objects.get(title=movie_data["title"])
        serializer = MovieSerializer(movie, context={"request": request})

        assert response.data == serializer.data


@pytest.mark.django_db
@pytest.mark.parametrize(
    "client_fixture, movie_id, expected_status",
    [
        ("api_client_staff", 1, 200),
        ("api_client_staff", 2, 200),
        ("api_client_staff", 3, 200),
        ("api_client_regular", 1, 200),
        ("api_client_regular", 2, 200),
        ("api_client_regular", 3, 200),
        ("api_client", 1, 401),
        ("api_client", 2, 401),
        ("api_client", 3, 401),
    ],
)
def test_movie_detail_get(
    client_fixture,
        movie_id,
        expected_status,
        request,
        single_movie_url,
        create_movies,
):
    client = request.getfixturevalue(client_fixture)
    response = client.get(single_movie_url(pk=movie_id))

    assert response.status_code == expected_status

    if expected_status == 200:
        movie = Movie.objects.get(id=movie_id)
        serializer = MovieDetailSerializer(movie, context={"request": request})
        assert response.data == serializer.data


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query_params",
    [
        ({"title": "Title 1"}),
        ({"genres": "1"}),
        ({"actors": "2"}),
        ({"title": "Title", "genres": "1"}),
        ({}),
    ],
)
def test_movie_list_filtering(
        api_client_regular,
        movie_list_url,
        create_movies,
        query_params,
        request
):
    queryset = Movie.objects.prefetch_related("genres", "actors")

    if query_params.get("title"):
        queryset = queryset.filter(title__icontains=query_params["title"])

    if query_params.get("genres"):
        genres_ids = [int(id) for id in query_params["genres"].split(",")]
        queryset = queryset.filter(genres__id__in=genres_ids)

    if query_params.get("actors"):
        actors_ids = [int(id) for id in query_params["actors"].split(",")]
        queryset = queryset.filter(actors__id__in=actors_ids)

    serializer = MovieListSerializer(
        queryset.distinct(),
        many=True,
        context={"request": request}
    )

    response = api_client_regular.get(movie_list_url, query_params)

    assert response.status_code == 200

    assert response.data == serializer.data
