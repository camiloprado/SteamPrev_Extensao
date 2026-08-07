"""
Módulo de Feature Engineering para inferência.
Replica a lógica de geração de features do projeto base (NormalizarModelos)
para uso em tempo real na API de inferência.

Features reais (17 features, na ordem esperada pelo modelo):
    review_score, preco_catalogo, preco_atual_hist,
    preco_media_janela, preco_std_janela, preco_min_janela, preco_max_janela,
    frequencia_descontos_por_ano, dias_no_preco_atual, ratio_preco_atual_vs_minimo,
    desconto_medio_janela, desconto_max_janela, num_promocoes_janela,
    dias_janela, dias_desde_ultimo_desconto,
    mes_atual, dia_do_ano, dias_para_proxima_grande_promo
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger("core.features")

# Ordem exata das features usadas no treinamento
FEATURE_COLUMNS = [
    "review_score",
    "preco_catalogo",
    "preco_atual_hist",
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
LABEL_MAP_CLASSIFICACAO = {0: "cai", 1: "mantem", 2: "sobe"}
LABEL_MAP_CLASSIFICACAO_EMOJI = {0: "📉 Cai", 1: "➡️ Mantém", 2: "📈 Sobe"}

# Datas fixas das grandes promoções Steam (Day of Year)
GRANDES_PROMOCOES_DOY = [75, 177, 327, 355]  # Spring, Summer, Autumn, Winter


def calcular_dias_proxima_grande_promo(dia_do_ano: int) -> int:
    """
    Calcula distância em dias até a próxima grande promoção Steam.

    Parâmetros:
    - dia_do_ano (int): Dia do ano (1-366).

    Retorna:
    - int: Dias até a próxima grande promoção.
    """
    dias_prox = 999
    for dia_promo in GRANDES_PROMOCOES_DOY:
        if dia_promo >= dia_do_ano:
            dias_prox = min(dias_prox, dia_promo - dia_do_ano)

    # Se passou de todas, próxima é Spring do ano que vem
    if dias_prox == 999:
        dias_prox = (365 - dia_do_ano) + 75

    return dias_prox


def gerar_features_para_inferencia(
    review_score: float,
    preco_catalogo: float,
    historico_precos: list[dict],
) -> pd.DataFrame:
    """
    Gera o DataFrame de features para inferência a partir dos dados brutos do jogo.

    Replica a lógica de _construir_amostras_temporais do projeto base,
    mas para um único ponto temporal (agora).

    Parâmetros:
    - review_score (float): Score de reviews do jogo (0-100).
    - preco_catalogo (float): Preço atual no catálogo da Steam.
    - historico_precos (list[dict]): Lista de pontos {timestamp, preco, desconto}
      ordenados cronologicamente.

    Retorna:
    - pd.DataFrame: DataFrame com 1 linha e as 18 features na ordem correta.
    """
    agora = datetime.now()
    timestamp_agora = int(agora.timestamp())
    mes_atual = agora.month
    dia_do_ano = agora.timetuple().tm_yday
    dias_prox_promo = calcular_dias_proxima_grande_promo(dia_do_ano)

    # Se não há histórico, usa valores padrão baseados no preço do catálogo
    if not historico_precos or len(historico_precos) == 0:
        features = {
            "review_score": float(review_score) if review_score else 0.0,
            "preco_catalogo": float(preco_catalogo) if preco_catalogo else 0.0,
            "preco_atual_hist": float(preco_catalogo) if preco_catalogo else 0.0,
            "preco_media_janela": float(preco_catalogo) if preco_catalogo else 0.0,
            "preco_std_janela": 0.0,
            "preco_min_janela": float(preco_catalogo) if preco_catalogo else 0.0,
            "preco_max_janela": float(preco_catalogo) if preco_catalogo else 0.0,
            "frequencia_descontos_por_ano": 0.0,
            "dias_no_preco_atual": 0,
            "ratio_preco_atual_vs_minimo": 1.0,
            "desconto_medio_janela": 0.0,
            "desconto_max_janela": 0.0,
            "num_promocoes_janela": 0,
            "dias_janela": 0,
            "dias_desde_ultimo_desconto": 9999,
            "mes_atual": mes_atual,
            "dia_do_ano": dia_do_ano,
            "dias_para_proxima_grande_promo": dias_prox_promo,
        }
        return pd.DataFrame([features])[FEATURE_COLUMNS]

    # ── Janela de 5 anos (mesma do treinamento) ──
    janela_segundos = 5 * 365 * 86400
    timestamp_limite = timestamp_agora - janela_segundos

    janela = [
        p for p in historico_precos
        if p.get("timestamp", 0) >= timestamp_limite
    ]

    if not janela:
        janela = historico_precos[-10:]  # Fallback: últimos 10 pontos

    precos_janela = [float(p["preco"]) for p in janela]
    descontos_janela = [float(p.get("desconto", 0)) for p in janela]
    timestamps_janela = [int(p["timestamp"]) for p in janela]

    # Preço atual = último ponto sem desconto, ou o mais recente
    preco_atual = preco_catalogo
    for p in reversed(janela):
        if p.get("desconto", 0) == 0 and p.get("preco", 0) > 0:
            preco_atual = float(p["preco"])
            break

    # Dias desde último desconto
    dias_desde_ultimo_desconto = 9999
    for p in reversed(janela):
        if p.get("desconto", 0) > 0:
            dias_desde_ultimo_desconto = max(0, int(
                (timestamp_agora - p["timestamp"]) / 86400
            ))
            break

    # Dias no preço atual (estabilidade)
    dias_no_preco_atual = 0
    for p in reversed(historico_precos):
        if p.get("preco", 0) > 0 and abs(p["preco"] - preco_atual) / max(preco_atual, 0.01) < 0.01:
            dias_no_preco_atual = max(0, int(
                (timestamp_agora - p["timestamp"]) / 86400
            ))
        else:
            break

    # Frequência de descontos por ano
    total_descontos = sum(1 for d in descontos_janela if d > 0)
    dias_janela = max(1, int(
        (timestamps_janela[-1] - timestamps_janela[0]) / 86400
    )) if len(timestamps_janela) > 1 else 1
    freq_descontos_ano = (total_descontos / dias_janela) * 365 if dias_janela > 0 else 0.0

    # Ratio preço atual vs mínimo
    preco_min = float(np.min(precos_janela))
    ratio_vs_min = preco_atual / preco_min if preco_min > 0 else 1.0

    features = {
        "review_score": float(review_score) if review_score else 0.0,
        "preco_catalogo": float(preco_catalogo) if preco_catalogo else 0.0,
        "preco_atual_hist": float(preco_atual),
        "preco_media_janela": float(np.mean(precos_janela)),
        "preco_std_janela": float(np.std(precos_janela)),
        "preco_min_janela": float(preco_min),
        "preco_max_janela": float(np.max(precos_janela)),
        "frequencia_descontos_por_ano": float(freq_descontos_ano),
        "dias_no_preco_atual": int(dias_no_preco_atual),
        "ratio_preco_atual_vs_minimo": float(ratio_vs_min),
        "desconto_medio_janela": float(np.mean(descontos_janela)),
        "desconto_max_janela": float(np.max(descontos_janela)),
        "num_promocoes_janela": int(total_descontos),
        "dias_janela": int(dias_janela),
        "dias_desde_ultimo_desconto": int(dias_desde_ultimo_desconto),
        "mes_atual": int(mes_atual),
        "dia_do_ano": int(dia_do_ano),
        "dias_para_proxima_grande_promo": int(dias_prox_promo),
    }

    return pd.DataFrame([features])[FEATURE_COLUMNS]
