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


def generate_synthetic_data(n_samples: int = 5000) -> pd.DataFrame:
    """Gera dados sintéticos realistas para treinamento."""
    np.random.seed(42)

    data = {
        "review_score": np.random.uniform(30, 100, n_samples),
        "preco_catalogo": np.random.uniform(10, 300, n_samples),
        "preco_atual_hist": np.random.uniform(10, 300, n_samples),
        "preco_media_janela": np.random.uniform(10, 250, n_samples),
        "preco_std_janela": np.random.uniform(0, 50, n_samples),
        "preco_min_janela": np.random.uniform(5, 150, n_samples),
        "preco_max_janela": np.random.uniform(50, 350, n_samples),
        "frequencia_descontos_por_ano": np.random.uniform(0, 15, n_samples),
        "dias_no_preco_atual": np.random.randint(0, 365, n_samples),
        "ratio_preco_atual_vs_minimo": np.random.uniform(1.0, 5.0, n_samples),
        "desconto_medio_janela": np.random.uniform(0, 50, n_samples),
        "desconto_max_janela": np.random.uniform(0, 80, n_samples),
        "num_promocoes_janela": np.random.randint(0, 30, n_samples),
        "dias_janela": np.random.randint(30, 1800, n_samples),
        "dias_desde_ultimo_desconto": np.random.randint(0, 9999, n_samples),
        "mes_atual": np.random.randint(1, 13, n_samples),
        "dia_do_ano": np.random.randint(1, 366, n_samples),
        "dias_para_proxima_grande_promo": np.random.randint(0, 200, n_samples),
    }

    df = pd.DataFrame(data)

    # Alvo classificação: lógica simples baseada em features
    # Mais promoções + perto de sale sazonal → mais chance de "cai"
    score = (
        df["frequencia_descontos_por_ano"] * 0.3
        - df["dias_para_proxima_grande_promo"] * 0.01
        + df["desconto_max_janela"] * 0.02
        - df["dias_desde_ultimo_desconto"] * 0.001
        + np.random.normal(0, 0.5, n_samples)
    )
    df["alvo_classificacao"] = pd.cut(score, bins=3, labels=[0, 1, 2]).astype(int)

    # Alvo regressão: dias até próximo desconto
    df["alvo_regressao"] = np.clip(
        df["dias_desde_ultimo_desconto"] * 0.3
        + df["dias_para_proxima_grande_promo"] * 0.5
        - df["frequencia_descontos_por_ano"] * 5
        + np.random.normal(0, 20, n_samples),
        0, 365
    ).astype(int)

    return df


def main():
    """Gera e salva os modelos dummy."""
    output_dir = Path(__file__).resolve().parents[1] / "resources" / "models"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("🏭 Gerando Modelos Dummy para Previsor Steam")
    print("=" * 60)

    # Gera dados
    df = generate_synthetic_data(5000)
    X = df[FEATURE_COLUMNS]
    y_clf = df["alvo_classificacao"]
    y_reg = df["alvo_regressao"]

    print(f"✅ Dados gerados: {len(df)} amostras, {len(FEATURE_COLUMNS)} features")

    # ── Classificação XGBoost ──
    print("\n📊 Treinando modelo de classificação (XGBoost)...")
    clf = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        use_label_encoder=False,
        eval_metric="mlogloss",
    )
    clf.fit(X, y_clf)
    clf_path = output_dir / "modelo_classificacao_XGBoost_latest.joblib"
    joblib.dump(clf, clf_path)
    print(f"   ✅ Salvo: {clf_path}")

    # ── Regressão XGBoost ──
    print("\n📈 Treinando modelo de regressão (XGBoost)...")
    reg = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
    )
    reg.fit(X, y_reg)
    reg_path = output_dir / "modelo_regressao_XGBoost_latest.joblib"
    joblib.dump(reg, reg_path)
    print(f"   ✅ Salvo: {reg_path}")

    # ── Pipeline de escalonamento ──
    print("\n⚙️ Gerando pipeline de escalonamento...")
    scaler = StandardScaler()
    scaler.fit(X)
    pipe_path = output_dir / "pipeline_escalonamento.joblib"
    joblib.dump(scaler, pipe_path)
    print(f"   ✅ Salvo: {pipe_path}")

    print("\n" + "=" * 60)
    print("✅ Todos os modelos dummy foram gerados com sucesso!")
    print(f"   Diretório: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
