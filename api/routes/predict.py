"""Endpoints de predição: classificação e regressão."""

from fastapi import APIRouter, Request, HTTPException
import pandas as pd
import numpy as np
import asyncio
import logging
from datetime import datetime

from api.schemas import (
    GameQueryInput,
    GameFeaturesInput,
    PredictionResponse,
    ClassificationResult,
    RegressionResult,
    GameInfo,
    HistoricoDesconto,
    SearchResult,
)

from core.steam_client import SteamClient
from core.itad_client import ITADClient, CON_INT_JANELA_ANOS_PADRAO
from core.feature_engineering import (
    gerar_features_para_inferencia,
    CON_LIST_FEATURE_COLUMNS,
    CON_DICT_LABEL_MAP_CLASSIFICACAO,
    CON_DICT_LABEL_MAP_CLASSIFICACAO_EMOJI,
)

logger = logging.getLogger("api.predict")
router = APIRouter(tags=["Prediction"])


def _calcular_historico_desconto(arg_listHistorico: list, arg_intDescontoAtual: int) -> HistoricoDesconto | None:
    """
    Compara o desconto atual com o maior já registrado no histórico de preços.

    Parâmetros:
    - arg_listHistorico (list): Histórico já obtido via ITADClient.get_price_history (evita nova chamada).
    - arg_intDescontoAtual (int): Percentual de desconto atual do jogo (0 se não estiver em promoção).

    Retorna:
    - HistoricoDesconto | None: None se não há histórico disponível, ou se o jogo
      nunca teve desconto e também não está em promoção agora (nada relevante a
      reportar — melhor omitir do que mostrar um "recorde" de 0%).
    """
    if not arg_listHistorico:
        return None
    var_dictMaiorDesconto = max(arg_listHistorico, key=lambda var_dictPonto: var_dictPonto["desconto"])
    var_intMaiorDesconto = var_dictMaiorDesconto["desconto"]
    if var_intMaiorDesconto == 0 and arg_intDescontoAtual == 0:
        return None
    return HistoricoDesconto(
        eh_maior_historico=arg_intDescontoAtual > 0 and arg_intDescontoAtual >= var_intMaiorDesconto,
        maior_desconto_pct=var_intMaiorDesconto,
        data_maior_desconto=(
            datetime.fromtimestamp(var_dictMaiorDesconto["timestamp"]).strftime("%Y-%m-%d")
            if var_intMaiorDesconto > 0 else None
        ),
        janela_anos=CON_INT_JANELA_ANOS_PADRAO,
        fonte=arg_listHistorico[0].get("fonte", "mock"),
    )


def _obter_cap_dias_horizonte(arg_strHorizonte: str) -> int:
    """
    Teto de dias alinhado ao contrato de exportação (30/60/90).
    O horizonte 'latest' reutiliza o modelo de 30 dias.
    """
    var_strNorm = (arg_strHorizonte or "latest").replace("_latest", "")
    if var_strNorm == "60d":
        return 60
    if var_strNorm == "90d":
        return 90
    return 30


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
            var_strHorizonteAtual = getattr(arg_objModelManager, "_var_strCurrentHorizon", "latest")
            var_intCapDias = _obter_cap_dias_horizonte(var_strHorizonteAtual)
            var_intDias = min(var_intDias, var_intCapDias)

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

                    try:
                        manifest_data = arg_objModelManager.manifest
                        var_strHorizonteManifest = arg_objModelManager._var_strCurrentHorizon
                        if var_strHorizonteManifest == "latest":
                            var_strHorizonteManifest = "30d"
                        model_key = f"modelo_regressao_desconto_{var_strHorizonteManifest}.joblib"
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
    Faz predição completa (classificação + regressão + desconto) a partir do nome ou AppID.

    Fluxo:
    1. Resolve o jogo pelo nome (busca local) ou AppID
    2. Obtém dados ao vivo na Steam Store API (`appdetails` + `appreviews`)
    3. Obtém histórico de preços na ITAD API v2 (`games/lookup/v1` + `games/history/v2`)
    4. Gera as 18 features na mesma ordem do treino
    5. Executa classificação, regressão de dias (cap 30/60/90) e regressão de desconto
    """
    var_objModelManager = request.app.state.model_manager

    var_strQuery = str(input_data.query).strip()
    if not var_strQuery.isdigit():
        from core.search import var_objSearcher
        var_intAppidEncontrado = var_objSearcher.search_by_name(var_strQuery)
        if not var_intAppidEncontrado:
            raise HTTPException(status_code=404, detail=f"Jogo não encontrado pelo nome: '{var_strQuery}'")
        var_intAppid = var_intAppidEncontrado
    else:
        var_intAppid = int(var_strQuery)

    # 2. Dados do jogo
    var_dictSteamData = await SteamClient.get_game_data(var_intAppid)
    if not var_dictSteamData:
        raise HTTPException(status_code=404, detail=f"Dados do jogo não disponíveis: {var_intAppid}")

    # Early Return: Se o jogo já está em promoção, abortamos a predição, mas
    # comparamos o desconto atual com o maior já registrado no histórico ITAD.
    if var_dictSteamData.get("is_on_sale"):
        logger.info(f"Bypass de predição ativado para appid {var_intAppid} (Em promoção).")
        var_objHistoricoDesconto = None
        var_listWarningsSale = []
        try:
            var_listHistoricoSale = await ITADClient.get_price_history(
                var_intAppid, arg_floatPrecoBase=var_dictSteamData.get("price", 0.0)
            )
            if var_listHistoricoSale and any(var_dictPonto.get("fonte") == "mock" for var_dictPonto in var_listHistoricoSale):
                var_listWarningsSale.append("A API de histórico de preços (ITAD) está indisponível (chave ausente, limite de requisições ou erro de rede). O sistema está utilizando um histórico de preços simulado (mock) para a demonstração dos modelos de IA.")
            var_objHistoricoDesconto = _calcular_historico_desconto(
                var_listHistoricoSale, var_dictSteamData.get("discount_percent", 0)
            )
        except Exception as e:
            logger.warning(f"Falha ao buscar histórico para comparação de desconto (appid {var_intAppid}): {e}")

        return PredictionResponse(
            game=GameInfo(**var_dictSteamData),
            classificacao=None,
            regressao=None,
            historico_desconto=var_objHistoricoDesconto,
            features_utilizadas=None,
            warnings=var_listWarningsSale if var_listWarningsSale else None,
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
    # ITADClient sinaliza por item ("fonte": "mock"/"real") quando cai no fallback
    # simulado — cobre não só rate limit, mas também ITAD_API_KEY ausente e erros
    # de rede, que antes não geravam nenhum aviso ao cliente.
    if var_listHistorico and any(var_dictPonto.get("fonte") == "mock" for var_dictPonto in var_listHistorico):
        var_listWarnings.append("A API de histórico de preços (ITAD) está indisponível (chave ausente, limite de requisições ou erro de rede). O sistema está utilizando um histórico de preços simulado (mock) para a demonstração dos modelos de IA.")

    # Comparação com o desconto histórico (sempre exibida, não só quando já em promoção)
    var_objHistoricoDesconto = _calcular_historico_desconto(var_listHistorico, 0)

    # 4. Features
    var_dfFeatures = gerar_features_para_inferencia(
        arg_floatReviewScore=var_dictSteamData.get("review_score", 0),
        arg_floatPrecoCatalogo=var_floatPrice,
        arg_listHistoricoPrecos=var_listHistorico,
    )

    # 5. Hot-reload check & Dynamic Model Loading
    # joblib.load() é síncrono e pode envolver I/O de disco pesado (modelos com
    # centenas de MB) — roda em thread separada para não bloquear o event loop.
    await asyncio.to_thread(var_objModelManager.ensure_models_for_horizon, input_data.horizonte)

    # 6. Predição
    # predict()/predict_proba() são síncronos e potencialmente custosos (CPU) —
    # também rodam em thread separada.
    var_objClassificacao, var_objRegressao = await asyncio.to_thread(
        _executar_predicao, var_objModelManager, var_dfFeatures
    )

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
        historico_desconto=var_objHistoricoDesconto,
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

    var_objClassificacao, var_objRegressao = await asyncio.to_thread(
        _executar_predicao, var_objModelManager, var_dfFeatures
    )

    var_objGameInfo = GameInfo(appid=0, name="Input Manual")

    return PredictionResponse(
        game=var_objGameInfo,
        classificacao=var_objClassificacao,
        regressao=var_objRegressao,
        features_utilizadas=var_dictFeatures if debug else None,
    )


