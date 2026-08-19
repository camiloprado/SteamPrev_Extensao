"""Endpoints de predição: classificação e regressão."""

from fastapi import APIRouter, Request, HTTPException
import pandas as pd
import numpy as np
import logging
import time

from api.schemas import (
    GameQueryInput,
    GameFeaturesInput,
    PredictionResponse,
    ClassificationResult,
    RegressionResult,
    GameInfo,
    SearchResult,
)

from core.steam_client import SteamClient
from core.itad_client import ITADClient
from core.feature_engineering import (
    gerar_features_para_inferencia,
    CON_LIST_FEATURE_COLUMNS,
    CON_DICT_LABEL_MAP_CLASSIFICACAO,
    CON_DICT_LABEL_MAP_CLASSIFICACAO_EMOJI,
)

logger = logging.getLogger("api.predict")
router = APIRouter(tags=["Prediction"])


def _executar_predicao(arg_objModelManager, arg_dfFeatures: pd.DataFrame) -> tuple:
    """
    Executa classificação e regressão nos features fornecidos.

    Parâmetros:
    - arg_objModelManager: Instância do ModelManager com modelos carregados.
    - arg_dfFeatures (pd.DataFrame): DataFrame com as features para predição.

    Retorna:
    - tuple: (ClassificationResult | None, RegressionResult | None)
    """
    var_objClassificacaoResult = None
    var_objRegressaoResult = None

    # ── Classificação ──
    if arg_objModelManager.classificacao_available:
        try:
            var_intPredicao = arg_objModelManager.classificacao_model.predict(arg_dfFeatures)[0]
            var_strClasse = CON_DICT_LABEL_MAP_CLASSIFICACAO.get(int(var_intPredicao), "desconhecido")
            var_strClasseEmoji = CON_DICT_LABEL_MAP_CLASSIFICACAO_EMOJI.get(int(var_intPredicao), "❓ Desconhecido")

            # Probabilidades
            var_dictProbabilidades = {}
            if hasattr(arg_objModelManager.classificacao_model, "predict_proba"):
                var_arrProbArray = arg_objModelManager.classificacao_model.predict_proba(arg_dfFeatures)[0]
                for var_intIdx, var_floatProb in enumerate(var_arrProbArray):
                    var_strLabel = CON_DICT_LABEL_MAP_CLASSIFICACAO.get(var_intIdx, f"classe_{var_intIdx}")
                    var_dictProbabilidades[var_strLabel] = round(float(var_floatProb), 4)
            else:
                var_dictProbabilidades = {var_strClasse: 1.0}

            var_floatConfianca = max(var_dictProbabilidades.values()) if var_dictProbabilidades else 0.0

            var_objClassificacaoResult = ClassificationResult(
                classe=var_strClasse,
                classe_emoji=var_strClasseEmoji,
                probabilidades=var_dictProbabilidades,
                confianca=round(var_floatConfianca, 4),
            )
        except Exception as e:
            logger.error(f"Erro na classificação: {e}")

    # ── Regressão ──
    if arg_objModelManager.regressao_available:
        try:
            var_floatPredicao = arg_objModelManager.regressao_model.predict(arg_dfFeatures)[0]
            var_intDias = max(0, int(round(float(var_floatPredicao))))
            var_intDias = min(var_intDias, 365)  # Cap em 365 dias

            if var_intDias <= 7:
                var_strDescricao = f"🔥 Promoção iminente! Estimativa: {var_intDias} dias"
            elif var_intDias <= 30:
                var_strDescricao = f"⏳ Promoção próxima: ~{var_intDias} dias"
            elif var_intDias <= 90:
                var_strDescricao = f"📅 Promoção em breve: ~{var_intDias} dias ({var_intDias // 30} meses)"
            else:
                var_strDescricao = f"⏰ Promoção distante: ~{var_intDias} dias ({var_intDias // 30} meses)"

            # Regressão de Desconto
            var_intDesconto = 0
            var_floatPrecoEstimado = 0.0
            var_floatDescontoMargemErro = 6.6

            if arg_objModelManager.regressao_desconto_available:
                try:
                    var_floatDesconto = arg_objModelManager.regressao_desconto_model.predict(arg_dfFeatures)[0]
                    var_intDesconto = max(0, min(100, int(round(float(var_floatDesconto)))))
                    
                    import json
                    try:
                        manifest_path = arg_objModelManager._var_pathModels / "manifest.json"
                        if manifest_path.exists():
                            with open(manifest_path, "r", encoding="utf-8") as f:
                                manifest_data = json.load(f)
                                horizon = arg_objModelManager._var_strCurrentHorizon
                                model_key = f"modelo_regressao_desconto_{horizon}.joblib"
                                if model_key in manifest_data.get("models", {}):
                                    var_floatDescontoMargemErro = manifest_data["models"][model_key]["metrics"].get("mae", 6.6)
                    except Exception:
                        pass
                    
                    var_floatPrecoAtual = float(arg_dfFeatures["preco_catalogo"].iloc[0]) if "preco_catalogo" in arg_dfFeatures else 0.0
                    var_floatPrecoEstimado = round(var_floatPrecoAtual * (1.0 - (var_intDesconto / 100.0)), 2)
                except Exception as e:
                    logger.error(f"Erro na regressão de desconto: {e}")

            var_objRegressaoResult = RegressionResult(
                dias_estimados=var_intDias,
                desconto_previsto_pct=var_intDesconto,
                desconto_margem_erro=round(var_floatDescontoMargemErro, 1),
                preco_estimado=var_floatPrecoEstimado,
                descricao=var_strDescricao,
            )
        except Exception as e:
            logger.error(f"Erro na regressão: {e}")

    return var_objClassificacaoResult, var_objRegressaoResult


@router.post("/predict/game", response_model=PredictionResponse)
async def predict_by_game(input_data: GameQueryInput, request: Request, debug: bool = False):
    """
    Faz predição completa (classificação + regressão) a partir do nome ou AppID do jogo.

    Fluxo:
    1. Busca o jogo pelo nome ou AppID
    2. Obtém dados do jogo (Steam mock)
    3. Obtém histórico de preços (ITAD mock)
    4. Gera features
    5. Executa predição
    """
    var_objModelManager = request.app.state.model_manager

    var_strQuery = str(input_data.query).strip()
    if not var_strQuery.isdigit():
        from core.search import searcher
        var_intAppidEncontrado = searcher.search_by_name(var_strQuery)
        if not var_intAppidEncontrado:
            raise HTTPException(status_code=404, detail=f"Jogo não encontrado pelo nome: '{var_strQuery}'")
        var_intAppid = var_intAppidEncontrado
    else:
        var_intAppid = int(var_strQuery)

    # 2. Dados do jogo
    var_dictSteamData = await SteamClient.get_game_data(var_intAppid)
    if not var_dictSteamData:
        raise HTTPException(status_code=404, detail=f"Dados do jogo não disponíveis: {var_intAppid}")

    # Early Return: Se o jogo já está em promoção, abortamos a predição.
    if var_dictSteamData.get("is_on_sale"):
        logger.info(f"Bypass de predição ativado para appid {var_intAppid} (Em promoção).")
        return PredictionResponse(
            game=GameInfo(**var_dictSteamData),
            classificacao=None,
            regressao=None,
            features_utilizadas=None,
        )
        
    var_strGameName = var_dictSteamData.get("name", f"App {var_intAppid}")
    var_floatPrice = var_dictSteamData.get("price", 0.0)
    var_boolIsFree = var_dictSteamData.get("is_free", False)
    var_boolIsComingSoon = var_dictSteamData.get("is_coming_soon", False)

    # Early return para jogos não lançados ou gratuitos
    if var_boolIsComingSoon or var_boolIsFree:
        var_objGameInfo = GameInfo(
            appid=var_intAppid,
            name=var_strGameName,
            price=0.0 if var_boolIsComingSoon else var_floatPrice,
            review_score=var_dictSteamData.get("review_score"),
            header_image=var_dictSteamData.get("header_image"),
            is_coming_soon=var_boolIsComingSoon,
            release_date=var_dictSteamData.get("release_date"),
        )
        var_listWarnings = []
        if var_boolIsComingSoon:
            var_listWarnings.append("Este jogo ainda não foi lançado. Previsões de preço não estão disponíveis.")
            
        return PredictionResponse(
            game=var_objGameInfo,
            classificacao=None,
            regressao=None,
            features_utilizadas={} if debug else None,
            warnings=var_listWarnings if var_listWarnings else None,
        )

    # 3. Histórico de preços
    var_listHistorico = await ITADClient.get_price_history(var_intAppid, arg_floatPrecoBase=var_floatPrice)
    
    var_listWarnings = []
    if time.time() < ITADClient.rate_limit_until:
        var_listWarnings.append("A API de histórico de preços (ITAD) atingiu o limite de requisições. O sistema está utilizando um histórico de preços simulado (mock) para a demonstração dos modelos de IA.")

    # 4. Features
    var_dfFeatures = gerar_features_para_inferencia(
        arg_floatReviewScore=var_dictSteamData.get("review_score", 0),
        arg_floatPrecoCatalogo=var_floatPrice,
        arg_listHistoricoPrecos=var_listHistorico,
    )

    # 5. Hot-reload check & Dynamic Model Loading
    var_objModelManager.ensure_models_for_horizon(input_data.horizonte)

    # 6. Predição
    var_objClassificacao, var_objRegressao = _executar_predicao(var_objModelManager, var_dfFeatures)

    var_objGameInfo = GameInfo(
        appid=var_intAppid,
        name=var_strGameName,
        price=var_floatPrice,
        review_score=var_dictSteamData.get("review_score"),
        header_image=var_dictSteamData.get("header_image"),
        is_coming_soon=var_boolIsComingSoon,
        release_date=var_dictSteamData.get("release_date"),
    )

    return PredictionResponse(
        game=var_objGameInfo,
        classificacao=var_objClassificacao,
        regressao=var_objRegressao,
        features_utilizadas=var_dfFeatures.iloc[0].to_dict() if debug else None,
        warnings=var_listWarnings if var_listWarnings else None,
    )


@router.post("/predict/classificacao", response_model=PredictionResponse)
async def predict_classificacao(input_data: GameQueryInput, request: Request, debug: bool = False):
    """
    Prevê a direção do preço ('cai', 'mantem', 'sobe') para um jogo.
    Aceita AppID ou nome do jogo.
    """
    # Reutiliza a lógica completa mas retorna só classificação
    var_objResponse = await predict_by_game(input_data, request, debug)
    var_objResponse.regressao = None
    return var_objResponse


@router.post("/predict/regressao", response_model=PredictionResponse)
async def predict_regressao(input_data: GameQueryInput, request: Request, debug: bool = False):
    """
    Prevê quantos dias até a próxima promoção de um jogo.
    Aceita AppID ou nome do jogo.
    """
    var_objResponse = await predict_by_game(input_data, request, debug)
    var_objResponse.classificacao = None
    return var_objResponse


@router.post("/predict/features", response_model=PredictionResponse)
async def predict_from_features(input_data: GameFeaturesInput, request: Request, debug: bool = False):
    """
    Faz predição a partir de features manuais (modo avançado).
    Útil para testes e integração com outros sistemas.
    """
    var_objModelManager = request.app.state.model_manager

    var_dictFeatures = input_data.model_dump()
    var_dfFeatures = pd.DataFrame([var_dictFeatures])[CON_LIST_FEATURE_COLUMNS]

    var_objClassificacao, var_objRegressao = _executar_predicao(var_objModelManager, var_dfFeatures)

    var_objGameInfo = GameInfo(appid=0, name="Input Manual")

    return PredictionResponse(
        game=var_objGameInfo,
        classificacao=var_objClassificacao,
        regressao=var_objRegressao,
        features_utilizadas=var_dictFeatures if debug else None,
    )


