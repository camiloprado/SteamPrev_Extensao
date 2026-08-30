"""
Script para gerar modelos dummy para desenvolvimento e testes.
Treina modelos XGBoost simples com dados sintéticos e exporta como .joblib
com a nomenclatura padronizada da Fábrica.

Uso:
    python scripts/generate_dummy_models.py
"""

import shutil
import numpy as np
import pandas as pd
import joblib
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from pathlib import Path


# Features (mesma ordem do treinamento real)
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

CON_LIST_HORIZONTES = ["30d", "60d", "90d"]
CON_DICT_CAP_DIAS = {"30d": 30, "60d": 60, "90d": 90}


def gerar_dados_sinteticos(arg_intNumSamples: int = 5000) -> pd.DataFrame:
    """
    Gera dados sintéticos realistas para treinamento.

    Parâmetros:
    - arg_intNumSamples (int): Número de amostras a gerar.

    Retorna:
    - pd.DataFrame: DataFrame com dados sintéticos e alvos.
    """
    np.random.seed(42)

    var_dictData = {
        "review_score": np.random.uniform(30, 100, arg_intNumSamples),
        "preco_catalogo": np.random.uniform(10, 300, arg_intNumSamples),
        "preco_zscore_janela": np.random.normal(0, 1, arg_intNumSamples),
        "preco_media_janela": np.random.uniform(10, 250, arg_intNumSamples),
        "preco_std_janela": np.random.uniform(0, 50, arg_intNumSamples),
        "preco_min_janela": np.random.uniform(5, 150, arg_intNumSamples),
        "preco_max_janela": np.random.uniform(50, 350, arg_intNumSamples),
        "frequencia_descontos_por_ano": np.random.uniform(0, 15, arg_intNumSamples),
        "dias_no_preco_atual": np.random.randint(0, 365, arg_intNumSamples),
        "ratio_preco_atual_vs_minimo": np.random.uniform(1.0, 5.0, arg_intNumSamples),
        "desconto_medio_janela": np.random.uniform(0, 50, arg_intNumSamples),
        "desconto_max_janela": np.random.uniform(0, 80, arg_intNumSamples),
        "num_promocoes_janela": np.random.randint(0, 30, arg_intNumSamples),
        "dias_janela": np.random.randint(30, 1800, arg_intNumSamples),
        "dias_desde_ultimo_desconto": np.random.randint(0, 9999, arg_intNumSamples),
        "mes_atual": np.random.randint(1, 13, arg_intNumSamples),
        "dia_do_ano": np.random.randint(1, 366, arg_intNumSamples),
        "dias_para_proxima_grande_promo": np.random.randint(0, 200, arg_intNumSamples),
    }

    var_dfDados = pd.DataFrame(var_dictData)

    var_serScore = (
        var_dfDados["frequencia_descontos_por_ano"] * 0.3
        - var_dfDados["dias_para_proxima_grande_promo"] * 0.01
        + var_dfDados["desconto_max_janela"] * 0.02
        - var_dfDados["dias_desde_ultimo_desconto"] * 0.001
        + np.random.normal(0, 0.5, arg_intNumSamples)
    )
    var_dfDados["alvo_classificacao"] = pd.cut(var_serScore, bins=3, labels=[0, 1, 2]).astype(int)

    var_serDiasBruto = (
        var_dfDados["dias_desde_ultimo_desconto"] * 0.3
        + var_dfDados["dias_para_proxima_grande_promo"] * 0.5
        - var_dfDados["frequencia_descontos_por_ano"] * 5
        + np.random.normal(0, 20, arg_intNumSamples)
    )
    for var_strHorizonte, var_intCap in CON_DICT_CAP_DIAS.items():
        var_dfDados[f"alvo_regressao_dias_{var_strHorizonte}"] = np.clip(
            var_serDiasBruto, 0, var_intCap
        ).astype(int)

    var_dfDados["alvo_regressao_desconto"] = np.clip(
        var_dfDados["desconto_medio_janela"] * 0.6
        + var_dfDados["desconto_max_janela"] * 0.3
        + np.random.normal(0, 5, arg_intNumSamples),
        0, 100
    )

    return var_dfDados


def main():
    """Gera e salva os modelos dummy com nomenclatura padronizada."""
    var_pathOutputDir = Path(__file__).resolve().parents[1] / "resources" / "models"
    var_pathOutputDir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Gerando Modelos Dummy para Previsor Steam")
    print("=" * 60)

    var_dfDados = gerar_dados_sinteticos(5000)
    var_dfX = var_dfDados[CON_LIST_FEATURE_COLUMNS]
    var_serYClassificacao = var_dfDados["alvo_classificacao"]
    var_serYDesconto = var_dfDados["alvo_regressao_desconto"]

    print(f"Dados gerados: {len(var_dfDados)} amostras, {len(CON_LIST_FEATURE_COLUMNS)} features")

    print("\nTreinando modelo de classificacao (XGBoost)...")
    var_objClassificador = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        eval_metric="mlogloss",
    )
    var_objClassificador.fit(var_dfX, var_serYClassificacao)

    print("\nTreinando modelo de regressao de desconto (XGBoost)...")
    var_objRegressorDesconto = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
    )
    var_objRegressorDesconto.fit(var_dfX, var_serYDesconto)

    for var_strHorizonte in CON_LIST_HORIZONTES:
        var_pathClassificacao = var_pathOutputDir / f"modelo_classificacao_{var_strHorizonte}.joblib"
        joblib.dump(var_objClassificador, var_pathClassificacao)
        print(f"   Salvo: {var_pathClassificacao.name}")

        print(f"\nTreinando regressao de dias ({var_strHorizonte})...")
        var_objRegressorDias = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
        )
        var_objRegressorDias.fit(var_dfX, var_dfDados[f"alvo_regressao_dias_{var_strHorizonte}"])
        var_pathRegressaoDias = var_pathOutputDir / f"modelo_regressao_dias_{var_strHorizonte}.joblib"
        joblib.dump(var_objRegressorDias, var_pathRegressaoDias)
        print(f"   Salvo: {var_pathRegressaoDias.name}")

        var_pathRegressaoDesconto = var_pathOutputDir / f"modelo_regressao_desconto_{var_strHorizonte}.joblib"
        joblib.dump(var_objRegressorDesconto, var_pathRegressaoDesconto)
        print(f"   Salvo: {var_pathRegressaoDesconto.name}")

    var_pathLatest = var_pathOutputDir / "modelo_latest.joblib"
    shutil.copy2(var_pathOutputDir / "modelo_classificacao_30d.joblib", var_pathLatest)
    print(f"   Alias: {var_pathLatest.name} -> modelo_classificacao_30d.joblib")

    print("\nGerando pipeline de escalonamento...")
    var_objScaler = StandardScaler()
    var_objScaler.fit(var_dfX)
    var_pathPipeline = var_pathOutputDir / "pipeline_escalonamento.joblib"
    joblib.dump(var_objScaler, var_pathPipeline)
    print(f"   Salvo: {var_pathPipeline.name}")

    print("\n" + "=" * 60)
    print("Todos os modelos dummy foram gerados com sucesso!")
    print(f"   Diretorio: {var_pathOutputDir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
