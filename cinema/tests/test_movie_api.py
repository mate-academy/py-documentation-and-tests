import io
from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])

class MovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com", "testpass"
        )
        self.admin = get_user_model().objects.create_superuser(
            "admin@test.com", "adminpass"
        )

    def test_list_movies(self):
        sample_movie()
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_title(self):
        m1 = sample_movie(title="Inception")
        m2 = sample_movie(title="Avatar")
        res = self.client.get(MOVIE_URL, {"title": "inception"})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], m1.title)

    def test_filter_movies_by_genres(self):
        genre = Genre.objects.create(name="Sci-Fi")
        m1 = sample_movie(title="Movie 1")
        m1.genres.add(genre)
        sample_movie(title="Movie 2")
        res = self.client.get(MOVIE_URL, {"genres": f"{genre.id}"})
        self.assertEqual(len(res.data), 1)

    def test_filter_movies_by_actors(self):
        actor = Actor.objects.create(first_name="Actor", last_name="1")
        m1 = sample_movie(title="Movie 1")
        m1.actors.add(actor)
        res = self.client.get(MOVIE_URL, {"actors": f"{actor.id}"})
        self.assertEqual(len(res.data), 1)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_movie_forbidden(self):
        self.client.force_authenticate(self.user)
        payload = {"title": "Movie", "description": "D", "duration": 100}
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movie(self):
        self.client.force_authenticate(self.admin)
        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(first_name="Test", last_name="Actor") # Додали актора
        
        buffer = io.BytesIO()
        img = Image.new("RGB", (10, 10))
        img.save(buffer, format="JPEG")
        image_file = SimpleUploadedFile(
            "test.jpg", buffer.getvalue(), content_type="image/jpeg"
        )
        
        payload = {
            "title": "New Movie",
            "description": "Description",
            "duration": 100,
            "genres": [genre.id],
            "actors": [actor.id], # Тепер список не порожній
            "image": image_file,
        }
        res = self.client.post(MOVIE_URL, payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_update_movie(self):
        self.client.force_authenticate(self.admin)
        movie = sample_movie()
        genre = Genre.objects.create(name="Update Genre") # Створюємо жанр
        actor = Actor.objects.create(first_name="Update", last_name="Actor") # Створюємо актора
        
        buffer = io.BytesIO()
        img = Image.new("RGB", (10, 10))
        img.save(buffer, format="JPEG")
        image_file = SimpleUploadedFile(
            "update.jpg", buffer.getvalue(), content_type="image/jpeg"
        )
        
        payload = {
            "title": "Updated Title",
            "description": "Updated description",
            "duration": 120,
            "genres": [genre.id], # Тепер список не порожній
            "actors": [actor.id], # Тепер список не порожній
            "image": image_file,
        }
        res = self.client.put(detail_url(movie.id), payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_delete_movie(self):
        self.client.force_authenticate(self.admin)
        movie = sample_movie()
        res = self.client.delete(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Movie.objects.filter(id=movie.id).exists())
