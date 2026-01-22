from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieSerializer

MOVIE_URL = reverse("cinema:movie-list")

def sample_movie(**params):
    defaults = {
        "title": "Sample Movie",
        "description": "Sample Description",
        "duration": 120,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])

class MovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'test@test.com',
            'testpass123'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_movies(self):
        """Test retrieving a list of movies"""
        sample_movie()
        sample_movie(title="Another Movie")

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all().order_by("id")
        serializer = MovieSerializer(movies, many=True)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        """Test filtering movies by title"""
        movie1 = sample_movie(title="Batman")
        movie2 = sample_movie(title="Superman")
        
        res = self.client.get(MOVIE_URL, {"title": "bat"})
        
        serializer1 = MovieSerializer(movie1)
        serializer2 = MovieSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_genre(self):
        """Test filtering movies by genre"""
        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Drama")
        
        movie1 = sample_movie(title="Action Movie")
        movie1.genres.add(genre1)
        
        movie2 = sample_movie(title="Drama Movie")
        movie2.genres.add(genre2)
        
        movie3 = sample_movie(title="No Genre Movie")

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})
        
        serializer1 = MovieSerializer(movie1)
        serializer2 = MovieSerializer(movie2)
        serializer3 = MovieSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_movies_by_actors(self):
        """Test filtering movies by actors"""
        actor1 = Actor.objects.create(first_name="George", last_name="Clooney")
        actor2 = Actor.objects.create(first_name="Brad", last_name="Pitt")
        
        movie1 = sample_movie(title="Oceans 11")
        movie1.actors.add(actor1)
        
        movie2 = sample_movie(title="Troy")
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})
        
        serializer1 = MovieSerializer(movie1)
        serializer2 = MovieSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_movie_detail(self):
        """Test retrieving a movie detail"""
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="SciFi"))
        
        url = detail_url(movie.id)
        res = self.client.get(url)
        
        serializer = MovieSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        """Test that standard users cannot create movies"""
        payload = {
            "title": "Movie",
            "description": "Desc",
            "duration": 100
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            'admin@admin.com',
            'password123'
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        """Test that admin can create movies"""
        payload = {
            "title": "Movie",
            "description": "Desc",
            "duration": 100
        }
        res = self.client.post(MOVIE_URL, payload)
        
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(movie, key))
