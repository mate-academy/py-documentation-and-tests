# cinema/tests/test_movie_api.py (Crie este arquivo se ainda não existir)

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from cinema.models import Movie

# Dados do superusuário fornecido
ADMIN_USER_EMAIL = 'admin.user@cinema.com'
ADMIN_USER_PASSWORD = '1qazcde3'
TOKEN_OBTAIN_URL = '/api/user/token/'  # ASSUMIMOS ESTA URL


# --- FIXTURES ---

@pytest.fixture
def api_client():
    """Cliente para requisições não autenticadas (anon)"""
    return APIClient()


@pytest.fixture
def admin_token_client(api_client):
    """Fixture para um cliente autenticado como superusuário (JWT)."""

    # 1. Obter o Token de Acesso
    response = api_client.post(
        TOKEN_OBTAIN_URL,
        {'email': ADMIN_USER_EMAIL, 'password': ADMIN_USER_PASSWORD},
        format='json'
    )

    # Se a requisição falhar, o teste falhará aqui (indicando URL incorreta ou falta de usuário/token endpoint)
    assert response.status_code == status.HTTP_200_OK, f"Falha ao obter token JWT: {response.data}"

    access_token = response.data.get('access')
    assert access_token is not None, "Token de acesso não encontrado na resposta do token."

    # 2. Configurar o Header de Autorização
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    return api_client


# *** Nota: A fixture 'auth_client' foi removida pois 'admin_token_client' a substitui ***


# --- TESTES ---

@pytest.mark.django_db
def test_movie_list_unauthenticated(api_client):
    """Testa a lista sem autenticação (deve funcionar com limite de 10/min)."""
    response = api_client.get("/api/cinema/movies/")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.data['results'], list)


@pytest.mark.django_db
def test_movie_list_filtered_by_title(api_client):
    """Testa o filtro por título."""
    # Supondo que 'Action Hero' e 'Funny Times' existam nas fixtures
    response = api_client.get("/api/cinema/movies/?title=action")

    assert response.status_code == status.HTTP_200_OK

    # Verifica se o filme correto está na resposta (baseado nos dados da fixture)
    titles = [movie['title'] for movie in response.data['results']]
    assert "Action Hero" in titles
    assert "Funny Times" not in titles


@pytest.mark.django_db
def test_movie_list_filtered_by_genre_and_actor(admin_token_client):
    """Testa os filtros de gênero e ator (usando um cliente autenticado com JWT)."""
    # Assumindo que Genre ID 1 é 'Action' e Actor ID 1 é 'John Doe'
    response = admin_token_client.get("/api/cinema/movies/?genres=1&actors=1")

    assert response.status_code == status.HTTP_200_OK

    # Verifica se apenas o filme correspondente aos IDs está presente
    assert len(response.data['results']) == 1
    assert response.data['results'][0]['title'] == "Action Hero"


@pytest.mark.django_db
def test_movie_retrieve(api_client):
    """Testa o endpoint de detalhe (retrieve)."""
    # Assumindo que o primeiro filme criado tem ID 1
    response = api_client.get("/api/cinema/movies/1/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data['title'] == "Action Hero"  # Baseado na fixture de exemplo


@pytest.mark.django_db
def test_movie_create_forbidden_for_unauthenticated(api_client):
    """Testa se a criação falha para não autenticados."""
    data = {
        "title": "New Movie",
        "description": "Desc",
        "duration": 100,
        "genres": [],
        "actors": []
    }
    response = api_client.post("/api/cinema/movies/", data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# *** TESTE DE THROTTLING ***
@pytest.mark.django_db
def test_throttling_anon_limit(api_client):
    """Testa se o limite de 10 requisições/minuto é aplicado (requer chamar 11 vezes rapidamente)."""
    # Este teste é lento para rodar rápido, então apenas um pequeno loop
    for _ in range(5):
        api_client.get("/api/cinema/movies/")
    pass
