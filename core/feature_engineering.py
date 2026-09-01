"""
Módulo de Feature Engineering para inferência.
Replica a lógica de geração de features do projeto base (NormalizarModelos)
para uso em tempo real na API de inferência.

Features reais (18 features, na ordem esperada pelo modelo):
    review_score, preco_catalogo, preco_zscore_janela,
    preco_media_janela, preco_std_janela, preco_min_janela, preco_max_janela,
    frequencia_descontos_por_ano, dias_no_preco_atual, ratio_preco_atual_vs_minimo,
    desconto_medio_janela, desconto_max_janela, num_promocoes_janela,
    dias_janela, dias_desde_ultimo_desconto,
    mes_atual, dia_do_ano, dias_para_proxima_grande_promo
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger("core.features")

# ── Configuração da janela histórica (espelha NormalizarModelos do projeto base) ──
# ML_JANELA_ANOS (int)  → anos de histórico para cálculo de features (padrão: 5).
# ML_JANELA_EXTENDIDA (bool) → quando True, dobra a janela para ciclos históricos mais longos.
CON_INT_JANELA_ANOS: int = int(os.getenv("ML_JANELA_ANOS", "5"))
CON_BOOL_JANELA_EXTENDIDA: bool = str(os.getenv("ML_JANELA_EXTENDIDA", "False")).lower() in ("true", "1", "yes")
CON_INT_ANOS_EFETIVOS: int = CON_INT_JANELA_ANOS * 2 if CON_BOOL_JANELA_EXTENDIDA else CON_INT_JANELA_ANOS

# Ordem exata das features usadas no treinamento
CON_LIST_FEATURE_COLUMNS = [
    "review_score",
    "preco_catalogo",
    "preco_zscore_janela",
    "preco_media_janela",
    "preco_std_janela",
    "preco_min_janela",
    "preco_max_janela",
    "frequencia_descontos_por_ano",
    "dias_no_preco_atual",
    "ratio_preco_atual_vs_minimo",
    "desconto_medio_janela",
    "desconto_max_janela",
    "num_promocoes_janela",
    "dias_janela",
    "dias_desde_ultimo_desconto",
    "mes_atual",
    "dia_do_ano",
    "dias_para_proxima_grande_promo",
]

# Mapeamento de rótulos: saída do modelo → texto legível
CON_DICT_LABEL_MAP_CLASSIFICACAO = {0: "cai", 1: "mantem", 2: "sobe"}
CON_DICT_LABEL_MAP_CLASSIFICACAO_EMOJI = {0: "📉 Cai", 1: "➡️ Mantém", 2: "📈 Sobe"}

# Mediana empírica (2022-2025) derivada do histórico real de descontos na Fábrica —
# substitui a suposição de datas fixas, que divergia até 28 dias no slot de Outono.
CON_LIST_GRANDES_PROMOCOES_DOY = [67, 174, 299, 348]  # Spring, Summer, Autumn, Winter


def validar_features_modelo(arg_objModelo) -> list[str] | None:
    """
    Compara as features que o modelo espera (feature_names_in_, exposto por
    sklearn/XGBoost quando treinados com um DataFrame) contra CON_LIST_FEATURE_COLUMNS.

    Detecta o cenário que já aconteceu em produção: a Fábrica troca uma feature
    (ex.: preco_atual_hist → preco_zscore_janela) e o código de inferência da
    Extensão fica desatualizado — toda predição falha silenciosamente (None),
    sem nada visível no /health.

    Parâmetros:
    - arg_objModelo: modelo .joblib carregado (classificação ou regressão).

    Retorna:
    - list[str] | None: lista de features que o MODELO espera, se diferente de
      CON_LIST_FEATURE_COLUMNS; None se compatível ou se o modelo não expõe
      feature_names_in_ (não há como validar nesse caso).
    """
    var_listEsperadoPeloModelo = getattr(arg_objModelo, "feature_names_in_", None)
    if var_listEsperadoPeloModelo is None:
        return None
    var_listEsperadoPeloModelo = list(var_listEsperadoPeloModelo)
    if var_listEsperadoPeloModelo != CON_LIST_FEATURE_COLUMNS:
        return var_listEsperadoPeloModelo
    return None


def calcular_dias_proxima_grande_promo(arg_intDiaDoAno: int) -> int:
    """
    Calcula distância em dias até a próxima grande promoção Steam.

    Parâmetros:
    - arg_intDiaDoAno (int): Dia do ano (1-366).

    Retorna:
    - int: Dias até a próxima grande promoção.
    """
    var_intDiasProx = 999
    for var_intDiaPromo in CON_LIST_GRANDES_PROMOCOES_DOY:
        if var_intDiaPromo >= arg_intDiaDoAno:
            var_intDiasProx = min(var_intDiasProx, var_intDiaPromo - arg_intDiaDoAno)

    # Se passou de todas, próxima é a primeira do ano que vem
    if var_intDiasProx == 999:
        var_intDiasProx = (365 - arg_intDiaDoAno) + min(CON_LIST_GRANDES_PROMOCOES_DOY)

    return var_intDiasProx


def gerar_features_para_inferencia(
    arg_floatReviewScore: float,
    arg_floatPrecoCatalogo: float,
    arg_listHistoricoPrecos: list[dict],
) -> pd.DataFrame:
    """
    Gera o DataFrame de features para inferência a partir dos dados brutos do jogo.

    Replica a lógica de _construir_amostras_temporais do projeto base,
    mas para um único ponto temporal (agora).

    Parâmetros:
    - arg_floatReviewScore (float): Score de reviews do jogo (0-100).
    - arg_floatPrecoCatalogo (float): Preço atual no catálogo da Steam.
    - arg_listHistoricoPrecos (list[dict]): Lista de pontos {timestamp, preco, desconto}
      ordenados cronologicamente.

    Retorna:
    - pd.DataFrame: DataFrame com 1 linha e as 18 features na ordem correta.
    """
    var_dtAgora = datetime.now()
    var_intTimestampAgora = int(var_dtAgora.timestamp())
    var_intMesAtual = var_dtAgora.month
    var_intDiaDoAno = var_dtAgora.timetuple().tm_yday
    var_intDiasProxPromo = calcular_dias_proxima_grande_promo(var_intDiaDoAno)

    # Se não há histórico, usa valores padrão baseados no preço do catálogo
    if not arg_listHistoricoPrecos or len(arg_listHistoricoPrecos) == 0:
        var_dictFeatures = {
            "review_score": float(arg_floatReviewScore) if arg_floatReviewScore else 0.0,
            "preco_catalogo": float(arg_floatPrecoCatalogo) if arg_floatPrecoCatalogo else 0.0,
            "preco_zscore_janela": 0.0,
            "preco_media_janela": float(arg_floatPrecoCatalogo) if arg_floatPrecoCatalogo else 0.0,
            "preco_std_janela": 0.0,
            "preco_min_janela": float(arg_floatPrecoCatalogo) if arg_floatPrecoCatalogo else 0.0,
            "preco_max_janela": float(arg_floatPrecoCatalogo) if arg_floatPrecoCatalogo else 0.0,
            "frequencia_descontos_por_ano": 0.0,
            "dias_no_preco_atual": 0,
            "ratio_preco_atual_vs_minimo": 1.0,
            "desconto_medio_janela": 0.0,
            "desconto_max_janela": 0.0,
            "num_promocoes_janela": 0,
            "dias_janela": 0,
            "dias_desde_ultimo_desconto": 9999,
            "mes_atual": var_intMesAtual,
            "dia_do_ano": var_intDiaDoAno,
            "dias_para_proxima_grande_promo": var_intDiasProxPromo,
        }
        return pd.DataFrame([var_dictFeatures])[CON_LIST_FEATURE_COLUMNS]

    # ── Janela de anos configurada via env (espelha NormalizarModelos) ──
    var_intJanelaSegundos = CON_INT_ANOS_EFETIVOS * 365 * 86400
    var_intTimestampLimite = var_intTimestampAgora - var_intJanelaSegundos

    var_listJanela = [
        var_dictPonto for var_dictPonto in arg_listHistoricoPrecos
        if var_dictPonto.get("timestamp", 0) >= var_intTimestampLimite
    ]

    if not var_listJanela:
        var_listJanela = arg_listHistoricoPrecos[-10:]  # Fallback: últimos 10 pontos

    var_listPrecosJanela = [float(var_dictPonto["preco"]) for var_dictPonto in var_listJanela]
    var_listDescontosJanela = [float(var_dictPonto.get("desconto", 0)) for var_dictPonto in var_listJanela]
    var_listTimestampsJanela = [int(var_dictPonto["timestamp"]) for var_dictPonto in var_listJanela]

    # Preço atual = último ponto sem desconto, ou o mais recente
    var_floatPrecoAtual = arg_floatPrecoCatalogo
    for var_dictPonto in reversed(var_listJanela):
        if var_dictPonto.get("desconto", 0) == 0 and var_dictPonto.get("preco", 0) > 0:
            var_floatPrecoAtual = float(var_dictPonto["preco"])
            break

    # Dias desde último desconto
    var_intDiasDesdeUltimoDesconto = 9999
    for var_dictPonto in reversed(var_listJanela):
        if var_dictPonto.get("desconto", 0) > 0:
            var_intDiasDesdeUltimoDesconto = max(0, int(
                (var_intTimestampAgora - var_dictPonto["timestamp"]) / 86400
            ))
            break

    # Dias no preço atual (estabilidade) — cap pela janela configurada (paridade com normalizar_modelos.py)
    var_intTimestampLimiteNoPreco = var_intTimestampAgora - var_intJanelaSegundos
    var_intDiasNoPrecoAtual = 0
    for var_dictPonto in reversed(arg_listHistoricoPrecos):
        # Para ao ultrapassar o limite da janela
        if var_dictPonto.get("timestamp", 0) < var_intTimestampLimiteNoPreco:
            break
        if var_dictPonto.get("preco", 0) > 0 and abs(var_dictPonto["preco"] - var_floatPrecoAtual) / max(var_floatPrecoAtual, 0.01) < 0.01:
            var_intDiasNoPrecoAtual = max(0, int(
                (var_intTimestampAgora - var_dictPonto["timestamp"]) / 86400
            ))
        else:
            break

    # Frequência de descontos por ano
    var_intTotalDescontos = sum(1 for var_floatDesconto in var_listDescontosJanela if var_floatDesconto > 0)
    var_intDiasJanela = max(1, int(
        (var_listTimestampsJanela[-1] - var_listTimestampsJanela[0]) / 86400
    )) if len(var_listTimestampsJanela) > 1 else 1
    var_floatFreqDescontosAno = (var_intTotalDescontos / var_intDiasJanela) * 365 if var_intDiasJanela > 0 else 0.0

    # Ratio preço atual vs mínimo
    var_floatPrecoMin = float(np.min(var_listPrecosJanela))
    var_floatRatioVsMin = var_floatPrecoAtual / var_floatPrecoMin if var_floatPrecoMin > 0 else 1.0

    # Quão atípico o preço atual é frente à própria janela do jogo (escala relativa,
    # não sofre com o drift de preço absoluto do catálogo ao longo do tempo).
    var_floatMediaJanela = float(np.mean(var_listPrecosJanela))
    var_floatStdJanela = float(np.std(var_listPrecosJanela))
    var_floatZscorePreco = (var_floatPrecoAtual - var_floatMediaJanela) / var_floatStdJanela if var_floatStdJanela > 0 else 0.0

    var_dictFeatures = {
        "review_score": float(arg_floatReviewScore) if arg_floatReviewScore else 0.0,
        "preco_catalogo": float(arg_floatPrecoCatalogo) if arg_floatPrecoCatalogo else 0.0,
        "preco_zscore_janela": float(var_floatZscorePreco),
        "preco_media_janela": var_floatMediaJanela,
        "preco_std_janela": var_floatStdJanela,
        "preco_min_janela": float(var_floatPrecoMin),
        "preco_max_janela": float(np.max(var_listPrecosJanela)),
        "frequencia_descontos_por_ano": float(var_floatFreqDescontosAno),
        "dias_no_preco_atual": int(var_intDiasNoPrecoAtual),
        "ratio_preco_atual_vs_minimo": float(var_floatRatioVsMin),
        "desconto_medio_janela": float(np.mean(var_listDescontosJanela)),
        "desconto_max_janela": float(np.max(var_listDescontosJanela)),
        "num_promocoes_janela": int(var_intTotalDescontos),
        "dias_janela": int(var_intDiasJanela),
        "dias_desde_ultimo_desconto": int(var_intDiasDesdeUltimoDesconto),
        "mes_atual": int(var_intMesAtual),
        "dia_do_ano": int(var_intDiaDoAno),
        "dias_para_proxima_grande_promo": int(var_intDiasProxPromo),
    }

    return pd.DataFrame([var_dictFeatures])[CON_LIST_FEATURE_COLUMNS]
