"""Endpoints de predição: classificação e regressão."""

from fastapi import APIRouter, Request, HTTPException
import pandas as pd
import numpy as np
import logging

from api.schemas import (
    GameQueryInput,
    GameFeaturesInput,
    PredictionResponse,
    ClassificationResult,
    RegressionResult,
    GameInfo,
    SearchResult,
)
from core.game_search import search_games, get_game_by_name_or_id
from core.steam_client import SteamClient
from core.itad_client import ITADClient
from core.feature_engineering import (
    gerar_features_para_inferencia,
    FEATURE_COLUMNS,
    LABEL_MAP_CLASSIFICACAO,
    LABEL_MAP_CLASSIFICACAO_EMOJI,
)

logger = logging.getLogger("api.predict")
router = APIRouter(tags=["Prediction"])


def _run_prediction(model_manager, features_df: pd.DataFrame) -> tuple:
    """
    Executa classificação e regressão nos features fornecidos.

    Retorna:
    - tuple: (ClassificationResult | None, RegressionResult | None)
    """
    clf_result = None
    reg_result = None

    # ── Classificação ──
    if model_manager.classificacao_available:
        try:
            pred = model_manager.classificacao_model.predict(features_df)[0]
            classe = LABEL_MAP_CLASSIFICACAO.get(int(pred), "desconhecido")
            classe_emoji = LABEL_MAP_CLASSIFICACAO_EMOJI.get(int(pred), "❓ Desconhecido")

            # Probabilidades
            probas = {}
            if hasattr(model_manager.classificacao_model, "predict_proba"):
                proba_array = model_manager.classificacao_model.predict_proba(features_df)[0]
                for i, p in enumerate(proba_array):
                    label = LABEL_MAP_CLASSIFICACAO.get(i, f"classe_{i}")
                    probas[label] = round(float(p), 4)
            else:
                probas = {classe: 1.0}

            confianca = max(probas.values()) if probas else 0.0

            clf_result = ClassificationResult(
                classe=classe,
                classe_emoji=classe_emoji,
                probabilidades=probas,
                confianca=round(confianca, 4),
            )
        except Exception as e:
            logger.error(f"Erro na classificação: {e}")

    # ── Regressão ──
    if model_manager.regressao_available:
        try:
            pred = model_manager.regressao_model.predict(features_df)[0]
            dias = max(0, int(round(float(pred))))
            dias = min(dias, 365)  # Cap em 365 dias

            if dias <= 7:
                descricao = f"🔥 Promoção iminente! Estimativa: {dias} dias"
            elif dias <= 30:
                descricao = f"⏳ Promoção próxima: ~{dias} dias"
            elif dias <= 90:
                descricao = f"📅 Promoção em breve: ~{dias} dias ({dias // 30} meses)"
            else:
                descricao = f"⏰ Promoção distante: ~{dias} dias ({dias // 30} meses)"

            reg_result = RegressionResult(
                dias_estimados=dias,
                descricao=descricao,
            )
        except Exception as e:
            logger.error(f"Erro na regressão: {e}")

    return clf_result, reg_result


@router.post("/predict/game", response_model=PredictionResponse)
async def predict_by_game(input_data: GameQueryInput, request: Request):
    """
    Faz predição completa (classificação + regressão) a partir do nome ou AppID do jogo.

    Fluxo:
    1. Busca o jogo pelo nome ou AppID
    2. Obtém dados do jogo (Steam mock)
    3. Obtém histórico de preços (ITAD mock)
    4. Gera features
    5. Executa predição
    """
    model_manager = request.app.state.model_manager

    # 1. Encontrar o jogo
    game = get_game_by_name_or_id(input_data.query)
    if not game:
        raise HTTPException(status_code=404, detail=f"Jogo não encontrado: '{input_data.query}'")

    appid = game["appid"]
    game_name = game["name"]

    # 2. Dados do jogo
    steam_data = SteamClient.get_game_data(appid)
    if not steam_data:
        raise HTTPException(status_code=404, detail=f"Dados do jogo não disponíveis: {appid}")

    # 3. Histórico de preços
    price = steam_data.get("price", 0.0)
    historico = ITADClient.get_price_history(appid, base_price=price)

    # 4. Features
    features_df = gerar_features_para_inferencia(
        review_score=steam_data.get("review_score", 0),
        preco_catalogo=price,
        historico_precos=historico,
    )

    # 5. Hot-reload check
    model_manager.check_and_reload()

    # 6. Predição
    clf_result, reg_result = _run_prediction(model_manager, features_df)

    game_info = GameInfo(
        appid=appid,
        name=game_name,
        price=price,
        review_score=steam_data.get("review_score"),
        header_image=steam_data.get("header_image"),
    )

    return PredictionResponse(
        game=game_info,
        classificacao=clf_result,
        regressao=reg_result,
        features_utilizadas=features_df.iloc[0].to_dict(),
    )


@router.post("/predict/classificacao", response_model=PredictionResponse)
async def predict_classificacao(input_data: GameQueryInput, request: Request):
    """
    Prevê a direção do preço ('cai', 'mantem', 'sobe') para um jogo.
    Aceita AppID ou nome do jogo.
    """
    # Reutiliza a lógica completa mas retorna só classificação
    response = await predict_by_game(input_data, request)
    response.regressao = None
    return response


@router.post("/predict/regressao", response_model=PredictionResponse)
async def predict_regressao(input_data: GameQueryInput, request: Request):
    """
    Prevê quantos dias até a próxima promoção de um jogo.
    Aceita AppID ou nome do jogo.
    """
    response = await predict_by_game(input_data, request)
    response.classificacao = None
    return response


@router.post("/predict/features", response_model=PredictionResponse)
async def predict_from_features(input_data: GameFeaturesInput, request: Request):
    """
    Faz predição a partir de features manuais (modo avançado).
    Útil para testes e integração com outros sistemas.
    """
    model_manager = request.app.state.model_manager

    features_dict = input_data.model_dump()
    features_df = pd.DataFrame([features_dict])[FEATURE_COLUMNS]

    clf_result, reg_result = _run_prediction(model_manager, features_df)

    game_info = GameInfo(appid=0, name="Input Manual")

    return PredictionResponse(
        game=game_info,
        classificacao=clf_result,
        regressao=reg_result,
        features_utilizadas=features_dict,
    )


@router.get("/search", response_model=SearchResult)
async def search_game(q: str, limit: int = 10):
    """
    Busca jogos por nome aproximado.

    Parâmetros:
    - q (str): Query de busca (nome do jogo).
    - limit (int): Máximo de resultados (default: 10).
    """
    results = search_games(q, max_results=limit)
    game_infos = [GameInfo(appid=r["appid"], name=r["name"]) for r in results]

    return SearchResult(
        results=game_infos,
        total=len(game_infos),
        query=q,
    )
