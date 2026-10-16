import io
import tempfile
from pathlib import Path

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Actor, Genre, Movie


MOVIES_URL = reverse("cinema:movie-list")


def movie_detail_url(movie):
    return reverse("cinema:movie-detail", args=[movie.pk])


def movie_image_url(movie):
    return reverse("cinema:movie-upload-image", args=[movie.pk])


def image_file():
    image = io.BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(image, format="JPEG")
    return SimpleUploadedFile(
        "poster.jpg", image.getvalue(), content_type="image/jpeg"
    )


class MovieViewSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email="movie-reader@example.com", password="test-password"
        )
        cls.staff = get_user_model().objects.create_user(
            email="movie-staff@example.com",
            password="test-password",
            is_staff=True,
        )
        cls.drama = Genre.objects.create(name="Drama")
        cls.comedy = Genre.objects.create(name="Comedy")
        cls.action = Genre.objects.create(name="Action")
        cls.actor = Actor.objects.create(first_name="Tom", last_name="Hanks")
        cls.other_actor = Actor.objects.create(
            first_name="Emma", last_name="Stone"
        )
        cls.third_actor = Actor.objects.create(
            first_name="Morgan", last_name="Freeman"
        )
        cls.movie = Movie.objects.create(
            title="The Green Mile", description="A prison drama", duration=189
        )
        cls.movie.genres.add(cls.drama, cls.action)
        cls.movie.actors.add(cls.actor, cls.third_actor)
        cls.other_movie = Movie.objects.create(
            title="La La Land", description="A musical", duration=128
        )
        cls.other_movie.genres.add(cls.drama, cls.comedy)
        cls.other_movie.actors.add(cls.other_actor)
        cls.third_movie = Movie.objects.create(
            title="Toy Story", description="An animated adventure", duration=81
        )
        cls.third_movie.genres.add(cls.comedy)
        cls.third_movie.actors.add(cls.actor)

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = APIClient()
        media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

    def movie_payload(self, **changes):
        payload = {
            "title": "New movie",
            "description": "A new story",
            "duration": 110,
            "genres": [self.drama.pk, self.comedy.pk],
            "actors": [self.actor.pk, self.other_actor.pk],
        }
        payload.update(changes)
        return payload

    def assert_movie_ids(self, response, movies):
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [movie["id"] for movie in response.data],
            [movie.pk for movie in movies],
        )


class UnauthenticatedMovieViewSetTests(MovieViewSetTestCase):
    def test_list_requires_authentication(self):
        response = self.client.get(MOVIES_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_requires_authentication(self):
        response = self.client.get(movie_detail_url(self.movie))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_authentication_and_does_not_save(self):
        count = Movie.objects.count()

        response = self.client.post(
            MOVIES_URL, self.movie_payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Movie.objects.count(), count)

    def test_image_upload_requires_authentication(self):
        response = self.client.post(
            movie_image_url(self.movie),
            {"image": image_file()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.movie.refresh_from_db()
        self.assertFalse(self.movie.image)


class AuthenticatedMovieViewSetTests(MovieViewSetTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_list_returns_all_movies_in_title_order(self):
        response = self.client.get(MOVIES_URL)

        self.assert_movie_ids(
            response, [self.movie, self.other_movie, self.third_movie]
        )
        self.assertEqual(
            [movie["title"] for movie in response.data],
            ["La La Land", "The Green Mile", "Toy Story"],
        )

    def test_list_without_movies_returns_empty_list(self):
        Movie.objects.all().delete()

        response = self.client.get(MOVIES_URL)

        self.assert_movie_ids(response, [])

    def test_list_serializes_relation_names_and_image(self):
        response = self.client.get(MOVIES_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        movie = next(
            item for item in response.data if item["id"] == self.movie.pk
        )
        self.assertEqual(
            set(movie),
            {
                "id", "title", "description", "duration", "genres", "actors",
                "image",
            },
        )
        self.assertEqual(movie["title"], self.movie.title)
        self.assertEqual(movie["description"], self.movie.description)
        self.assertEqual(movie["duration"], self.movie.duration)
        self.assertCountEqual(movie["genres"], ["Drama", "Action"])
        self.assertCountEqual(movie["actors"], ["Tom Hanks", "Morgan Freeman"])
        self.assertIsNone(movie["image"])

    def test_retrieve_serializes_nested_relations(self):
        response = self.client.get(movie_detail_url(self.movie))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.movie.pk)
        self.assertEqual(response.data["title"], self.movie.title)
        self.assertEqual(response.data["description"], self.movie.description)
        self.assertEqual(response.data["duration"], self.movie.duration)
        self.assertCountEqual(
            response.data["genres"],
            [
                {"id": self.drama.pk, "name": self.drama.name},
                {"id": self.action.pk, "name": self.action.name},
            ],
        )
        self.assertCountEqual(
            response.data["actors"],
            [
                {
                    "id": actor.pk,
                    "first_name": actor.first_name,
                    "last_name": actor.last_name,
                    "full_name": actor.full_name,
                }
                for actor in [self.actor, self.third_actor]
            ],
        )
        self.assertIsNone(response.data["image"])

    def test_retrieve_nonexistent_movie_returns_not_found(self):
        response = self.client.get(
            reverse("cinema:movie-detail", args=[999999])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_title_filter_is_case_insensitive_and_matches_substrings(self):
        response = self.client.get(MOVIES_URL, {"title": "gReEn"})

        self.assert_movie_ids(response, [self.movie])

    def test_title_filter_without_matches_returns_empty_list(self):
        response = self.client.get(MOVIES_URL, {"title": "does-not-exist"})

        self.assert_movie_ids(response, [])

    def test_genre_filter_accepts_one_id(self):
        response = self.client.get(MOVIES_URL, {"genres": self.action.pk})

        self.assert_movie_ids(response, [self.movie])

    def test_genre_filter_accepts_csv_and_does_not_duplicate_movies(self):
        response = self.client.get(
            MOVIES_URL, {"genres": f"{self.drama.pk},{self.comedy.pk}"}
        )

        self.assert_movie_ids(
            response, [self.movie, self.other_movie, self.third_movie]
        )

    def test_actor_filter_accepts_one_id(self):
        response = self.client.get(MOVIES_URL, {"actors": self.other_actor.pk})

        self.assert_movie_ids(response, [self.other_movie])

    def test_actor_filter_accepts_csv_and_does_not_duplicate_movies(self):
        response = self.client.get(
            MOVIES_URL, {"actors": f"{self.actor.pk},{self.third_actor.pk}"}
        )

        self.assert_movie_ids(response, [self.movie, self.third_movie])

    def test_filters_are_combined_and_joined_results_are_distinct(self):
        response = self.client.get(
            MOVIES_URL,
            {
                "title": "the",
                "genres": f"{self.drama.pk},{self.action.pk}",
                "actors": f"{self.actor.pk},{self.third_actor.pk}",
            },
        )

        self.assert_movie_ids(response, [self.movie])

    def test_combined_filters_require_every_condition(self):
        response = self.client.get(
            MOVIES_URL,
            {"genres": self.action.pk, "actors": self.other_actor.pk},
        )

        self.assert_movie_ids(response, [])

    def test_nonexistent_relation_filters_return_empty_list(self):
        for parameter in ["genres", "actors"]:
            with self.subTest(parameter=parameter):
                response = self.client.get(MOVIES_URL, {parameter: 999999})

                self.assert_movie_ids(response, [])

    def test_empty_filters_are_ignored(self):
        response = self.client.get(
            MOVIES_URL, {"title": "", "genres": "", "actors": ""}
        )

        self.assert_movie_ids(
            response, [self.movie, self.other_movie, self.third_movie]
        )

    def test_regular_user_cannot_create_movie(self):
        count = Movie.objects.count()

        response = self.client.post(
            MOVIES_URL, self.movie_payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Movie.objects.count(), count)

    def test_regular_user_cannot_upload_image(self):
        response = self.client.post(
            movie_image_url(self.movie),
            {"image": image_file()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.movie.refresh_from_db()
        self.assertFalse(self.movie.image)


class StaffMovieViewSetTests(MovieViewSetTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.staff)

    def test_staff_user_can_list_and_retrieve_movies(self):
        list_response = self.client.get(MOVIES_URL)
        detail_response = self.client.get(movie_detail_url(self.movie))

        self.assert_movie_ids(
            list_response, [self.movie, self.other_movie, self.third_movie]
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["id"], self.movie.pk)

    def test_create_movie_saves_fields_and_relations(self):
        payload = self.movie_payload()
        count = Movie.objects.count()

        response = self.client.post(MOVIES_URL, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), count + 1)
        movie = Movie.objects.get(pk=response.data["id"])
        for field in ["title", "description", "duration"]:
            self.assertEqual(getattr(movie, field), payload[field])
            self.assertEqual(response.data[field], payload[field])
        self.assertCountEqual(
            movie.genres.values_list("pk", flat=True), payload["genres"]
        )
        self.assertCountEqual(
            movie.actors.values_list("pk", flat=True), payload["actors"]
        )
        self.assertCountEqual(response.data["genres"], payload["genres"])
        self.assertCountEqual(response.data["actors"], payload["actors"])
        self.assertNotIn("image", response.data)

    def test_invalid_movie_fields_do_not_create_movie(self):
        invalid_fields = {
            "title": "",
            "description": "",
            "duration": "not-an-integer",
        }
        count = Movie.objects.count()
        genre_count = Genre.objects.count()
        actor_count = Actor.objects.count()

        for field, value in invalid_fields.items():
            with self.subTest(field=field):
                response = self.client.post(
                    MOVIES_URL,
                    self.movie_payload(**{field: value}),
                    format="json",
                )

                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST
                )
                self.assertIn(field, response.data)
                self.assertEqual(Movie.objects.count(), count)
                self.assertEqual(Genre.objects.count(), genre_count)
                self.assertEqual(Actor.objects.count(), actor_count)

    def test_missing_required_fields_do_not_create_movie(self):
        count = Movie.objects.count()
        for field in ["title", "description", "duration", "genres", "actors"]:
            with self.subTest(field=field):
                payload = self.movie_payload()
                del payload[field]

                response = self.client.post(MOVIES_URL, payload, format="json")

                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST
                )
                self.assertIn(field, response.data)
                self.assertEqual(Movie.objects.count(), count)

    def test_nonexistent_relations_do_not_create_movie(self):
        count = Movie.objects.count()
        for field in ["genres", "actors"]:
            with self.subTest(field=field):
                response = self.client.post(
                    MOVIES_URL,
                    self.movie_payload(**{field: [999999]}),
                    format="json",
                )

                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST
                )
                self.assertIn(field, response.data)
                self.assertEqual(Movie.objects.count(), count)

    def test_put_is_not_supported_and_does_not_change_movie(self):
        response = self.client.put(
            movie_detail_url(self.movie), self.movie_payload(), format="json"
        )

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.title, "The Green Mile")

    def test_patch_is_not_supported_and_does_not_change_movie(self):
        response = self.client.patch(
            movie_detail_url(self.movie), {"title": "Changed"}, format="json"
        )

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.title, "The Green Mile")

    def test_delete_is_not_supported_and_does_not_remove_movie(self):
        count = Movie.objects.count()

        response = self.client.delete(movie_detail_url(self.movie))

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.assertEqual(Movie.objects.count(), count)
        self.assertTrue(Movie.objects.filter(pk=self.movie.pk).exists())

    def test_upload_valid_image_saves_file_and_returns_image_serializer(self):
        response = self.client.post(
            movie_image_url(self.movie),
            {"image": image_file()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.movie.refresh_from_db()
        self.assertEqual(set(response.data), {"id", "image"})
        self.assertEqual(response.data["id"], self.movie.pk)
        self.assertTrue(response.data["image"].endswith(self.movie.image.url))
        self.assertTrue(Path(self.movie.image.path).is_file())
        with Image.open(self.movie.image.path) as uploaded_image:
            self.assertEqual(uploaded_image.size, (10, 10))
            self.assertEqual(uploaded_image.format, "JPEG")

    def test_upload_invalid_image_does_not_change_existing_image(self):
        self.movie.image.save("original.jpg", image_file(), save=True)
        original_name = self.movie.image.name

        response = self.client.post(
            movie_image_url(self.movie),
            {"image": SimpleUploadedFile("bad.jpg", b"not an image")},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", response.data)
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.image.name, original_name)
        self.assertTrue(Path(self.movie.image.path).is_file())

    def test_upload_to_nonexistent_movie_returns_not_found(self):
        response = self.client.post(
            reverse("cinema:movie-upload-image", args=[999999]),
            {"image": image_file()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_image_uploaded_to_movie_is_visible_in_list_and_detail(self):
        self.client.post(
            movie_image_url(self.movie),
            {"image": image_file()},
            format="multipart",
        )
        self.movie.refresh_from_db()
        self.client.force_authenticate(self.user)

        list_response = self.client.get(MOVIES_URL)
        detail_response = self.client.get(movie_detail_url(self.movie))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        listed_movie = next(
            movie
            for movie in list_response.data
            if movie["id"] == self.movie.pk
        )
        self.assertTrue(listed_movie["image"].endswith(self.movie.image.url))
        self.assertEqual(listed_movie["image"], detail_response.data["image"])
