"""Testes para a API de inferência."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from api.main import app
from tests.unit.mocks.mock_data import get_mock_steam_game, get_mock_itad_history


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as var_objClient:
        yield var_objClient


# Mockando os clientes externos em todos os testes unitários
@pytest.fixture(autouse=True)
def mock_external_apis():
    with patch("api.routes.predict.SteamClient.get_game_data", new_callable=AsyncMock) as mock_steam:
        with patch("api.routes.predict.ITADClient.get_price_history", new_callable=AsyncMock) as mock_itad:
            # Configura os retornos baseados nos dados locais
            mock_steam.side_effect = get_mock_steam_game
            
            def mock_history_wrapper(appid, arg_floatPrecoBase=0.0):
                return get_mock_itad_history(arg_floatPrecoBase=arg_floatPrecoBase, arg_intAnos=5)
            mock_itad.side_effect = mock_history_wrapper
            
            yield


class TestHealth:
    """Testes do endpoint /health."""

    def test_health_returns_200(self, client):
        var_objResponse = client.get("/health")
        assert var_objResponse.status_code == 200
        var_dictData = var_objResponse.json()
        assert "status" in var_dictData
        assert "models" in var_dictData
        assert "timestamp" in var_dictData


class TestPredict:
    """Testes dos endpoints de predição."""

    def test_predict_invalid_query(self, client):
        var_objResponse = client.post("/predict/game", json={"query": "Counter-Strike"})
        assert var_objResponse.status_code == 400

    def test_predict_by_appid(self, client):
        var_objResponse = client.post("/predict/game", json={"query": "1245620"})
        assert var_objResponse.status_code == 200
        var_dictData = var_objResponse.json()
        assert var_dictData["game"]["appid"] == 1245620

    def test_predict_free_game(self, client):
        var_objResponse = client.post("/predict/game", json={"query": "730"})
        assert var_objResponse.status_code == 200
        var_dictData = var_objResponse.json()
        assert var_dictData["game"]["appid"] == 730
        assert var_dictData["classificacao"] is None
        assert var_dictData["regressao"] is None

    def test_predict_not_found(self, client):
        var_objResponse = client.post("/predict/game", json={"query": "99999999"})
        assert var_objResponse.status_code == 404
        assert var_objResponse.status_code == 404

    def test_predict_classificacao(self, client):
        var_objResponse = client.post("/predict/classificacao", json={"query": "1245620"})
        assert var_objResponse.status_code == 200
        var_dictData = var_objResponse.json()
        if var_dictData.get("classificacao"):
            assert var_dictData["classificacao"]["classe"] in ["cai", "mantem", "sobe"]
            assert 0 <= var_dictData["classificacao"]["confianca"] <= 1

    def test_predict_regressao(self, client):
        var_objResponse = client.post("/predict/regressao", json={"query": "1245620"})
        assert var_objResponse.status_code == 200
        var_dictData = var_objResponse.json()
        if var_dictData.get("regressao"):
            assert var_dictData["regressao"]["dias_estimados"] >= 0


class TestRoot:
    """Testes da rota raiz."""

    def test_root(self, client):
        var_objResponse = client.get("/")
        assert var_objResponse.status_code == 200
        var_dictData = var_objResponse.json()
        assert "name" in var_dictData
        assert "version" in var_dictData
