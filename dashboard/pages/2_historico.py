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
        with open("resources/dados/steam_applist.json", "r", encoding="utf-8") as var_fileApplist:
            var_listData = json.load(var_fileApplist)
        var_listDataSorted = sorted([var_dictG for var_dictG in var_listData if var_dictG.get("name")], key=lambda x: x["name"])
        return {var_dictG['name']: var_dictG['appid'] for var_dictG in var_listDataSorted}
    except Exception:
        return {"ELDEN RING": 1245620, "Stardew Valley": 413150, "Cyberpunk 2077": 1091500, "Valheim": 892970, "Terraria": 105600, "Red Dead Redemption 2": 1174180}

var_dictGameCatalog = get_game_catalog()
var_listGameNames = list(var_dictGameCatalog.keys())



st.title("📈 Histórico & Análise")
st.caption("Visualização de dados de preços e previsões anteriores")

# ── Dados Mockados ──
np.random.seed(42)

# Gera histórico de previsões simulado
var_intNPrevisoes = 50
var_listDates = [datetime.now() - timedelta(days=var_intI) for var_intI in range(var_intNPrevisoes, 0, -1)]
var_listGamesPopulares = ["ELDEN RING", "Stardew Valley", "Cyberpunk 2077", "Valheim", "Terraria", "Red Dead Redemption 2"]

var_listPrevisoesData = []
for var_dtD in var_listDates:
    var_strGame = np.random.choice(var_listGamesPopulares)
    var_strClasse = np.random.choice(["cai", "mantem", "sobe"], p=[0.35, 0.40, 0.25])
    var_floatConfianca = np.random.uniform(0.45, 0.95)
    var_intDiasEstimados = np.random.randint(5, 200)
    var_listPrevisoesData.append({
        "data": var_dtD.strftime("%Y-%m-%d %H:%M"),
        "jogo": var_strGame,
        "classe": var_strClasse,
        "confianca": var_floatConfianca,
        "dias_estimados": var_intDiasEstimados,
    })

# ── Filtros ──
st.markdown("### 🔍 Filtros")
var_objColF1, var_objColF2 = st.columns(2)
with var_objColF1:
    var_strSelectedGame = st.selectbox("Jogo", ["Todos"] + var_listGameNames)
with var_objColF2:
    var_strSelectedClasse = st.selectbox("Classe", ["Todas", "cai", "mantem", "sobe"])

# Garante que o jogo selecionado tenha dados mockados para o gráfico não ficar vazio
if var_strSelectedGame != "Todos" and var_strSelectedGame not in var_listGamesPopulares:
    np.random.seed(hash(var_strSelectedGame) % 2**32)
    for var_intI in range(1, 6):
        var_dtD = datetime.now() - timedelta(days=np.random.randint(1, 100))
        var_listPrevisoesData.append({
            "data": var_dtD.strftime("%Y-%m-%d %H:%M"),
            "jogo": var_strSelectedGame,
            "classe": np.random.choice(["cai", "mantem", "sobe"], p=[0.35, 0.40, 0.25]),
            "confianca": np.random.uniform(0.45, 0.95),
            "dias_estimados": np.random.randint(5, 200),
        })

var_dfPrevisoes = pd.DataFrame(var_listPrevisoesData)
# Ordenar por data mais recente
var_dfPrevisoes = var_dfPrevisoes.sort_values(by="data", ascending=False)

var_dfFiltered = var_dfPrevisoes.copy()
if var_strSelectedGame != "Todos":
    var_dfFiltered = var_dfFiltered[var_dfFiltered["jogo"] == var_strSelectedGame]
if var_strSelectedClasse != "Todas":
    var_dfFiltered = var_dfFiltered[var_dfFiltered["classe"] == var_strSelectedClasse]

st.divider()

# ── Métricas Resumo ──
var_objColM1, var_objColM2, var_objColM3, var_objColM4 = st.columns(4)
with var_objColM1:
    st.metric("Total Previsões", len(var_dfFiltered))
with var_objColM2:
    st.metric("Confiança Média", f"{var_dfFiltered['confianca'].mean():.1%}")
with var_objColM3:
    st.metric("Dias Médio", f"{var_dfFiltered['dias_estimados'].mean():.0f}")
with var_objColM4:
    var_strMostCommon = var_dfFiltered["classe"].mode().iloc[0] if not var_dfFiltered.empty else "N/A"
    st.metric("Classe Dominante", var_strMostCommon)

st.divider()

# ── Gráficos ──
var_objColG1, var_objColG2 = st.columns(2)

with var_objColG1:
    st.subheader("📊 Distribuição de Classes")
    var_serClassCounts = var_dfFiltered["classe"].value_counts()
    var_dictColors = {"cai": "#2ed573", "mantem": "#ffa502", "sobe": "#ff4757"}

    var_objFigPie = go.Figure(data=[go.Pie(
        labels=var_serClassCounts.index,
        values=var_serClassCounts.values,
        marker_colors=[var_dictColors.get(var_strC, "#5352ed") for var_strC in var_serClassCounts.index],
        hole=0.4,
        textinfo="label+percent",
        textfont_size=14,
    )])
    var_objFigPie.update_layout(
        template="plotly_dark",
        height=400,
        showlegend=True,
        margin=dict(t=30, b=30),
    )
    st.plotly_chart(var_objFigPie, width="stretch")

with var_objColG2:
    st.subheader("📈 Confiança ao Longo do Tempo")
    var_objFigConf = px.scatter(
        var_dfFiltered,
        x="data",
        y="confianca",
        color="classe",
        color_discrete_map=var_dictColors,
        hover_data=["jogo", "dias_estimados"],
        template="plotly_dark",
        height=400,
    )
    var_objFigConf.update_layout(
        yaxis_range=[0, 1],
        xaxis_title="Data",
        yaxis_title="Confiança",
        margin=dict(t=30, b=30),
    )
    st.plotly_chart(var_objFigConf, width="stretch")

# ── Evolução de Preço via ITAD (real, com fallback simulado quando indisponível) ──
st.divider()
st.subheader("💰 Evolução de Preço")

var_objColGame, var_objColTime = st.columns([3, 1])

with var_objColGame:
    var_strGameForChart = st.selectbox(
        "Selecione um jogo:",
        var_listGameNames,
        index=var_listGameNames.index(var_strSelectedGame) if var_strSelectedGame != "Todos" and var_strSelectedGame in var_listGameNames else 0,
        key="price_game"
    )

with var_objColTime:
    var_strTimeFilter = st.selectbox(
        "Período:",
        ["5+ Anos", "3 Anos", "2 Anos", "1 Ano", "Mês Passado", "Últimos 15 Dias"]
    )

# Busca histórico real via ITAD API
with st.spinner(f"Buscando histórico real para {var_strGameForChart}..."):
    var_intAppid = var_dictGameCatalog[var_strGameForChart]
    var_listItadHistory = asyncio.run(ITADClient.get_price_history(var_intAppid))

if not var_listItadHistory:
    st.warning("Nenhum histórico encontrado na ITAD para este jogo.")
    var_dfPrices = pd.DataFrame(columns=["data", "preco"])
else:
    # ITADClient sinaliza por item se os dados vieram da API real ou de um
    # fallback simulado (sem ITAD_API_KEY, rate limit, ou erro de rede) — avisa
    # o usuário para não confundir dados fabricados com o histórico real.
    if any(var_dictItem.get("fonte") == "mock" for var_dictItem in var_listItadHistory):
        st.info(
            "⚠️ Não foi possível obter o histórico real da ITAD agora (chave da API "
            "ausente, limite de requisições ou erro de rede). Os dados abaixo são "
            "**simulados** para fins de demonstração.",
            icon="⚠️",
        )
    else:
        st.caption("✅ Histórico real obtido via ITAD API.")

    # Conversão dos dados do ITAD para o formato do DataFrame
    var_listPriceDates = [datetime.fromtimestamp(var_dictItem["timestamp"]) for var_dictItem in var_listItadHistory]
    var_listPrices = [var_dictItem["preco"] for var_dictItem in var_listItadHistory]
    var_dfPrices = pd.DataFrame({"data": var_listPriceDates, "preco": var_listPrices})

    if not var_dfPrices.empty:
        var_dtNow = datetime.now()
        if var_strTimeFilter == "3 Anos":
            var_dtCutoff = var_dtNow - timedelta(days=365*3)
        elif var_strTimeFilter == "2 Anos":
            var_dtCutoff = var_dtNow - timedelta(days=365*2)
        elif var_strTimeFilter == "1 Ano":
            var_dtCutoff = var_dtNow - timedelta(days=365)
        elif var_strTimeFilter == "Mês Passado":
            var_dtCutoff = var_dtNow - timedelta(days=30)
        elif var_strTimeFilter == "Últimos 15 Dias":
            var_dtCutoff = var_dtNow - timedelta(days=15)
        else:
            var_dtCutoff = None

        if var_dtCutoff:
            var_dfPrices = var_dfPrices[var_dfPrices["data"] >= var_dtCutoff]

var_objFigPrice = go.Figure()
var_objFigPrice.add_trace(go.Scatter(
    x=var_dfPrices["data"],
    y=var_dfPrices["preco"],
    mode="lines+markers",
    line=dict(color="#5352ed", width=2, shape="hv"),
    marker=dict(size=4),
    fill="tozeroy",
    fillcolor="rgba(83, 82, 237, 0.1)",
    name="Preço",
))
var_objFigPrice.update_layout(
    template="plotly_dark",
    height=400,
    xaxis_title="Data",
    yaxis_title="Preço (R$)",
    margin=dict(t=30, b=30),
)
st.plotly_chart(var_objFigPrice, width="stretch")

# ── Tabela de Previsões ──
st.divider()
st.subheader("📋 Registro de Previsões")
st.dataframe(
    var_dfFiltered.style.background_gradient(subset=["confianca"], cmap="YlOrRd"),
    width="stretch",
    height=400,
)
