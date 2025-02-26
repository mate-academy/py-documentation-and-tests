from django.contrib.auth import get_user_model
from django.template.defaultfilters import title
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from django.test import TestCase
from cinema.models import Actor, Genre, Movie
from cinema.serializers import MovieListSerializer

def movie_create(**params):
    defaults = {
        "title": "Lord",
        "description": "Story lords",
        "duration" : 120
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class TestNotAuthenticatedUser(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_un_authorized_list(self):
        res = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)



class TestAuthenticatedUser(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create(
            email="vas@gmail.com",
            password="vas12345"
        )
        self.client.force_authenticate(user=self.user)

    def test_list_movie_allow(self):
        res = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)


    def test_post_not_allow(self):
        data = {
            "title": "New Movie",
            "description": "New description",
            "duration": 90
        }
        res = self.client.post(reverse("cinema:movie-list"), data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_not_allow(self):
        movie = movie_create()

        data = {
            "title": "New title",
            "description": "Updated description",
            "duration": 150
        }
        res = self.client.put(reverse("cinema:movie-detail", args=[movie.id]), data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_not_allow(self):
        movie = movie_create()
        data = {"title": "New title"}
        res = self.client.patch(reverse("cinema:movie-detail", args=[movie.id]), data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_movie_allow(self):
        movie = movie_create()
        res = self.client.get(reverse("cinema:movie-detail", args=[movie.id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], movie.title)

    def test_delete_not_allow(self):
        movie = movie_create()
        res = self.client.delete(reverse("cinema:movie-detail", args=[movie.id]))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


    def test_filter_by_title(self):
        movie1 = movie_create()
        movie_2 = movie_create(title="Movie test",
                               description="Description test",
                               duration=130)
        res = self.client.get(reverse("cinema:movie-list"), {"title": "Lord"})
        serializer_movie_1 = MovieListSerializer(movie1)
        serializer_movie_2 = MovieListSerializer(movie_2)
        self.assertIn(serializer_movie_1.data, res.data)
        self.assertNotIn(serializer_movie_2.data, res.data)


    def test_filter_by_genre(self):
        movie_1 = movie_create()
        movie_2 = movie_create(title="Movie test",
                               description="Description test",
                               duration=130)
        genre_1 = Genre.objects.create(name="ujastic")
        genre_2 = Genre.objects.create(name="horor")
        movie_1.genres.add(genre_1)
        movie_2.genres.add(genre_2)
        res = self.client.get(reverse("cinema:movie-list"), {"genres": genre_1.id})
        serializer_movie_1 = MovieListSerializer(movie_1)
        serializer_movie_2 = MovieListSerializer(movie_2)
        self.assertIn(serializer_movie_1.data, res.data)
        self.assertNotIn(serializer_movie_2.data, res.data)


    def test_filter_by_actors(self):
        movie_1 = movie_create()
        movie_2 = movie_create(title="Movie test",
                               description="Description test",
                               duration=130)
        actor_1 = Actor.objects.create(first_name="Morgan", last_name="Friman")
        actor_2 = Actor.objects.create(first_name="Jason", last_name="Statham")
        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_2)
        res = self.client.get(reverse("cinema:movie-list"), {"actors": movie_2.id})
        serializer_movie_1 = MovieListSerializer(movie_1)
        serializer_movie_2 = MovieListSerializer(movie_2)
        self.assertNotIn(serializer_movie_1.data, res.data)
        self.assertIn(serializer_movie_2.data, res.data)


class TestAdminUserAuthenticated(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@example.com",
            password="admin123",
            is_staff=True,  # Обов'язково адмін
        )
        self.client.force_authenticate(user=self.user)

        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="Bruce", last_name="Willis")

    def test_admin_create_movie(self):
        payload = {
            "title": "Die Hard",
            "description": "A story of a cop fighting terrorists in a skyscraper.",
            "duration": 132,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        url = reverse("cinema:movie-list")
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        res = self.client.post(reverse("cinema:movie-list"), payload)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(movie.title, "Die Hard")
        self.assertIn(self.actor, movie.actors.all())
        self.assertIn(self.genre, movie.genres.all())
