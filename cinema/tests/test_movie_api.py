# cinema/tests/test_movie_api.py

from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from cinema.models import Actor, Genre, Movie, CinemaHall, MovieSession


class MovieApiTests(APITestCase):
    def setUp(self):
        # Zera throttling entre testes
        cache.clear()

        self.client = APIClient()
        self.movie_list_url = reverse("cinema:movie-list")
        self.movie_session_list_url = reverse("cinema:moviesession-list")
        self.token_url = reverse("cinema:token_obtain_pair")

        # Usuário staff para permitir POST (upload-image)
        user_model = get_user_model()
        self.username_field = user_model.USERNAME_FIELD
        self.user = user_model.objects.create_user(
            **{self.username_field: "admin@example.com"},
            password="test-pass-123",
            is_staff=True,
        )
        self._auth()  # Autentica para endpoints que exigem login

        # Dados mínimos
        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")
        self.movie = Movie.objects.create(
            title="Example",
            description="Desc",
            duration=120,
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

        self.hall = CinemaHall.objects.create(
            name="Hall 1",
            rows=5,
            seats_in_row=10,
        )
        self.session = MovieSession.objects.create(
            movie=self.movie,
            cinema_hall=self.hall,
            show_time=timezone.now(),
        )

    def _auth(self) -> None:
        # Garante que não há resquícios de throttling antes de logar
        cache.clear()
        payload = {
            self.username_field: getattr(self.user, self.username_field),
            "password": "test-pass-123",
        }
        res = self.client.post(self.token_url, data=payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        access = res.data.get("access")
        self.assertTrue(access)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    @staticmethod
    def _results(data):
        """
        Retorna a lista de itens considerando paginação do DRF:
        - Se data é list: retorna direto.
        - Se é dict com 'results': retorna data['results'].
        - Do contrário, retorna [].
        """
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return []

    def test_list_movies(self):
        res = self.client.get(self.movie_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = self._results(res.data)
        self.assertGreaterEqual(len(items), 1)

    def test_filter_movies_by_title(self):
        res = self.client.get(self.movie_list_url, {"title": "exa"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = self._results(res.data)
        self.assertTrue(any(i["title"] == "Example" for i in items))

    def test_filter_movies_by_genres(self):
        res = self.client.get(
            self.movie_list_url,
            {"genres": str(self.genre.id)},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = self._results(res.data)
        self.assertTrue(any(i["title"] == "Example" for i in items))

    def test_filter_movies_by_actors(self):
        res = self.client.get(
            self.movie_list_url,
            {"actors": str(self.actor.id)},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = self._results(res.data)
        self.assertTrue(any(i["title"] == "Example" for i in items))

    def test_list_movie_sessions(self):
        # Mesmo autenticado, este endpoint deve responder 200 estável
        res = self.client.get(self.movie_session_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = self._results(res.data)
        self.assertGreaterEqual(len(items), 1)

    def test_filter_sessions_by_date(self):
        date_str = self.session.show_time.date().isoformat()
        res = self.client.get(self.movie_session_list_url, {"date": date_str})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = self._results(res.data)
        self.assertGreaterEqual(len(items), 1)

    def test_upload_movie_image(self):
        # Cria uma imagem em memória
        file_obj = BytesIO()
        image = Image.new("RGB", (100, 100))
        image.save(file_obj, format="PNG")
        file_obj.seek(0)

        upload = SimpleUploadedFile(
            "poster.png",
            file_obj.read(),
            content_type="image/png",
        )
        detail_url = reverse("cinema:movie-upload-image", args=[self.movie.id])
        res = self.client.post(
            detail_url,
            data={"image": upload},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
