from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


class MovieViewTest(APITestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test_user@user.com",
            password="TestUser123_"
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("cinema:movie-list")

        self.movie = Movie.objects.create(
            title="test_title",
            description="test_description",
            duration=55,
            image=None
        )

        self.genre = Genre.objects.create(name="test_genre")
        self.actor = Actor.objects.create(
            first_name="test_first_name",
            last_name="test_last_name"
        )

        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

        self.movie_1 = Movie.objects.create(
            title="The Dark Knight",
            description="Out of the darkness...comes the Knight.",
            duration=152,
            image=None
        )

        self.genre_1 = Genre.objects.create(name="Thriller")
        self.genre_2 = Genre.objects.create(name="Criminal")
        self.actor_1 = Actor.objects.create(
            first_name="Christian",
            last_name="Bale"
        )

        self.movie_1.genres.add(self.genre_1)
        self.movie_1.actors.add(self.actor_1)

        self.movie_2 = Movie.objects.create(
            title="The Dark Knight Rises",
            description="The return of the legend.",
            duration=164,
            image=None
        )

        self.movie_2.genres.set([self.genre_1, self.genre_2])
        self.movie_2.actors.add(self.actor_1)

    def test_get_movie_list(self) -> None:
        res = self.client.get(self.url)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_get_movie_by_id(self) -> None:
        url = reverse("cinema:movie-detail", args=[self.movie.id])
        res = self.client.get(url)
        serializer = MovieDetailSerializer(self.movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_search_movie_by_title(self) -> None:
        res = self.client.get(self.url, {"title": "kniGhT"})
        titles = [movie["title"] for movie in res.data]

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("The Dark Knight", titles)
        self.assertIn("The Dark Knight Rises", titles)
        self.assertNotIn("test_title", titles)
        self.assertEqual(len(res.data), 2)

    def test_search_movie_by_genre(self) -> None:
        res = self.client.get(self.url, {"genres": str(self.genre.id)})
        titles = [movie["title"] for movie in res.data]

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("test_title", titles)
        self.assertNotIn("The Dark Knight", titles)
        self.assertEqual(len(res.data), 1)

    def test_search_movie_by_multiple_genres(self) -> None:
        res = self.client.get(
            self.url,
            {"genres": f"{self.genre_1.id},{self.genre_2.id}"}
        )
        titles = [movie["title"] for movie in res.data]

        self.assertIn("The Dark Knight", titles)
        self.assertIn("The Dark Knight Rises", titles)
        self.assertNotIn("test_title", titles)
        self.assertEqual(len(res.data), 2)

    def test_search_movie_by_actor(self) -> None:
        res = self.client.get(self.url, {"actors": str(self.actor_1.id)})
        titles = [movie["title"] for movie in res.data]

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("The Dark Knight", titles)
        self.assertIn("The Dark Knight Rises", titles)
        self.assertNotIn("test_title", titles)
        self.assertEqual(len(res.data), 2)

    def test_search_movie_by_title_and_genre_combined(self) -> None:
        res = self.client.get(
            self.url,
            {"title": "Dark Knight", "genres": str(self.genre_2.id)}
        )
        titles = [movie["title"] for movie in res.data]

        self.assertIn("The Dark Knight Rises", titles)
        self.assertNotIn("The Dark Knight", titles)
        self.assertEqual(len(res.data), 1)

    def test_no_search_filter_returns_all(self) -> None:
        res = self.client.get(self.url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)

    def test_filter_with_nonexistent_title_returns_empty(self) -> None:
        res = self.client.get(self.url, {"title": "nonexistent-movie-xyz"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

    def test_filter_with_nonexistent_genre_returns_empty(self) -> None:
        res = self.client.get(self.url, {"genres": "99999"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

    def test_unauthenticated_user_cannot_access(self) -> None:
        self.client.force_authenticate(user=None)
        res = self.client.get(self.url)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
