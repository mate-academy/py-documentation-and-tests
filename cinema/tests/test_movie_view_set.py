import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def img_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


class UnauthenticatedUserTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testtest1221"
        )
        self.movie1 = Movie.objects.create(
            title="test_movie1",
            description="test_description1",
            duration=100,
        )
        self.movie2 = Movie.objects.create(
            title="test_movie2",
            description="test_description2",
            duration=100,
        )
        self.movie3 = Movie.objects.create(
            title="test_movie3",
            description="test_description3",
            duration=100,
        )
        self.client.force_authenticate(self.user)


    def test_movie_list(self):
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filtering_by_title_genre_actors(self):
        def res(param: str):
            return self.client.get(f"{MOVIE_URL}?{param}")

        for data in [self.movie1, self.movie2]:
            genre = Genre.objects.create(name=f"test_genre{data.id}")
            actor = Actor.objects.create(first_name=f"test_first_name{data.id}", last_name=f"test_last_name{data.id}")
            data.genres.set([genre,])
            data.actors.set([actor,])

        res1=res("title=movie1")
        serializer1 = MovieListSerializer(Movie.objects.filter(title__icontains="test_movie1"), many=True)
        self.assertEqual(res1.data, serializer1.data)

        res2=res("genres=1,2")
        serializer2 = MovieListSerializer(Movie.objects.filter(genres__id__in=[1, 2]).distinct(), many=True)
        self.assertEqual(res2.data, serializer2.data)

        res3=res("actors=1")
        serializer3 = MovieListSerializer(Movie.objects.filter(actors__id__in=[1]).distinct(), many=True)
        self.assertEqual(res3.data, serializer3.data)

    def test_movie_retrieve(self):
        res = self.client.get(f"{MOVIE_URL}{self.movie1.id}/")
        serializer = MovieDetailSerializer(self.movie1)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "test_movie2",
            "description": "test_description2",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image_forbidden_for_regular_user(self):
        url = img_upload_url(self.movie1.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

class AdminMovieTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="testtest1221",
            is_staff=True
        )
        self.movie1 = Movie.objects.create(
            title="test_movie1",
            description="test_description1",
            duration=100,
        )
        self.genre1 = Genre.objects.create(name="test_genre1")
        self.actor1 = Actor.objects.create(first_name="test_first_name1", last_name="test_last_name1")
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "test_movie2",
            "description": "test_description2",
            "duration": 100
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        for data_value in payload:
            self.assertEqual(payload[data_value], getattr(movie, data_value))

    def test_create_movie_with_actor_genre(self):
        payload = {
            "title": "test_movie2",
            "description": "test_description2",
            "duration": 100,
            "actors": [self.actor1.id,],
            "genres": [self.genre1.id,],

        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(self.genre1, genres)
        self.assertIn(self.actor1, actors)

    def test_upload_image_available_for_staff(self):
        url = img_upload_url(self.movie1.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
