from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_graph_endpoint():
    response = client.get('/graph/mother')
    assert response.status_code == 200
    data = response.json()
    assert 'nodes' in data
    assert 'edges' in data


def test_random_endpoint():
    response = client.get('/random')
    assert response.status_code == 200
    assert 'word' in response.json()
