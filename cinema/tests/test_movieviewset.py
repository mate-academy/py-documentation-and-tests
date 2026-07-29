from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from django.test import TestCase
from django.urls import reverse

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieSerializer, MovieListSerializer, MovieDetailSerializer


class MovieViewsetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("test@mail.com", "testpassword123")
        self.client.force_authenticate(self.user)
        self.movie = Movie.objects.create(title="test movie", description="test movie", duration=30)
        self.actor1 = Actor.objects.create(first_name="Alex", last_name="Jordan")
        self.actor2 = Actor.objects.create(first_name="Michael", last_name="Golden")
        self.genre = Genre.objects.create(name="Fiction")
        self.movie.actors.add(self.actor1, self.actor2)
        self.movie.genres.add(self.genre)


    def test_movie_list(self):
        url = reverse("cinema:movie-list")
        res = self.client.get(url)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)


    def test_movie_retrieve(self):
        movie = Movie.objects.get(title="test movie")
        url = reverse("cinema:movie-detail", args=[movie.id])
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)