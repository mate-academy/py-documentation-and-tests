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
    for i in range(1, 4):
        Movie.objects.create(title=f"Title {i}", description=f"Desc {i}", duration=i)


@pytest.fixture
def movie_data():
    return {
        "title": "New Movie",
        "description": "New Movie Description",
        "duration": 120,
        "genres": [sample_genre().id],
        "actors": [sample_actor().id],
    }


@pytest.mark.django_db
def test_movie_list_get_by_regular(api_client_regular, movie_list_url, create_movies):
    movies = Movie.objects.all()

    response = api_client_regular.get(movie_list_url)

    assert response.status_code == 200
    assert len(response.data) == len(movies)

    for movie_obj, movie_dict in zip(movies, response.data):
        assert movie_dict["title"] == movie_obj.title
        assert movie_dict["description"] == movie_obj.description
        assert movie_dict["duration"] == movie_obj.duration


@pytest.mark.django_db
def test_movie_list_post_by_staff(api_client_staff, movie_data, movie_list_url):
    data = movie_data
    response = api_client_staff.post(movie_list_url, data)
    assert response.status_code == 201
    assert response.data["title"] == data["title"]
    assert Movie.objects.filter(title="New Movie").exists()


@pytest.mark.django_db
def test_movie_list_post_by_regular(api_client_regular, movie_data, movie_list_url):
    data = movie_data
    response = api_client_regular.post(movie_list_url, data)
    assert response.status_code == 403


@pytest.mark.django_db
def test_movie_list_post_by_anonymous(api_client, movie_data, movie_list_url):
    data = movie_data
    response = api_client.post(movie_list_url, data)
    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize(
    "movie_id, expected_title",
    [
        (1, "Title 1"),
        (2, "Title 2"),
        (3, "Title 3"),
    ],
)
def test_movie_detail_get(
    api_client_regular, single_movie_url, create_movies, movie_id, expected_title
):
    response = api_client_regular.get(single_movie_url(pk=movie_id))

    assert response.status_code == 200
    assert response.data["title"] == expected_title
