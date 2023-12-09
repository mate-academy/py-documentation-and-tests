import os
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer
from cinema_service.settings import MEDIA_ROOT


MOVIE_URL = reverse("cinema:movie-list")

def detail_url(movie_id: int) -> str:
    return reverse("cinema:movie-detail", args=[movie_id])

def upload_image_url(movie_id: int) -> str:
    return reverse("cinema:movie-upload-image", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Test Movie",
        "description": "Movie for Tests",
        "duration": 100,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)



class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)

    def test_list_movie(self):
        sample_movie(title="Test Movie 1")
        movie_with_genres = sample_movie(title="Test Movie 2")
        movie_with_actors = sample_movie(title="Test Movie 3")

        genre1 = Genre.objects.create(name="Horror")
        genre2 = Genre.objects.create(name="Thriller")

        actor1 = Actor.objects.create(first_name="Test", last_name="One")
        actor2 = Actor.objects.create(first_name="Test", last_name="Two")

        movie_with_genres.genres.add(genre1, genre2)
        movie_with_actors.actors.add(actor1, actor2)


        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_filter_by_title(self):
        movie1 = sample_movie(title="Test Movie title1")
        movie2 = sample_movie(title="Test Movie title2")

        response = self.client.get(MOVIE_URL, {"title": "title1",})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)
    
    def test_movie_filter_by_genres(self):
        movie1 = sample_movie(title="Test Movie 1")
        movie2 = sample_movie(title="Test Movie 2")
        movie3 = sample_movie(title="Test Movie 3")

        genre1 = Genre.objects.create(name="Horror")
        genre2 = Genre.objects.create(name="Thriller")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        response = self.client.get(MOVIE_URL, {"genres": f"{genre1.pk},{genre2.pk}",})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)



    def test_movie_filter_by_actors(self):
        movie1 = sample_movie(title="Test Movie 1")
        movie2 = sample_movie(title="Test Movie 2")
        movie3 = sample_movie(title="Test Movie 3")

        actor1 = Actor.objects.create(first_name="Test", last_name="One")
        actor2 = Actor.objects.create(first_name="Test", last_name="Two")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        response = self.client.get(MOVIE_URL, {"actors": f"{actor1.pk},{actor2.pk}",})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.actors.add(
            Actor.objects.create(first_name="Test", last_name="One")
        )
        movie.genres.add(
            Genre.objects.create(name="Horror")
        )

        url = detail_url(movie.pk)
        response = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_upload_image_forbidden(self):
        movie = sample_movie()

        payload = {
            "image": SimpleUploadedFile(
                name="test_image.png",
                content=open(
                    os.path.join(MEDIA_ROOT, "test_image.png"), "rb"
                ).read(),
                content_type="image/png",
            )
        }

        response = self.client.post(upload_image_url(movie.pk), payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test Movie",
            "description": "Movie for Tests",
            "duration": 100,
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_movie_forbidden(self):
        movie = sample_movie()
        payload = {
            "title": "New Movie Title",
            "description": "Another Movie for Tests",
            "duration": 200,
        }

        response = self.client.put(detail_url(movie.pk), payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_partial_update_movie_forbidden(self):
        movie = sample_movie()
        payload = {
            "title": "New Movie Title",
        }

        response = self.client.patch(detail_url(movie.pk), payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_delete_movie_forbidden(self):
        movie = sample_movie()

        response = self.client.delete(detail_url(movie.pk))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)
    
    def test_create_movie_forbidden(self):
        actor1 = Actor.objects.create(first_name="Test", last_name="One")
        actor2 = Actor.objects.create(first_name="Test", last_name="Two")
        genre1 = Genre.objects.create(name="Horror")
        genre2 = Genre.objects.create(name="Thriller")
        payload = {
            "title": "Test Movie",
            "description": "Movie for Tests",
            "duration": 100,
            "genres": [genre1.pk, genre2.pk],
            "actors": [actor1.pk, actor2.pk],
        }

        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(pk=response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        for key in ("title", "description", "duration"):
            self.assertEqual(payload[key], getattr(movie, key))
        
        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 2)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)
    
    def test_movie_upload_image(self):
        movie = sample_movie()

        payload = {
            "image": SimpleUploadedFile(
                name="test_image.png",
                content=open(
                    os.path.join(MEDIA_ROOT, "test_image.png"), "rb"
                ).read(),
                content_type="image/png",
            )
        }

        response = self.client.post(upload_image_url(movie.pk), payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(movie.image)
