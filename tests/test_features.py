"""Testes para o módulo de Feature Engineering."""

import pytest
import pandas as pd
from core.feature_engineering import (
    gerar_features_para_inferencia,
    calcular_dias_proxima_grande_promo,
    FEATURE_COLUMNS,
)


class TestDiasProxPromo:
    """Testes para cálculo de dias até próxima promoção."""

    def test_antes_spring(self):
        # Dia 50, Spring é dia 75 → 25 dias
        assert calcular_dias_proxima_grande_promo(50) == 25

    def test_entre_summer_autumn(self):
        # Dia 200, Autumn é dia 327 → 127 dias
        assert calcular_dias_proxima_grande_promo(200) == 127

    def test_apos_todas(self):
        # Dia 360, próxima é Spring (dia 75) do próximo ano
        result = calcular_dias_proxima_grande_promo(360)
        assert result == (365 - 360) + 75  # 80 dias


class TestFeatureEngineering:
    """Testes para geração de features."""

    def test_sem_historico(self):
        df = gerar_features_para_inferencia(
            review_score=85.0,
            preco_catalogo=99.99,
            historico_precos=[],
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert list(df.columns) == FEATURE_COLUMNS

    def test_com_historico(self):
        import time
        now = int(time.time())
        historico = [
            {"timestamp": now - 86400 * 100, "preco": 99.99, "desconto": 0},
            {"timestamp": now - 86400 * 60, "preco": 49.99, "desconto": 50},
            {"timestamp": now - 86400 * 30, "preco": 99.99, "desconto": 0},
            {"timestamp": now - 86400 * 5, "preco": 99.99, "desconto": 0},
        ]
        df = gerar_features_para_inferencia(
            review_score=90.0,
            preco_catalogo=99.99,
            historico_precos=historico,
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert list(df.columns) == FEATURE_COLUMNS
        assert df.iloc[0]["review_score"] == 90.0
        assert df.iloc[0]["num_promocoes_janela"] >= 1

    def test_feature_columns_order(self):
        assert len(FEATURE_COLUMNS) == 18
        assert FEATURE_COLUMNS[0] == "review_score"
        assert FEATURE_COLUMNS[-1] == "dias_para_proxima_grande_promo"
