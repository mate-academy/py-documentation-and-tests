from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieSerializer, MovieDetailSerializer, MovieListSerializer


class AthorizedUsersTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "test@test.com",
            "test123"
        )
        self.client.force_authenticate(self.user)

    def test_items_list(self):
        url = reverse("cinema:movie-list")
        res = self.client.get(url)
        items = Movie.objects.all()
        serializer = MovieListSerializer(items, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_items_retrieve(self):
        genre = Genre.objects.create(
            name="test_genre",
        )

        actor = Actor.objects.create(
            first_name="test_first_name",
            last_name="test_last_name",
        )

        item = Movie.objects.create(
            title="title",
            description="description",
            duration="20"
        )

        item.genres.set([genre])
        item.actors.set([actor])


        url = reverse("cinema:movie-detail", args=[item.id])
        res = self.client.get(url)

        serializer = MovieDetailSerializer(item)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie(self):
        genre = Genre.objects.create(name="test_genre")

        actor = Actor.objects.create(
            first_name="test_first_name",
            last_name="test_last_name",
        )

        payload = {
            "title": "test_title",
            "description": "test_description",
            "duration": 12,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        url = reverse("cinema:movie-list")

        res = self.client.post(
            url,
            payload,
            format="json",
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_201_CREATED,
            res.data,
        )

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])

        self.assertEqual(
            list(movie.genres.all()),
            [genre],
        )
        self.assertEqual(
            list(movie.actors.all()),
            [actor],
        )

    def test_update_movie_not_allowed(self):
        genre = Genre.objects.create(name="test_genre")

        actor = Actor.objects.create(
            first_name="test_first_name",
            last_name="test_last_name",
        )

        movie = Movie.objects.create(
            title="title",
            description="description",
            duration=20,
        )

        movie.actors.add(actor)
        movie.genres.add(genre)

        url = reverse(
            "cinema:movie-detail",
            args=[movie.id],
        )

        payload = {
            "title": "test_edited_title",
            "description": "test_edited_description",
        }

        update_response = self.client.put(
            url,
            data=payload,
            format="json",
        )

        self.assertEqual(
            update_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
            update_response.data,
        )


    def test_delete_movie_not_allowed(self):

        genre = Genre.objects.create(name="test_genre")

        actor = Actor.objects.create(
            first_name="test_first_name",
            last_name="test_last_name",
        )

        movie = Movie.objects.create(
            title="title",
            description="description",
            duration=20,
        )

        movie.actors.add(actor)
        movie.genres.add(genre)

        url = reverse(
            "cinema:movie-detail",
            args=[movie.id],
        )

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class FilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "test123"
        )
        self.client.force_authenticate(self.user)


        self.genre1= Genre.objects.create(
            name="test_genre 1",
        )

        self.actor1 = Actor.objects.create(
            first_name="test_first_name 1",
            last_name="test_last_name 1",
        )

        self.movie1 = Movie.objects.create(
            title="title 1",
            description="description 1",
            duration="20"
        )

        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.genre2= Genre.objects.create(
            name="test_genre 2",
        )

        self.actor2= Actor.objects.create(
            first_name="test_first_name 2",
            last_name="test_last_name 2",
        )

        self.movie2 = Movie.objects.create(
            title="title 2",
            description="description 2",
            duration="30"
        )

        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

    def test_filter_by_title(self):
        url = reverse("cinema:movie-list")

        res = self.client.get(url, {"title": f"{self.movie1.title}"})

        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_by_genres_id(self):
        url = reverse("cinema:movie-list")

        genre_ids = self.movie1.genres.values_list("id", flat=True)

        res = self.client.get(
            url,
            data={
                "genres": ",".join(map(str, genre_ids)),
            },
        )

        serializer = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_by_actors_id(self):
        url = reverse("cinema:movie-list")

        actors_ids = self.movie1.actors.values_list("id", flat=True)

        res = self.client.get(
            url,
            data={
                "actors": ",".join(map(str, actors_ids)),
            },
        )

        serializer = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer.data, res.data)
        self.assertNotIn(serializer2.data, res.data)


class UnauthorizedUsersTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthorized_user_cannot_list(self):
        url = reverse("cinema:movie-list")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)