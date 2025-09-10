from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
)


def sample_genre(name="Adventure"):
    return Genre.objects.create(name=name)


def sample_actor(first_name="Alice", last_name="Johnson"):
    return Actor.objects.create(first_name=first_name, last_name=last_name)


def sample_movie(**params):
    defaults = {
        "title": "Sample Movie",
        "description": "Sample description",
        "duration": 110,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


MOVIE_URL = reverse("cinema:movie-list")


class MovieViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com", password="testpass"
        )
        self.admin = get_user_model().objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        self.client.force_authenticate(user=self.user)
        self.movie_url = reverse("cinema:movie-list")

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        url = reverse("cinema:movie-detail", args=[movie.id])
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_list_movies(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        res = self.client.get(self.movie_url)

        movies = Movie.objects.all().prefetch_related("genres", "actors")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data if isinstance(res.data, list) else res.data.get("results", res.data)
        self.assertEqual(data, serializer.data)

    def test_filter_movies_by_genres(self):
        genre1 = sample_genre(name="Thriller")
        genre2 = sample_genre(name="Comedy")

        movie1 = sample_movie(title="Seven")
        movie2 = sample_movie(title="The Mask")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(self.movie_url, {"genres": f"{genre1.id}"})

        data = res.data if isinstance(res.data, list) else res.data.get("results", res.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Seven")

    def test_filter_movies_by_title(self):
        sample_movie(title="Arrival")
        sample_movie(title="Blade Runner")

        res = self.client.get(self.movie_url, {"title": "Arrival"})

        data = res.data if isinstance(res.data, list) else res.data.get("results", res.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Arrival")

    def test_filter_movies_by_actors(self):
        actor1 = sample_actor(first_name="Robert", last_name="Downey")
        actor2 = sample_actor(first_name="Chris", last_name="Evans")

        movie1 = sample_movie(title="Captain America")
        movie2 = sample_movie(title="Iron Man")

        movie1.actors.add(actor2)
        movie2.actors.add(actor1)

        res = self.client.get(self.movie_url, {"actors": f"{actor1.id}"})

        data = res.data if isinstance(res.data, list) else res.data.get("results", res.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Iron Man")

    def test_filter_movies_by_multiple_genres(self):
        g1 = sample_genre(name="Sci-Fi")
        g2 = sample_genre(name="Drama")
        g3 = sample_genre(name="Comedy")

        m1 = sample_movie(title="Interstellar")
        m2 = sample_movie(title="The Godfather")
        m3 = sample_movie(title="The Mask")

        m1.genres.add(g1)
        m2.genres.add(g2)
        m3.genres.add(g3)

        res = self.client.get(self.movie_url, {"genres": f"{g1.id},{g2.id}"})
        data = res.data if isinstance(res.data, list) else res.data.get("results", res.data)
        returned_titles = {item["title"] for item in data}
        self.assertSetEqual(returned_titles, {"Interstellar", "The Godfather"})

    def test_filter_movies_by_multiple_actors(self):
        a1 = sample_actor(first_name="Keanu", last_name="Reeves")
        a2 = sample_actor(first_name="Laurence", last_name="Fishburne")
        a3 = sample_actor(first_name="Jim", last_name="Carrey")

        m1 = sample_movie(title="The Matrix")
        m2 = sample_movie(title="John Wick")
        m3 = sample_movie(title="The Mask")

        m1.actors.add(a1, a2)
        m2.actors.add(a1)
        m3.actors.add(a3)

        res = self.client.get(self.movie_url, {"actors": f"{a1.id},{a2.id}"})
        data = res.data if isinstance(res.data, list) else res.data.get("results", res.data)
        returned_titles = {item["title"] for item in data}
        self.assertTrue({"The Matrix", "John Wick"}.issubset(returned_titles))


    def test_update_movie_put_as_admin(self):
        movie = sample_movie(title="Old", description="Old desc", duration=80)
        old_g = sample_genre("OldG")
        old_a = sample_actor("Old", "Actor")
        movie.genres.add(old_g)
        movie.actors.add(old_a)

        new_g1 = sample_genre("NewG1")
        new_a1 = sample_actor("New", "Actor1")

        url = reverse("cinema:movie-detail", args=[movie.id])
        self.client.force_authenticate(user=self.admin)
        payload = {
            "title": "New Title",
            "description": "New desc",
            "duration": 120,
            "genres": [new_g1.id],
            "actors": [new_a1.id],
        }
        res = self.client.put(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        def test_create_movie(self):
            genre = sample_genre()
            actor = sample_actor()
            payload = {
                "title": "Brand New Movie",
                "description": "Fresh plot",
                "duration": 130,
                "genres": [genre.id],
                "actors": [actor.id],
            }

            self.client.force_authenticate(user=self.admin)
            res = self.client.post(self.movie_url, payload)

            self.assertEqual(res.status_code, status.HTTP_201_CREATED)
            self.assertTrue(Movie.objects.filter(title="Brand New Movie").exists())

    def test_partial_update_movie_patch_as_admin(self):
        movie = sample_movie(title="PatchMe", description="D", duration=100)
        g = sample_genre("G")
        a = sample_actor("A", "B")
        movie.genres.add(g)
        movie.actors.add(a)

        url = reverse("cinema:movie-detail", args=[movie.id])
        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(url, {"title": "Patched"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_delete_forbidden_for_regular_user(self):
        movie = sample_movie(title="NoTouch")
        url = reverse("cinema:movie-detail", args=[movie.id])

        # PUT
        res_put = self.client.put(
            url,
            {"title": "Hack", "description": "x", "duration": 10, "genres": [], "actors": []},
            format="json",
        )
        self.assertIn(
            res_put.status_code,
            (status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED),
        )

        # PATCH
        res_patch = self.client.patch(url, {"title": "Hack2"}, format="json")
        self.assertIn(
            res_patch.status_code,
            (status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED),
        )

        # DELETE
        res_delete = self.client.delete(url)
        self.assertIn(
            res_delete.status_code,
            (status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED),
        )

    def test_delete_movie_as_admin(self):
        movie = sample_movie(title="ToDelete")
        url = reverse("cinema:movie-detail", args=[movie.id])

        self.client.force_authenticate(user=self.admin)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Movie.objects.filter(id=movie.id).exists())

    def test_create_movie_forbidden_for_anonymous(self):
        anon = APIClient()  # без аутентифікації
        payload = {
            "title": "Anon Movie",
            "description": "Should fail",
            "duration": 100,
            "genres": [],
            "actors": [],
        }
        res = anon.post(self.movie_url, payload, format="json")
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_update_delete_forbidden_for_anonymous(self):
        movie = sample_movie(title="AnonNoTouch")
        url = reverse("cinema:movie-detail", args=[movie.id])
        anon = APIClient()

        res_put = anon.put(url, {"title": "Hack", "description": "x", "duration": 10, "genres": [], "actors": []}, format="json")
        self.assertIn(res_put.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED))

        res_patch = anon.patch(url, {"title": "Hack2"}, format="json")
        self.assertIn(res_patch.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED))

        res_delete = anon.delete(url)
        self.assertIn(res_delete.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED))