"""Testes para a API de inferência."""

import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestHealth:
    """Testes do endpoint /health."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "models" in data
        assert "timestamp" in data


class TestSearch:
    """Testes do endpoint /search."""

    def test_search_by_name(self, client):
        response = client.get("/search", params={"q": "Counter-Strike"})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["total"] > 0
        assert data["results"][0]["name"]

    def test_search_empty_query(self, client):
        response = client.get("/search", params={"q": ""})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_search_partial_name(self, client):
        response = client.get("/search", params={"q": "elden"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0


class TestPredict:
    """Testes dos endpoints de predição."""

    def test_predict_by_name(self, client):
        response = client.post("/predict/game", json={"query": "Counter-Strike"})
        assert response.status_code == 200
        data = response.json()
        assert "game" in data
        assert data["game"]["name"]

    def test_predict_by_appid(self, client):
        response = client.post("/predict/game", json={"query": "730"})
        assert response.status_code == 200
        data = response.json()
        assert data["game"]["appid"] == 730

    def test_predict_not_found(self, client):
        response = client.post("/predict/game", json={"query": "xyzabcnonexistentgame123456"})
        assert response.status_code == 404

    def test_predict_classificacao(self, client):
        response = client.post("/predict/classificacao", json={"query": "Counter-Strike"})
        assert response.status_code == 200
        data = response.json()
        if data.get("classificacao"):
            assert data["classificacao"]["classe"] in ["cai", "mantem", "sobe"]
            assert 0 <= data["classificacao"]["confianca"] <= 1

    def test_predict_regressao(self, client):
        response = client.post("/predict/regressao", json={"query": "Counter-Strike"})
        assert response.status_code == 200
        data = response.json()
        if data.get("regressao"):
            assert data["regressao"]["dias_estimados"] >= 0


class TestRoot:
    """Testes da rota raiz."""

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
