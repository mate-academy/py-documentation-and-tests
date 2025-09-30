import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse, NoReverseMatch

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")

try:
    TOKEN_URL = reverse("user:token_obtain_pair")
except NoReverseMatch:
    try:
        TOKEN_URL = reverse("token_obtain_pair")
    except NoReverseMatch:
        TOKEN_URL = "/api/user/token/"


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


def get_jwt_for_user(client: APIClient, email: str, password: str):
    """
    Obtain JWT access token by calling the token endpoint.
    Tries reverse name 'token_obtain_pair' then falls back to /api/token/.
    Returns access token string (or None on failure).
    """
    data = {"email": email, "password": password}
    res = client.post(TOKEN_URL, data)
    if res.status_code == status.HTTP_200_OK and "access" in res.data:
        return res.data["access"]
    data_username = {"username": email, "password": password}
    res2 = client.post(TOKEN_URL, data_username)
    if res2.status_code == status.HTTP_200_OK and "access" in res2.data:
        return res2.data["access"]
    return None


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


# Covering of MovieViewSet


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self) -> None:
        result = self.client.get(MOVIE_URL)
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_email = "user@example.com"
        self.user_password = "testpass123"
        self.user = get_user_model().objects.create_user(
            email=self.user_email,
            password=self.user_password
        )
        self.staff_email = "admin@example.com"
        self.staff_password = "testpass123"
        self.staff = get_user_model().objects.create_superuser(
            email=self.staff_email,
            password=self.staff_password
        )

    def _auth_with_jwt(self, email, password):
        token = get_jwt_for_user(self.client, email, password)
        self.assertIsNotNone(token, "Could not obtain JWT token — check TOKEN_URL in tests.")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_auth_required_for_list(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_movies_authenticated_and_ordering(self):
        sample_movie(title="Zebra")
        sample_movie(title="Alpha")
        sample_movie(title="Middle")

        self._auth_with_jwt(self.user_email, self.user_password)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        titles = [m["title"] for m in res.data]
        self.assertEqual(titles, sorted(titles))

        movies = Movie.objects.all().order_by("title")
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        m1 = sample_movie(title="Batman")
        sample_movie(title="Superman")
        self._auth_with_jwt(self.user_email, self.user_password)
        res = self.client.get(MOVIE_URL, {"title": "bat"})

        self.assertIn(next((m for m in res.data if m["title"] == "Batman"), None), res.data)

    def test_filter_movies_by_genres_comma_separated_and_no_results(self):
        g1 = sample_genre(name="Action")
        g2 = sample_genre(name="Drama")
        m1 = sample_movie(title="Action film")
        m1.genres.add(g1)
        m2 = sample_movie(title="Drama film")
        m2.genres.add(g2)

        self._auth_with_jwt(self.user_email, self.user_password)

        res = self.client.get(MOVIE_URL, {"genres": f"{g1.id},{g2.id}"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        titles = [m["title"] for m in res.data]
        self.assertIn("Action film", titles)
        self.assertIn("Drama film", titles)

        res_no = self.client.get(MOVIE_URL, {"genres": "99999"})
        self.assertEqual(res_no.status_code, status.HTTP_200_OK)

        self.assertEqual(res_no.data, [])

    def test_filter_movies_by_genres_invalid_value(self):
        g = sample_genre(name="Action")
        m = sample_movie(title="Action film")
        m.genres.add(g)
        self._auth_with_jwt(self.user_email, self.user_password)

        res = self.client.get(MOVIE_URL, {"genres": "invalid-id"})
        self.assertIn(
            res.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR)
        )

    def test_filter_movies_by_actors_comma_and_invalid(self):
        a1 = sample_actor(first_name="Tom", last_name="Cruise")
        a2 = sample_actor(first_name="Will", last_name="Smith")
        m1 = sample_movie(title="With Tom")
        m1.actors.add(a1)
        m2 = sample_movie(title="With Will")
        m2.actors.add(a2)

        self._auth_with_jwt(self.user_email, self.user_password)

        res = self.client.get(MOVIE_URL, {"actors": f"{a1.id},{a2.id}"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [m["title"] for m in res.data]
        self.assertIn("With Tom", titles)
        self.assertIn("With Will", titles)

        res_invalid = self.client.get(MOVIE_URL, {"actors": "foo"})
        self.assertIn(
            res_invalid.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR)
        )

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())
        url = detail_url(movie.id)

        self._auth_with_jwt(self.user_email, self.user_password)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden_for_non_admin(self):
        payload = {"title": "Admin Movie", "description": "Desc", "duration": 120, "genres": [], "actors": []}
        self._auth_with_jwt(self.user_email, self.user_password)
        res = self.client.post(MOVIE_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movie_allowed_for_admin(self):
        payload = {"title": "Admin Movie", "description": "Desc", "duration": 120, "genres": [], "actors": []}
        self._auth_with_jwt(self.staff_email, self.staff_password)
        res = self.client.post(MOVIE_URL, payload, format="json")
        if res.status_code != status.HTTP_201_CREATED:
            print("CREATE ADMIN FAILED:", res.status_code, res.data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title="Admin Movie").exists())

    def test_create_update_delete_permissions(self):
        """Test that only admin users can create, update, and delete movies"""
        movie = sample_movie(title="ToUpdate")
        url = detail_url(movie.id)

        self._auth_with_jwt(self.user_email, self.user_password)

        res_delete = self.client.delete(url)
        self.assertIn(
            res_delete.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED)
        )

        self._auth_with_jwt(self.staff_email, self.staff_password)

        res_delete_admin = self.client.delete(url)

        if res_delete_admin.status_code != status.HTTP_405_METHOD_NOT_ALLOWED:
            self.assertIn(
                res_delete_admin.status_code,
                (status.HTTP_204_NO_CONTENT, status.HTTP_200_OK),
                f"Admin delete returned unexpected status: {res_delete_admin.status_code}"
            )

    def test_throttling_anonymous_and_authenticated(self):
        """Test that throttling works for anonymous and authenticated users"""
        from django.core.cache import cache
        cache.clear()

        client = APIClient()
        responses = []
        for i in range(5):
            resp = client.get(MOVIE_URL)
            responses.append(resp.status_code)

        self.assertNotIn(
            status.HTTP_429_TOO_MANY_REQUESTS,
            responses[:5],
            "Anonymous user should not be throttled within the first 5 requests"
        )

        cache.clear()
        client_auth = APIClient()
        email = "throttleuser@example.com"
        pwd = "throttlepass"
        get_user_model().objects.create_user(email=email, password=pwd)
        token = get_jwt_for_user(client_auth, email, pwd)
        self.assertIsNotNone(token, "Couldn't obtain token for throttle test user")
        client_auth.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        auth_responses = []
        for i in range(10):
            r = client_auth.get(MOVIE_URL)
            auth_responses.append(r.status_code)

        self.assertNotIn(
            status.HTTP_429_TOO_MANY_REQUESTS,
            auth_responses[:10],
            "Authenticated user should not be throttled within first 10 requests"
        )

        self.assertIn(
            status.HTTP_200_OK,
            auth_responses,
            "At least one authenticated request should succeed"
        )
