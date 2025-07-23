from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="test12345678",
        )
        self.client.force_authenticate(user=self.user)
        self.genre_one = Genre.objects.create(name="genre_one")
        self.genre_two = Genre.objects.create(name="genre_two")
        self.actor_one = Actor.objects.create(
            first_name="one",
            last_name="actor",
        )
        self.actor_two = Actor.objects.create(
            first_name="two",
            last_name="actor",
        )
        self.movie_one = Movie.objects.create(
            title="movie one",
            description="description one",
            duration=100,
        )
        self.movie_one.genres.set([self.genre_one])
        self.movie_one.actors.set([self.actor_one])
        self.movie_one.save()
        self.movie_two = Movie.objects.create(
            title="movie two",
            description="description two",
            duration=100,
        )
        self.movie_two.genres.set([self.genre_two])
        self.movie_two.actors.set([self.actor_two])
        self.movie_two.save()

    def test_movie_list(self):
        movies = Movie.objects.all()
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(serializer.data, res.data)

    def test_filter_movie_by_title(self):
        search_title = "one"
        movie_search = Movie.objects.filter(title__icontains=search_title)
        res = self.client.get(MOVIE_URL, {"title": search_title})
        serializer = MovieListSerializer(movie_search, many=True)
        self.assertEqual(serializer.data, res.data)

    def test_filter_movie_by_genres(self):
        search_genre = [self.genre_one.id]
        movie_search = Movie.objects.filter(genres__id__in=search_genre)
        res = self.client.get(MOVIE_URL, {"genres": f"{search_genre[0]}"})
        serializer = MovieListSerializer(movie_search, many=True)
        self.assertEqual(serializer.data, res.data)

    def test_filter_movie_by_actors(self):
        search_actor = [self.actor_one.id]
        movie_search = Movie.objects.filter(actors__id__in=search_actor)
        res = self.client.get(MOVIE_URL, {"actors": f"{search_actor[0]}"})
        serializer = MovieListSerializer(movie_search, many=True)
        self.assertEqual(serializer.data, res.data)

    def test_retrieve_movie(self):
        id_movie = self.movie_one.id
        MOVIE_URL_DETAIL = reverse("cinema:movie-detail", kwargs={"pk": id_movie})
        res = self.client.get(MOVIE_URL_DETAIL)
        movie = Movie.objects.get(pk=id_movie)
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(serializer.data, res.data)
