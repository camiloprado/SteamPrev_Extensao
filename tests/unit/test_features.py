"""Testes para o módulo de Feature Engineering."""

import pytest
import pandas as pd
from core.feature_engineering import (
    gerar_features_para_inferencia,
    calcular_dias_proxima_grande_promo,
    CON_LIST_FEATURE_COLUMNS,
    CON_LIST_GRANDES_PROMOCOES_DOY,
)


class TestDiasProxPromo:
    """Testes para cálculo de dias até próxima promoção. Deriva de CON_LIST_GRANDES_PROMOCOES_DOY em vez de hardcode para não ficar desatualizado se o calendário mudar de novo."""

    def test_antes_spring(self):
        var_intSpring = CON_LIST_GRANDES_PROMOCOES_DOY[0]
        assert calcular_dias_proxima_grande_promo(50) == var_intSpring - 50

    def test_entre_summer_autumn(self):
        var_intAutumn = CON_LIST_GRANDES_PROMOCOES_DOY[2]
        assert calcular_dias_proxima_grande_promo(200) == var_intAutumn - 200

    def test_apos_todas(self):
        var_intResult = calcular_dias_proxima_grande_promo(360)
        assert var_intResult == (365 - 360) + min(CON_LIST_GRANDES_PROMOCOES_DOY)


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

    def test_dias_no_preco_atual_cap_janela_5_anos(self):
        import time
        from core.feature_engineering import CON_INT_ANOS_EFETIVOS

        var_intNow = int(time.time())
        var_intDiasDentroDaJanela = CON_INT_ANOS_EFETIVOS * 365 - 10
        var_listHistorico = [
            {"timestamp": var_intNow - 86400 * 365 * 8, "preco": 59.99, "desconto": 0},
            {"timestamp": var_intNow - 86400 * var_intDiasDentroDaJanela, "preco": 59.99, "desconto": 0},
            {"timestamp": var_intNow - 86400, "preco": 59.99, "desconto": 0},
        ]
        var_dfResult = gerar_features_para_inferencia(
            arg_floatReviewScore=90.0,
            arg_floatPrecoCatalogo=59.99,
            arg_listHistoricoPrecos=var_listHistorico,
        )
        var_intDias = int(var_dfResult.iloc[0]["dias_no_preco_atual"])
        assert var_intDias <= CON_INT_ANOS_EFETIVOS * 365
        assert var_intDias < 365 * 8
        assert var_intDias >= var_intDiasDentroDaJanela - 2

    def test_feature_columns_order(self):
        assert len(CON_LIST_FEATURE_COLUMNS) == 18
        assert CON_LIST_FEATURE_COLUMNS[0] == "review_score"
        assert CON_LIST_FEATURE_COLUMNS[-1] == "dias_para_proxima_grande_promo"
