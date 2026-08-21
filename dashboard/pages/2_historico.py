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
import asyncio
import sys
import os

# Adiciona o diretório raiz ao path para importar o core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from core.itad_client import ITADClient

st.set_page_config(page_title="Histórico | Previsor Steam", page_icon="📈", layout="wide")

@st.cache_data
def get_game_catalog():
    import json
    try:
        with open("resources/dados/steam_applist.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        data_sorted = sorted([g for g in data if g.get("name")], key=lambda x: x["name"])
        return {g['name']: g['appid'] for g in data_sorted}
    except Exception:
        return {"ELDEN RING": 1245620, "Stardew Valley": 413150, "Cyberpunk 2077": 1091500, "Valheim": 892970, "Terraria": 105600, "Red Dead Redemption 2": 1174180}

game_catalog = get_game_catalog()
game_names = list(game_catalog.keys())



st.title("📈 Histórico & Análise")
st.caption("Visualização de dados de preços e previsões anteriores")

# ── Dados Mockados ──
np.random.seed(42)

# Gera histórico de previsões simulado
n_previsoes = 50
dates = [datetime.now() - timedelta(days=i) for i in range(n_previsoes, 0, -1)]
games_populares = ["ELDEN RING", "Stardew Valley", "Cyberpunk 2077", "Valheim", "Terraria", "Red Dead Redemption 2"]

previsoes_data = []
for d in dates:
    game = np.random.choice(games_populares)
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

# ── Filtros ──
st.markdown("### 🔍 Filtros")
col_f1, col_f2 = st.columns(2)
with col_f1:
    selected_game = st.selectbox("Jogo", ["Todos"] + game_names)
with col_f2:
    selected_classe = st.selectbox("Classe", ["Todas", "cai", "mantem", "sobe"])

# Garante que o jogo selecionado tenha dados mockados para o gráfico não ficar vazio
if selected_game != "Todos" and selected_game not in games_populares:
    np.random.seed(hash(selected_game) % 2**32)
    for i in range(1, 6):
        d = datetime.now() - timedelta(days=np.random.randint(1, 100))
        previsoes_data.append({
            "data": d.strftime("%Y-%m-%d %H:%M"),
            "jogo": selected_game,
            "classe": np.random.choice(["cai", "mantem", "sobe"], p=[0.35, 0.40, 0.25]),
            "confianca": np.random.uniform(0.45, 0.95),
            "dias_estimados": np.random.randint(5, 200),
        })

df_previsoes = pd.DataFrame(previsoes_data)
# Ordenar por data mais recente
df_previsoes = df_previsoes.sort_values(by="data", ascending=False)

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
    st.plotly_chart(fig_pie, width="stretch")

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
    st.plotly_chart(fig_conf, width="stretch")

# ── Evolução de Preço via ITAD (real, com fallback simulado quando indisponível) ──
st.divider()
st.subheader("💰 Evolução de Preço")

col_game, col_time = st.columns([3, 1])

with col_game:
    game_for_chart = st.selectbox(
        "Selecione um jogo:", 
        game_names, 
        index=game_names.index(selected_game) if selected_game != "Todos" and selected_game in game_names else 0, 
        key="price_game"
    )

with col_time:
    time_filter = st.selectbox(
        "Período:", 
        ["5+ Anos", "3 Anos", "2 Anos", "1 Ano", "Mês Passado", "Últimos 15 Dias"]
    )

# Busca histórico real via ITAD API
with st.spinner(f"Buscando histórico real para {game_for_chart}..."):
    appid = game_catalog[game_for_chart]
    itad_history = asyncio.run(ITADClient.get_price_history(appid))

if not itad_history:
    st.warning("Nenhum histórico encontrado na ITAD para este jogo.")
    df_prices = pd.DataFrame(columns=["data", "preco"])
else:
    # ITADClient sinaliza por item se os dados vieram da API real ou de um
    # fallback simulado (sem ITAD_API_KEY, rate limit, ou erro de rede) — avisa
    # o usuário para não confundir dados fabricados com o histórico real.
    if any(item.get("fonte") == "mock" for item in itad_history):
        st.info(
            "⚠️ Não foi possível obter o histórico real da ITAD agora (chave da API "
            "ausente, limite de requisições ou erro de rede). Os dados abaixo são "
            "**simulados** para fins de demonstração.",
            icon="⚠️",
        )
    else:
        st.caption("✅ Histórico real obtido via ITAD API.")

    # Conversão dos dados do ITAD para o formato do DataFrame
    price_dates = [datetime.fromtimestamp(item["timestamp"]) for item in itad_history]
    prices = [item["preco"] for item in itad_history]
    df_prices = pd.DataFrame({"data": price_dates, "preco": prices})
    
    if not df_prices.empty:
        now = datetime.now()
        if time_filter == "3 Anos":
            cutoff = now - timedelta(days=365*3)
        elif time_filter == "2 Anos":
            cutoff = now - timedelta(days=365*2)
        elif time_filter == "1 Ano":
            cutoff = now - timedelta(days=365)
        elif time_filter == "Mês Passado":
            cutoff = now - timedelta(days=30)
        elif time_filter == "Últimos 15 Dias":
            cutoff = now - timedelta(days=15)
        else:
            cutoff = None
            
        if cutoff:
            df_prices = df_prices[df_prices["data"] >= cutoff]

fig_price = go.Figure()
fig_price.add_trace(go.Scatter(
    x=df_prices["data"],
    y=df_prices["preco"],
    mode="lines+markers",
    line=dict(color="#5352ed", width=2, shape="hv"),
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
st.plotly_chart(fig_price, width="stretch")

# ── Tabela de Previsões ──
st.divider()
st.subheader("📋 Registro de Previsões")
st.dataframe(
    df_filtered.style.background_gradient(subset=["confianca"], cmap="YlOrRd"),
    width="stretch",
    height=400,
)
