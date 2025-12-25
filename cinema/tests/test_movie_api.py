# tests/test_movie_api.py
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import Movie, Genre, Actor
from .serializers import MovieListSerializer

MOVIE_URL = reverse('cinema:movie-list')  # Adjust 'cinema' to your app name

def detail_url(movie_id):
    return reverse('cinema:movie-detail', args=[movie_id])

class MovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create Data
        self.genre_action = Genre.objects.create(name="Action")
        self.genre_drama = Genre.objects.create(name="Drama")
        
        self.actor_1 = Actor.objects.create(first_name="Keanu", last_name="Reeves")
        self.actor_2 = Actor.objects.create(first_name="Scarlett", last_name="Johansson")
        
        self.movie1 = Movie.objects.create(
            title="John Wick",
            description="Action movie",
            duration=120
        )
        self.movie1.genres.add(self.genre_action)
        self.movie1.actors.add(self.actor_1)
        
        self.movie2 = Movie.objects.create(
            title="Marriage Story",
            description="Drama movie",
            duration=136
        )
        self.movie2.genres.add(self.genre_drama)
        self.movie2.actors.add(self.actor_2)

    def test_list_movies(self):
        """Test retrieving a list of movies"""
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all().order_by('id')
        serializer = MovieListSerializer(movies, many=True)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Note: Depending on your default ordering, you might need to sort results
        self.assertEqual(res.data['results'], serializer.data)

    def test_filter_movies_by_title(self):
        """Test filtering movies by title"""
        res = self.client.get(MOVIE_URL, {'title': 'John'})
        
        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)
        
        self.assertIn(serializer1.data, res.data['results'])
        self.assertNotIn(serializer2.data, res.data['results'])

    def test_filter_movies_by_genre(self):
        """Test filtering movies by genre ID"""
        res = self.client.get(MOVIE_URL, {'genres': f'{self.genre_drama.id}'})
        
        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)
        
        self.assertIn(serializer2.data, res.data['results'])
        self.assertNotIn(serializer1.data, res.data['results'])

    def test_filter_movies_by_actor(self):
        """Test filtering movies by actor ID"""
        res = self.client.get(MOVIE_URL, {'actors': f'{self.actor_1.id}'})
        
        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)
        
        self.assertIn(serializer1.data, res.data['results'])
        self.assertNotIn(serializer2.data, res.data['results'])

    def test_create_movie_forbidden_for_anon(self):
        """Test that anonymous users cannot create movies"""
        payload = {
            "title": "New Movie",
            "description": "Desc",
            "duration": 90,
            "genres": [self.genre_action.id],
            "actors": [self.actor_1.id]
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_admin(self):
        """Test that admin user can create movies"""
        admin_user = get_user_model().objects.create_superuser(
            'admin@test.com', 'password123'
        )
        self.client.force_authenticate(user=admin_user)
        
        payload = {
            "title": "New Matrix",
            "description": "New Desc",
            "duration": 140,
            "genres": [self.genre_action.id],
            "actors": [self.actor_1.id]
        }
        
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="New Matrix")
        self.assertEqual(movie.duration, 140)
