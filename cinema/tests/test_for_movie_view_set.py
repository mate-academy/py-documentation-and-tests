from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.contrib.auth import get_user_model

from cinema.models import Genre, Actor, Movie
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse('cinema:movie-list')


def detail_url(movie_id):
    return reverse('cinema:movie-detail', args=[movie_id])


class MovieViewSetTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'testuser',
            'password123'
        )
        self.client.force_authenticate(self.user)

        self.genre = Genre.objects.create(name='Action')
        self.actor = Actor.objects.create(first_name="John", last_name="Smith")
        self.movie = Movie.objects.create(
            title='Test Movie',
            description='Test Description',
            duration=120
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_list_movies(self):
        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie(self):
        """Test creating a movie"""
        payload = {
            'title': 'New Movie',
            'description': 'New Description',
            'duration': 150,
            'genres': [self.genre.id],
            'actors': [self.actor.id]
        }
        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=response.data['id'])
        for key in payload.keys():
            if key in ['genres', 'actors']:
                self.assertEqual(
                    list(getattr(movie, key).values_list('id', flat=True)),
                    payload[key]
                )
            else:
                self.assertEqual(getattr(movie, key), payload[key])

    def test_retrieve_movie(self):
        """Test retrieving a movie"""
        url = detail_url(self.movie.id)
        response = self.client.get(url)
        serializer = MovieDetailSerializer(self.movie)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_update_movie(self):
        """Test updating a movie"""
        payload = {'title': 'Updated Title'}
        url = detail_url(self.movie.id)
        response = self.client.patch(url, payload)
        self.movie.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.movie.title, payload['title'])

    def test_filter_movies_by_title(self):
        """Test filtering movies by title"""
        response = self.client.get(MOVIE_URL, {'title': 'Test'})
        serializer = MovieListSerializer(self.movie)
        self.assertIn(serializer.data, response.data)

    def test_filter_movies_by_genres(self):
        """Test filtering movies by genres"""
        response = self.client.get(MOVIE_URL, {'genres': self.genre.id})
        serializer = MovieListSerializer(self.movie)
        self.assertIn(serializer.data, response.data)

    def test_filter_movies_by_actors(self):
        """Test filtering movies by actors"""
        response = self.client.get(MOVIE_URL, {'actors': self.actor.id})
        serializer = MovieListSerializer(self.movie)
        self.assertIn(serializer.data, response.data)
