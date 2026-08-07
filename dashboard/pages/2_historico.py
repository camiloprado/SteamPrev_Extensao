"""
Página de Histórico — Previsor Steam
Análise de dados e evolução de preços (dados mockados).
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Histórico | Previsor Steam", page_icon="📈", layout="wide")

st.title("📈 Histórico & Análise")
st.caption("Visualização de dados de preços e previsões anteriores")

# ── Dados Mockados ──
np.random.seed(42)

# Gera histórico de previsões simulado
n_previsoes = 50
dates = [datetime.now() - timedelta(days=i) for i in range(n_previsoes, 0, -1)]
games = ["ELDEN RING", "Stardew Valley", "Cyberpunk 2077", "Valheim", "Terraria", "Red Dead Redemption 2"]

previsoes_data = []
for d in dates:
    game = np.random.choice(games)
    classe = np.random.choice(["cai", "mantem", "sobe"], p=[0.35, 0.40, 0.25])
    confianca = np.random.uniform(0.45, 0.95)
    dias_estimados = np.random.randint(5, 200)
    previsoes_data.append({
        "data": d.strftime("%Y-%m-%d %H:%M"),
        "jogo": game,
        "classe": classe,
        "confianca": confianca,
        "dias_estimados": dias_estimados,
    })

df_previsoes = pd.DataFrame(previsoes_data)

# ── Filtros ──
st.markdown("### 🔍 Filtros")
col_f1, col_f2 = st.columns(2)
with col_f1:
    selected_game = st.selectbox("Jogo", ["Todos"] + sorted(games))
with col_f2:
    selected_classe = st.selectbox("Classe", ["Todas", "cai", "mantem", "sobe"])

df_filtered = df_previsoes.copy()
if selected_game != "Todos":
    df_filtered = df_filtered[df_filtered["jogo"] == selected_game]
if selected_classe != "Todas":
    df_filtered = df_filtered[df_filtered["classe"] == selected_classe]

st.divider()

# ── Métricas Resumo ──
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric("Total Previsões", len(df_filtered))
with col_m2:
    st.metric("Confiança Média", f"{df_filtered['confianca'].mean():.1%}")
with col_m3:
    st.metric("Dias Médio", f"{df_filtered['dias_estimados'].mean():.0f}")
with col_m4:
    most_common = df_filtered["classe"].mode().iloc[0] if not df_filtered.empty else "N/A"
    st.metric("Classe Dominante", most_common)

st.divider()

# ── Gráficos ──
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("📊 Distribuição de Classes")
    class_counts = df_filtered["classe"].value_counts()
    colors = {"cai": "#2ed573", "mantem": "#ffa502", "sobe": "#ff4757"}

    fig_pie = go.Figure(data=[go.Pie(
        labels=class_counts.index,
        values=class_counts.values,
        marker_colors=[colors.get(c, "#5352ed") for c in class_counts.index],
        hole=0.4,
        textinfo="label+percent",
        textfont_size=14,
    )])
    fig_pie.update_layout(
        template="plotly_dark",
        height=400,
        showlegend=True,
        margin=dict(t=30, b=30),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_g2:
    st.subheader("📈 Confiança ao Longo do Tempo")
    fig_conf = px.scatter(
        df_filtered,
        x="data",
        y="confianca",
        color="classe",
        color_discrete_map=colors,
        hover_data=["jogo", "dias_estimados"],
        template="plotly_dark",
        height=400,
    )
    fig_conf.update_layout(
        yaxis_range=[0, 1],
        xaxis_title="Data",
        yaxis_title="Confiança",
        margin=dict(t=30, b=30),
    )
    st.plotly_chart(fig_conf, use_container_width=True)

# ── Evolução de Preço Simulada ──
st.divider()
st.subheader("💰 Evolução de Preço (Simulado)")

game_for_chart = st.selectbox("Selecione um jogo:", games, key="price_game")

# Gera dados de preço mockados
np.random.seed(hash(game_for_chart) % 2**32)
base_prices = {"ELDEN RING": 249.90, "Stardew Valley": 24.99, "Cyberpunk 2077": 199.90,
               "Valheim": 69.99, "Terraria": 39.99, "Red Dead Redemption 2": 299.90}
base = base_prices.get(game_for_chart, 99.99)

price_dates = [datetime.now() - timedelta(days=i*7) for i in range(104, 0, -1)]  # 2 anos
prices = []
for d in price_dates:
    doy = d.timetuple().tm_yday
    is_sale = any(abs(doy - s) < 15 for s in [75, 177, 327, 355])
    if is_sale and np.random.random() < 0.6:
        discount = np.random.choice([25, 33, 50, 60, 75])
        prices.append(round(base * (1 - discount / 100), 2))
    else:
        prices.append(base)

df_prices = pd.DataFrame({"data": price_dates, "preco": prices})

fig_price = go.Figure()
fig_price.add_trace(go.Scatter(
    x=df_prices["data"],
    y=df_prices["preco"],
    mode="lines+markers",
    line=dict(color="#5352ed", width=2),
    marker=dict(size=4),
    fill="tozeroy",
    fillcolor="rgba(83, 82, 237, 0.1)",
    name="Preço",
))
fig_price.update_layout(
    template="plotly_dark",
    height=400,
    xaxis_title="Data",
    yaxis_title="Preço (R$)",
    margin=dict(t=30, b=30),
)
st.plotly_chart(fig_price, use_container_width=True)

# ── Tabela de Previsões ──
st.divider()
st.subheader("📋 Registro de Previsões")
st.dataframe(
    df_filtered.style.background_gradient(subset=["confianca"], cmap="YlOrRd"),
    use_container_width=True,
    height=400,
)
