from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer
from user.models import User


def create_genre(suffix):
    Genre.objects.create(name=f"Test genre{suffix}")


def create_actor(suffix):
    Actor.objects.create(
        first_name=f"Actorname{suffix}", last_name=f"Actor LastName{suffix}"
    )


def create_movie(suffix=None, genres: list = None, actors: list = None):
    data = {
        "title": f"Title{suffix}",
        "description": "description",
        "duration": 109,
    }
    movie = Movie.objects.create(**data)
    if actors:
        movie.actors.set(actors)
    if genres:
        movie.genres.set(genres)
    return movie


class MovieViewSetTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.url = reverse("cinema:movie-list")

    def test_anon_user_no_access(self):
        response_list = self.client.get(self.url)
        self.assertEqual(
            response_list.status_code, status.HTTP_401_UNAUTHORIZED
        )

        response_create = self.client.post(
            reverse("cinema:movie-list"), data={}
        )
        self.assertEqual(
            response_create.status_code, status.HTTP_401_UNAUTHORIZED
        )

        create_movie()
        response_retrieve = self.client.get(
            reverse("cinema:movie-detail", args=(1,))
        )
        self.assertEqual(
            response_retrieve.status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_auth_user_has_access(self):
        user = User.objects.create_user("User")
        self.client.force_authenticate(user)
        response_list = self.client.get(self.url)
        self.assertEqual(response_list.status_code, status.HTTP_200_OK)

        response_create = self.client.post(
            reverse("cinema:movie-list"),
            data={},
        )
        self.assertEqual(
            response_create.status_code, status.HTTP_403_FORBIDDEN
        )

        movie = create_movie()
        response_retrieve = self.client.get(
            reverse("cinema:movie-detail", args=(1,))
        )
        self.assertEqual(response_retrieve.status_code, status.HTTP_200_OK)

        serializer = MovieDetailSerializer(movie)
        self.assertEqual(response_retrieve.data, serializer.data)

    def test_admin_can_post(self):
        user = User.objects.create_user("User", is_staff=True)
        self.client.force_authenticate(user)
        genre = Genre.objects.create(name="Test genre")
        actor = Actor.objects.create(
            first_name="Actorname", last_name="Actor LastName"
        )
        response_create = self.client.post(
            reverse("cinema:movie-list"),
            data={
                "title": "Title",
                "description": "description",
                "duration": 109,
                "genres": [genre.id],
                "actors": [actor.id],
            },
        )
        self.assertEqual(response_create.status_code, status.HTTP_201_CREATED)

    def test_querry_params_filtering(self):
        user = User.objects.create_user("User")
        self.client.force_authenticate(user)
        for suffix in range(20):
            create_genre(suffix)
            create_actor(suffix)

        for suffix in range(13):
            create_movie(suffix)

        for suffix in range(13, 20):
            create_movie(
                f"{suffix} exciting movie", genres=[1, 2], actors=[17, 6, 9, 4]
            )

        movies = Movie.objects.filter(genres__in=(1, 2)).distinct()
        serializer = MovieListSerializer(movies, many=True)

        response_genre_filter = self.client.get(self.url, data={"genres": "1"})

        response_actor_filter = self.client.get(
            self.url, data={"actors": "6,9"}
        )

        response_title_filter = self.client.get(
            self.url, data={"title": "exciting movie"}
        )

        for response in (
            response_genre_filter,
            response_actor_filter,
            response_title_filter,
        ):
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, serializer.data)
            self.assertEqual(len(response.data), 7)
