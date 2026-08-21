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
        # A API aceita busca por nome (não só AppID numérico) via core/search.py.
        # Uma query que não corresponde a nenhum jogo deve retornar 404, não 400.
        var_objResponse = client.post("/predict/game", json={"query": "zzzznonexistentgame12345"})
        assert var_objResponse.status_code == 404

    def test_predict_by_name(self, client):
        # Busca por nome é um comportamento intencional e deve funcionar (200).
        var_objResponse = client.post("/predict/game", json={"query": "Counter-Strike"})
        assert var_objResponse.status_code == 200

    def test_predict_invalid_horizonte(self, client):
        # horizonte fora do conjunto permitido deve gerar 422 (validação do Pydantic)
        var_objResponse = client.post(
            "/predict/game", json={"query": "1245620", "horizonte": "180d"}
        )
        assert var_objResponse.status_code == 422

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


class TestModelRoutingRegression:
    """
    Regressão do bug do Item A: a resolução de modelo de regressão (dias) por
    horizonte deve priorizar a nomenclatura atual "_dias_" (modelos reais,
    diferentes por horizonte) sobre a nomenclatura legada "modelo_regressao_{h}.joblib"
    (que já existiu como arquivo dummy/placeholder byte-idêntico entre horizontes).

    Este teste simula exatamente o cenário do bug original — arquivo legado e
    arquivo "_dias_" coexistindo no diretório de modelos — e falharia se a
    ordem de prioridade fosse invertida novamente.
    """

    def test_regressao_dias_prioriza_nomenclatura_atual_sobre_legado(self, tmp_path, monkeypatch):
        from pathlib import Path
        from api.models_loader import ModelManager

        # Recria o cenário do bug: arquivo legado (dummy) e arquivo real "_dias_"
        # presentes ao mesmo tempo, para cada horizonte.
        for var_strHorizonte in ["30d", "60d", "90d"]:
            (tmp_path / f"modelo_regressao_{var_strHorizonte}.joblib").write_bytes(b"LEGACY_DUMMY")
            (tmp_path / f"modelo_regressao_dias_{var_strHorizonte}.joblib").write_bytes(
                f"REAL_{var_strHorizonte}".encode()
            )

        var_listPathsCarregados = []

        def fake_joblib_load(path):
            var_objPath = Path(path)
            var_listPathsCarregados.append(var_objPath)
            return var_objPath.name  # devolve o nome do arquivo como "modelo" fake

        monkeypatch.setattr("api.models_loader.joblib.load", fake_joblib_load)

        var_objManager = ModelManager(str(tmp_path))

        var_dictResultadosPorHorizonte = {}
        for var_strHorizonte in ["30d", "60d", "90d"]:
            var_objManager.ensure_models_for_horizon(var_strHorizonte)
            var_dictResultadosPorHorizonte[var_strHorizonte] = var_objManager.regressao_model

        # Cada horizonte deve ter carregado o arquivo "_dias_" correspondente,
        # nunca o arquivo legado/dummy.
        for var_strHorizonte in ["30d", "60d", "90d"]:
            assert (
                var_dictResultadosPorHorizonte[var_strHorizonte]
                == f"modelo_regressao_dias_{var_strHorizonte}.joblib"
            )

        # E os 3 horizontes devem ter carregado ARQUIVOS DIFERENTES entre si —
        # o bug original fazia todos caírem no mesmo dummy.
        assert len(set(var_dictResultadosPorHorizonte.values())) == 3

    def test_regressao_dias_horizonte_latest_usa_30d(self, tmp_path, monkeypatch):
        from pathlib import Path
        from api.models_loader import ModelManager

        (tmp_path / "modelo_regressao_dias_30d.joblib").write_bytes(b"REAL_30")

        def fake_joblib_load(path):
            return Path(path).name

        monkeypatch.setattr("api.models_loader.joblib.load", fake_joblib_load)

        var_objManager = ModelManager(str(tmp_path))
        var_objManager.ensure_models_for_horizon("latest")

        assert var_objManager.regressao_model == "modelo_regressao_dias_30d.joblib"


class TestRoot:
    """Testes da rota raiz."""

    def test_root(self, client):
        var_objResponse = client.get("/")
        assert var_objResponse.status_code == 200
        var_dictData = var_objResponse.json()
        assert "name" in var_dictData
        assert "version" in var_dictData
