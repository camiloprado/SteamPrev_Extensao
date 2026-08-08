"""Testes para o módulo de Feature Engineering."""

import pytest
import pandas as pd
from core.feature_engineering import (
    gerar_features_para_inferencia,
    calcular_dias_proxima_grande_promo,
    CON_LIST_FEATURE_COLUMNS,
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
        var_intResult = calcular_dias_proxima_grande_promo(360)
        assert var_intResult == (365 - 360) + 75  # 80 dias


class TestFeatureEngineering:
    """Testes para geração de features."""

    def test_sem_historico(self):
        var_dfResult = gerar_features_para_inferencia(
            arg_floatReviewScore=85.0,
            arg_floatPrecoCatalogo=99.99,
            arg_listHistoricoPrecos=[],
        )
        assert isinstance(var_dfResult, pd.DataFrame)
        assert len(var_dfResult) == 1
        assert list(var_dfResult.columns) == CON_LIST_FEATURE_COLUMNS

    def test_com_historico(self):
        import time
        var_intNow = int(time.time())
        var_listHistorico = [
            {"timestamp": var_intNow - 86400 * 100, "preco": 99.99, "desconto": 0},
            {"timestamp": var_intNow - 86400 * 60, "preco": 49.99, "desconto": 50},
            {"timestamp": var_intNow - 86400 * 30, "preco": 99.99, "desconto": 0},
            {"timestamp": var_intNow - 86400 * 5, "preco": 99.99, "desconto": 0},
        ]
        var_dfResult = gerar_features_para_inferencia(
            arg_floatReviewScore=90.0,
            arg_floatPrecoCatalogo=99.99,
            arg_listHistoricoPrecos=var_listHistorico,
        )
        assert isinstance(var_dfResult, pd.DataFrame)
        assert len(var_dfResult) == 1
        assert list(var_dfResult.columns) == CON_LIST_FEATURE_COLUMNS
        assert var_dfResult.iloc[0]["review_score"] == 90.0
        assert var_dfResult.iloc[0]["num_promocoes_janela"] >= 1

    def test_feature_columns_order(self):
        assert len(CON_LIST_FEATURE_COLUMNS) == 18
        assert CON_LIST_FEATURE_COLUMNS[0] == "review_score"
        assert CON_LIST_FEATURE_COLUMNS[-1] == "dias_para_proxima_grande_promo"
