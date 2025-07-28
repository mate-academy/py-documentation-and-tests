from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APIClient
from rest_framework import status
from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


MOVIES_LIST_URL = reverse("cinema:movie-list")

def sample_movie(**params) -> Movie:
    defaults = {
        "title": "The Departed",
        "description": "An undercover cop and a mole in the police attempt to identify each other while infiltrating an Irishgang in South Boston.",
        "duration": 151,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)

def detail_movie_url(bus_id):
    return reverse("cinema:movie-detail", args=(bus_id,))

class TestNotAuthenticated(TestCase):

    def setUp(self):
        self.client = APIClient()
    

    def test_list_movies(self):
        res = self.client.get(MOVIES_LIST_URL)
        self.assertEqual(res.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        

class TestAuthenticated(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="testpassword"
        )
        self.client.force_authenticate(self.user)
    

    def test_list_movie(self):
        res = self.client.get(MOVIES_LIST_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
    

    def test_create_movie(self):
        payload = {
            "title": "The Departed",
            "description": "An undercover cop and a mole in the police attempt to identify each other while infiltrating an Irishgang in South Boston.",
            "duration": 151,
        }
        res = self.client.post(MOVIES_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
    

    def test_filtering_movies_by_genre_and_actor(self):
        movie_with_genres_and_actors_1 = sample_movie(title="Something")
        movie_with_genres_and_actors_2 = sample_movie(title="Anything")
        movie_with_genres_and_actors_3 = sample_movie(title="Doesn'tMatter")

        genre_1 = Genre.objects.create(name="Sci-Fi")
        genre_2 = Genre.objects.create(name="Mystery")
        genre_3 = Genre.objects.create(name="Adventure")

        actor_1 = Actor.objects.create(first_name="Jack",
                                     last_name="Nicholson")
        actor_2 = Actor.objects.create(first_name="Leonardo",
                                       last_name="Dicaprio")
        actor_3 = Actor.objects.create(first_name="Matt",
                                       last_name="Damon")
        
        movie_with_genres_and_actors_1.genres.add(genre_1, genre_3)
        movie_with_genres_and_actors_1.actors.add(actor_1, actor_3)
        movie_with_genres_and_actors_2.genres.add(genre_2, genre_3)
        movie_with_genres_and_actors_2.actors.add(actor_2, actor_3)
        movie_with_genres_and_actors_3.genres.add(genre_2)
        movie_with_genres_and_actors_3.actors.add(actor_2)

        serializer_movie_1 = MovieListSerializer(
            movie_with_genres_and_actors_1
        )
        
        serializer_movie_2 = MovieListSerializer(
            movie_with_genres_and_actors_2
        )

        serializer_movie_3 = MovieListSerializer(
            movie_with_genres_and_actors_3
        )


        res_genre = self.client.get(MOVIES_LIST_URL,
                              {"genres":f"{genre_1.id},{genre_3.id}"})
        
        res_actor = self.client.get(MOVIES_LIST_URL,
                                    {"actors":f"{actor_1.id},{actor_3.id}"})
        
        res_title = self.client.get(MOVIES_LIST_URL,
                                    {"title": "Something"})

        self.assertIn(serializer_movie_1.data, res_genre.data)
        self.assertNotIn(serializer_movie_3.data, res_genre.data)

        self.assertIn(serializer_movie_1.data, res_actor.data)
        self.assertNotIn(serializer_movie_3.data, res_actor.data)

        self.assertIn(serializer_movie_1.data, res_title.data)
        self.assertNotIn(serializer_movie_2.data, res_title.data)
        self.assertNotIn(serializer_movie_3.data, res_title.data)
    

    def test_retrieve(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Sci-Fi"))
        movie.actors.add(Actor.objects.create(first_name="Jack",
                                     last_name="Nicholson"))

        res = self.client.get(detail_movie_url(movie.id))

        ser_movie = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, ser_movie.data)


class Test_Is_Authenticated_Admin(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.admin",
            password="admintestpassword",
            is_staff=True
        )
        self.client.force_authenticate(self.user)
    
    def test_create_movie(self):
        payload = {
            "title": "The Departed",
            "description": "An undercover cop and a mole in the police attempt to identify each other while infiltrating an Irishgang in South Boston.",
            "duration": 151,
        }
        res = self.client.post(MOVIES_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        