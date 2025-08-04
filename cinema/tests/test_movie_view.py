
from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import  status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import  MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


# def generate_image_file():
#     file = BytesIO()
#     image = Image.new('RGB', (100, 100), color='red')
#     image.save(file, 'JPEG')
#     file.name = 'test.jpg'
#     file.seek(0)
#     return file

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))

def detail_view_image(movie_id):
    return reverse("cinema:movie-upload-image", args=(movie_id,))

def sample_movie(**params):
    defaults = {
        "title": "Movie Title",
        "description": "description",
        "duration": 5,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedNonAdminMovieViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="<EMAIL>",
            password="<PASSWORD>",
        )
        self.client.force_authenticate(user=self.user)

    def test_movies_list(self):
        sample_movie()
        movie_with_actors = sample_movie()
        movie_with_genres = sample_movie()

        genre1 = Genre.objects.create(name="Genre1")
        actor = Actor.objects.create(first_name="ActorFirstName", last_name="ActorLastName")

        movie_with_genres.genres.add(genre1)
        movie_with_actors.actors.add(actor)

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movies_filter_by_genres(self):
        movie_without_genres = sample_movie()
        movie_with_genre_1 = sample_movie(title="MovieWithGenres1")
        movie_with_genre_2 = sample_movie(title="MovieWithGenres2")
        movie_with_genre_3 = sample_movie(title="MovieWithGenres3")

        genre_1 = Genre.objects.create(name="Genre1")
        genre_2 = Genre.objects.create(name="Genre2")
        genre_3 = Genre.objects.create(name="Genre3")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)
        movie_with_genre_3.genres.add(genre_3)

        response = self.client.get(MOVIE_URL,{"genres": f"{genre_1.id}, {genre_2.id}"})

        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_with_genres_1 = MovieListSerializer(movie_with_genre_1)
        serializer_with_genres_2 = MovieListSerializer(movie_with_genre_2)
        serializer_with_genres_3 = MovieListSerializer(movie_with_genre_3)

        self.assertNotIn(serializer_without_genres.data, response.data)
        self.assertIn(serializer_with_genres_1.data, response.data)
        self.assertIn(serializer_with_genres_2.data, response.data)
        self.assertNotIn(serializer_with_genres_3.data, response.data)

    def test_movies_filter_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actors_1 = sample_movie(title="MovieWithActors1")
        movie_with_actors_2 = sample_movie(title="MovieWithActors2")

        actor_1 = Actor.objects.create(first_name="ActorFirstName1", last_name="ActorLastName1")
        actor_2 = Actor.objects.create(first_name="ActorFirstName2", last_name="ActorLastName2")

        movie_with_actors_1.actors.add(actor_1)
        movie_with_actors_2.actors.add(actor_2)

        response = self.client.get(MOVIE_URL,{"actors": actor_1.id})

        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_with_actors_1 = MovieListSerializer(movie_with_actors_1)
        serializer_with_actors_2 = MovieListSerializer(movie_with_actors_2)

        self.assertNotIn(serializer_without_actors.data, response.data)
        self.assertIn(serializer_with_actors_1.data, response.data)
        self.assertNotIn(serializer_with_actors_2.data, response.data)

    def test_movies_filter_by_title(self):
        movie_with_title_1 = sample_movie(title="MovieWithTitle1")
        movie_with_title_2 = sample_movie(title="MovieWithTitle2")

        response = self.client.get(MOVIE_URL,{"title": movie_with_title_1.title})

        serializer_with_title_1 = MovieListSerializer(movie_with_title_1)
        serializer_with_title_2 = MovieListSerializer(movie_with_title_2)

        self.assertIn(serializer_with_title_1.data, response.data)
        self.assertNotIn(serializer_with_title_2.data, response.data)

    def test_detail_movie(self):
        movie = sample_movie()
        movie.actors.add(Actor.objects.create(first_name="ActorFirstName", last_name="ActorLastName"))
        movie.genres.add(Genre.objects.create(name="Genre1"))

        response = self.client.get(detail_url(movie.id))

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie(self):
        payload = {
            "title": "Movie Title",
            "description": "description",
            "duration": 5,
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_movie(self):
        movie = sample_movie()

        response = self.client.delete(detail_url(movie.id))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_movie(self):
        movie = sample_movie()

        response = self.client.patch(detail_url(movie.id), {"title": "Movie Title"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # def test_upload_image(self):
    #     movie = sample_movie()
    #
    #     image = generate_image_file()
    #
    #     response = self.client.post(detail_view_image(movie.id), {"image": image}, format="multipart")
    #
    #     self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    #     self.assertIn("image", response.data)



class AuthenticatedAdminMovieViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="<EMAIL>",
            password="<PASSWORD>",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Genre1")
        actor = Actor.objects.create(first_name="ActorFirstName", last_name="ActorLastName")
        payload = {
            "title": "Movie Title",
            "description": "description",
            "duration": 5,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        response = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=response.data["id"])

        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIn(genre.id, response.data.get("genres"))
        self.assertIn(actor.id, response.data.get("actors"))

        self.assertEqual(actors.count(), 1)
        self.assertEqual(genres.count(), 1)

    # def test_upload_image(self):
    #     movie = sample_movie()
    #
    #     image = generate_image_file()
    #
    #     response = self.client.post(detail_view_image(movie.id), {"image": image}, format="multipart")
    #
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertIn("image", response.data)

