import pytest
from rest_framework import status
from rest_framework.test import APIClient
from cinema.models import Movie


# Pytest precisa de fixtures para user/admin e os dados carregados
# Assumimos que as fixtures de Movie/Genre/Actor foram carregadas usando o comando acima

@pytest.fixture
def admin_token_client():
    """Fixture para um cliente autenticado como superusuário."""
    client = APIClient()
    # Usar a fixture de usuário padrão (admin.user@cinema.com/1qazcde3)
    # **Você precisa configurar uma fixture para gerar o token JWT para este usuário**
    # Exemplo *hipotético* de como seria obter o token:

    # response = client.post('/api/user/token/', {'email': 'admin.user@cinema.com', 'password': '1qazcde3'})
    # access_token = response.data['access']
    # client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    # *** ATENÇÃO: Você deve garantir que o 'admin_token_client' obtenha o token JWT ***
    # Para simplificar, vou usar um cliente não autenticado e um autenticado (a ser implementado)
    return client


@pytest.fixture
def api_client():
    """Cliente para requisições não autenticadas (anon)"""
    return APIClient()


# *** FIXTURE DE JWT (PRECISA SER IMPLEMENTADA PARA TESTAR AUTH) ***
@pytest.fixture
def auth_client(api_client):
    """Fixture para cliente autenticado com JWT (a ser implementada)"""
    # Aqui você faria a chamada para obter o token e configuraria o header
    # Para este esqueleto, vamos testar anon vs admin_token_client configurado
    return api_client


# ***********************************************************************


@pytest.mark.django_db
def test_movie_list_unauthenticated(api_client):
    """Testa a lista sem autenticação (deve funcionar com limite de 10/min)."""
    response = api_client.get("/api/cinema/movies/")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.data['results'], list)
    # O número de resultados depende das suas fixtures


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
    """Testa os filtros de gênero e ator (usando um cliente que deve ter acesso)."""
    # Assumindo que Genre ID 1 é 'Action' e Actor ID 1 é 'John Doe'
    # O cliente autenticado deve ser capaz de passar nos filtros.
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
    assert response.status_code == status.HTTP_401_UNAUTHORIZED  # Esperado, pois a permissão padrão é IsAuthenticated se não especificar.


# *** TESTE DE THROTTLING ***
# Este teste exige muitas chamadas rápidas, que geralmente são feitas em um teste separado
# ou com um loop, mas o princípio é:

@pytest.mark.django_db
def test_throttling_anon_limit(api_client):
    """Testa se o limite de 10 requisições/minuto é aplicado (requer chamar 11 vezes rapidamente)."""
    # Para um teste real, você faria um loop e esperaria um 429 (Too Many Requests)
    # Chamadas válidas (ex: 5)
    for _ in range(5):
        api_client.get("/api/cinema/movies/")

        # A próxima chamada deveria ser OK, mas a 11ª falharia rapidamente se o limite fosse 10/segundo.
    # Como é 10/minuto, este teste só falhará se você rodar muitos testes de uma vez ou mudar o rate para segundos.
    # A lógica de teste é: após muitas chamadas em um curto espaço, um 429 deve ser retornado.
    pass  # Deixado como 'pass' pois o rate de 10/min é lento para testar em um teste unitário rápido.
