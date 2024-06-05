from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from PIL import Image
import tempfile

from cinema.models import Movie

User = get_user_model()


class MovieListViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(password='12345', email='test@example.com')
        self.client.force_authenticate(user=self.user)
        self.movie = Movie.objects.create(title='Test Movie', description='Test Description', duration=120)

    def test_list_movies(self):
        response = self.client.get('/api/cinema/movies/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class MovieRetrieveViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(password='12345', email='test@example.com')
        self.client.force_authenticate(user=self.user)
        self.movie = Movie.objects.create(title='Test Movie', description='Test Description', duration=120)

    def test_retrieve_movie(self):
        response = self.client.get(f'/api/cinema/movies/{self.movie.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Movie')


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            password='12345', email='admin@example.com'
        )
        self.client.force_authenticate(user=self.user)
        self.movie = Movie.objects.create(title='Test Movie', description='Test Description', duration=120)

    def tearDown(self):
        self.movie.image.delete()

    def test_upload_image_to_movie(self):
        with tempfile.NamedTemporaryFile(suffix='.jpg') as ntf:
            image = Image.new('RGB', (100, 100))
            image.save(ntf, format='JPEG')
            ntf.seek(0)
            url = f'/api/cinema/movies/{self.movie.id}/upload-image/'
            response = self.client.post(url, {'image': ntf}, format='multipart')

        self.movie.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('image', response.data)
        self.assertTrue(self.movie.image)
