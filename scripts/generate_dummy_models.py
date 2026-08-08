"""
Script para gerar modelos dummy para desenvolvimento e testes.
Treina modelos XGBoost simples com dados sintéticos e exporta como .joblib.

Uso:
    python scripts/generate_dummy_models.py
"""

import numpy as np
import pandas as pd
import joblib
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from pathlib import Path


# Features (mesma ordem do treinamento real)
CON_LIST_FEATURE_COLUMNS = [
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
        "preco_atual_hist": np.random.uniform(10, 300, arg_intNumSamples),
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

    # Alvo classificação: lógica simples baseada em features
    # Mais promoções + perto de sale sazonal → mais chance de "cai"
    var_serScore = (
        var_dfDados["frequencia_descontos_por_ano"] * 0.3
        - var_dfDados["dias_para_proxima_grande_promo"] * 0.01
        + var_dfDados["desconto_max_janela"] * 0.02
        - var_dfDados["dias_desde_ultimo_desconto"] * 0.001
        + np.random.normal(0, 0.5, arg_intNumSamples)
    )
    var_dfDados["alvo_classificacao"] = pd.cut(var_serScore, bins=3, labels=[0, 1, 2]).astype(int)

    # Alvo regressão: dias até próximo desconto
    var_dfDados["alvo_regressao"] = np.clip(
        var_dfDados["dias_desde_ultimo_desconto"] * 0.3
        + var_dfDados["dias_para_proxima_grande_promo"] * 0.5
        - var_dfDados["frequencia_descontos_por_ano"] * 5
        + np.random.normal(0, 20, arg_intNumSamples),
        0, 365
    ).astype(int)

    return var_dfDados


def main():
    """Gera e salva os modelos dummy."""
    var_pathOutputDir = Path(__file__).resolve().parents[1] / "resources" / "models"
    var_pathOutputDir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("🏭 Gerando Modelos Dummy para Previsor Steam")
    print("=" * 60)

    # Gera dados
    var_dfDados = gerar_dados_sinteticos(5000)
    var_dfX = var_dfDados[CON_LIST_FEATURE_COLUMNS]
    var_serYClassificacao = var_dfDados["alvo_classificacao"]
    var_serYRegressao = var_dfDados["alvo_regressao"]

    print(f"✅ Dados gerados: {len(var_dfDados)} amostras, {len(CON_LIST_FEATURE_COLUMNS)} features")

    # ── Classificação XGBoost ──
    print("\n📊 Treinando modelo de classificação (XGBoost)...")
    var_objClassificador = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        use_label_encoder=False,
        eval_metric="mlogloss",
    )
    var_objClassificador.fit(var_dfX, var_serYClassificacao)
    var_pathClassificacao = var_pathOutputDir / "modelo_classificacao_XGBoost_latest.joblib"
    joblib.dump(var_objClassificador, var_pathClassificacao)
    print(f"   ✅ Salvo: {var_pathClassificacao}")

    # ── Regressão XGBoost ──
    print("\n📈 Treinando modelo de regressão (XGBoost)...")
    var_objRegressor = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
    )
    var_objRegressor.fit(var_dfX, var_serYRegressao)
    var_pathRegressao = var_pathOutputDir / "modelo_regressao_XGBoost_latest.joblib"
    joblib.dump(var_objRegressor, var_pathRegressao)
    print(f"   ✅ Salvo: {var_pathRegressao}")

    # ── Pipeline de escalonamento ──
    print("\n⚙️ Gerando pipeline de escalonamento...")
    var_objScaler = StandardScaler()
    var_objScaler.fit(var_dfX)
    var_pathPipeline = var_pathOutputDir / "pipeline_escalonamento.joblib"
    joblib.dump(var_objScaler, var_pathPipeline)
    print(f"   ✅ Salvo: {var_pathPipeline}")

    print("\n" + "=" * 60)
    print("✅ Todos os modelos dummy foram gerados com sucesso!")
    print(f"   Diretório: {var_pathOutputDir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
