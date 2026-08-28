from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer

LIST_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", kwargs={"pk": movie_id})


def create_movie(**data):
    defaults = {
        "title": "Test Movie",
        "description": "Test Description",
        "duration": 100,
    }
    defaults.update(data)
    return Movie.objects.create(**defaults)


def test_data():
    return {
        "title": "Test Movie",
        "description": "Test Description",
        "duration": 99,
    }


class UserUnauthenticatedTest(APITestCase):
    def setUp(self):
        super().setUp()
        self.movie1 = create_movie()

    def test_all_methods_forbidden(self):
        data = {
            "title": "Test Movie2",
            "description": "Test Description2",
            "duration": 111,
        }
        list_response = self.client.get(LIST_URL)
        retrieve_response = self.client.get(detail_url(self.movie1.id))
        create_response = self.client.post(LIST_URL, test_data())
        update_response = self.client.put(
            detail_url(self.movie1.id), test_data()
        )
        partial_update_response = self.client.patch(
            detail_url(self.movie1.id), {"title": test_data()["title"]}
        )
        delete_response = self.client.delete(detail_url(self.movie1.id))
        self.assertEqual(
            list_response.status_code, status.HTTP_401_UNAUTHORIZED
        )
        self.assertEqual(
            retrieve_response.status_code, status.HTTP_401_UNAUTHORIZED
        )
        self.assertEqual(
            create_response.status_code, status.HTTP_401_UNAUTHORIZED
        )
        self.assertEqual(
            update_response.status_code, status.HTTP_401_UNAUTHORIZED
        )
        self.assertEqual(
            partial_update_response.status_code, status.HTTP_401_UNAUTHORIZED
        )
        self.assertEqual(
            delete_response.status_code, status.HTTP_401_UNAUTHORIZED
        )


class UserAuthenticatedTest(APITestCase):
    def setUp(self):
        super().setUp()
        user = get_user_model().objects.create_user(
            email="user@example.com",
            password="test_password",
        )
        self.client.force_authenticate(user=user)
        self.movie1 = create_movie()
        self.movie2 = create_movie()

    def test_list(self):
        res = self.client.get(LIST_URL)
        movies = Movie.objects.all()
        movies_serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, movies_serializer.data)

    def test_list_filter(self):
        actor = Actor.objects.create(first_name="Test", last_name="actor")
        self.movie1.actors.add(actor)
        movie1_serializer = MovieListSerializer(self.movie1)

        genre = Genre.objects.create(name="Test genre")
        self.movie2.genres.add(genre)
        movie2_serializer = MovieListSerializer(self.movie2)

        title = "Cinderella"
        self.movie3 = create_movie(title=title)
        movie3_serializer = MovieListSerializer(self.movie3)

        res = self.client.get(LIST_URL, {"actors": f"{actor.id}"})

        self.assertIn(movie1_serializer.data, res.data)
        self.assertNotIn(movie2_serializer.data, res.data)
        self.assertNotIn(movie3_serializer.data, res.data)
        self.assertEqual(len(res.data), 1)

        res = self.client.get(LIST_URL, {"genres": f"{genre.id}"})

        self.assertNotIn(movie1_serializer.data, res.data)
        self.assertIn(movie2_serializer.data, res.data)
        self.assertNotIn(movie3_serializer.data, res.data)
        self.assertEqual(len(res.data), 1)

        res = self.client.get(LIST_URL, {"title": f"{title}"})

        self.assertNotIn(movie1_serializer.data, res.data)
        self.assertNotIn(movie2_serializer.data, res.data)
        self.assertIn(movie3_serializer.data, res.data)
        self.assertEqual(len(res.data), 1)

    def test_retrieve(self):
        serializer = MovieListSerializer(self.movie1)
        res = self.client.get(detail_url(self.movie1.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_particular_methods_forbidden(self):
        create_response = self.client.post(LIST_URL, test_data())
        update_response = self.client.put(
            detail_url(self.movie1.id), test_data()
        )
        partial_update_response = self.client.patch(
            detail_url(self.movie1.id), {"title": test_data()["title"]}
        )
        delete_response = self.client.delete(detail_url(self.movie1.id))
        self.assertEqual(
            create_response.status_code, status.HTTP_403_FORBIDDEN
        )
        self.assertEqual(
            update_response.status_code, status.HTTP_403_FORBIDDEN
        )
        self.assertEqual(
            partial_update_response.status_code, status.HTTP_403_FORBIDDEN
        )
        self.assertEqual(
            delete_response.status_code, status.HTTP_403_FORBIDDEN
        )


class AdminUserTest(APITestCase):
    def setUp(self):
        super().setUp()
        user = get_user_model().objects.create_user(
            email="user@example.com",
            password="test_password",
            is_staff=True,
        )
        self.client.force_authenticate(user=user)
        self.movie1 = create_movie()
        self.movie2 = create_movie()

    def test_create(self):
        res = self.client.post(LIST_URL, test_data())

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(pk=res.data["id"])

        for key, value in test_data().items():
            with self.subTest(key=key):
                self.assertEqual(value, getattr(movie, key))

    def test_particular_methods_forbidden(self):
        update_response = self.client.put(
            detail_url(self.movie1.id), test_data()
        )
        partial_update_response = self.client.patch(
            detail_url(self.movie1.id), {"title": test_data()["title"]}
        )
        delete_response = self.client.delete(detail_url(self.movie1.id))
        self.assertEqual(
            update_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.assertEqual(
            partial_update_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            delete_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
