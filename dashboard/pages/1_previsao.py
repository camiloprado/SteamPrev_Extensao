"""
Página de Previsão Interativa — Previsor Steam
Formulário para buscar jogos e visualizar previsões.
"""

import os
import streamlit as st
import httpx
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Previsão | Previsor Steam", page_icon="📊", layout="wide")

st.title("📊 Previsão de Preço")
st.caption("Busque um jogo por nome ou AppID e veja a previsão de Machine Learning")

var_strApiUrl = (
    st.session_state.get("api_url")
    or os.getenv("API_BASE_URL", "http://localhost:8000")
).rstrip("/")

@st.cache_data
def get_game_catalog():
    import json
    try:
        with open("resources/dados/steam_applist.json", "r", encoding="utf-8") as var_fileApplist:
            var_listData = json.load(var_fileApplist)
        return sorted([var_dictG for var_dictG in var_listData if var_dictG.get("name")], key=lambda x: x["name"])
    except Exception:
        return []

def buscar_jogos_no_catalogo(arg_strQuery: str, arg_listCatalogo: list, arg_intLimite: int = 30) -> dict:
    # Filtra em memória e limita o resultado — evita mandar o catálogo inteiro (280k+ jogos) pro navegador a cada rerender
    if not arg_strQuery or len(arg_strQuery) < 2:
        return {}
    var_strQueryLower = arg_strQuery.lower().strip()
    var_listMatches = [var_dictG for var_dictG in arg_listCatalogo if var_strQueryLower in var_dictG["name"].lower()]
    var_listMatches.sort(key=lambda var_dictG: not var_dictG["name"].lower().startswith(var_strQueryLower))
    return {f"{var_dictG['name']} ({var_dictG['appid']})": var_dictG['appid'] for var_dictG in var_listMatches[:arg_intLimite]}

var_listGameCatalog = get_game_catalog()
var_dictHorizonteOpcoes = {
    "latest": "Padrão (Latest)",
    "30d_latest": "30 Dias",
    "60d_latest": "60 Dias",
    "90d_latest": "90 Dias",
}

# Radio fora do form para trocar o método de busca sem precisar de Enter
var_strModoBusca = st.radio(
    "Método de Busca",
    ["Nome (Autocomplete)", "AppID Manual"],
    horizontal=True,
    label_visibility="collapsed",
)

var_dictResultadosBusca = {}
if "Nome" in var_strModoBusca:
    # Também fora do form: cada tecla digitada já filtra o catálogo antes de renderizar o form
    var_strBuscaTexto = st.text_input(
        "🎮 Digite o nome do jogo",
        placeholder="Digite ao menos 2 letras para buscar...",
        label_visibility="collapsed",
    )
    var_dictResultadosBusca = buscar_jogos_no_catalogo(var_strBuscaTexto, var_listGameCatalog)

# ── Formulário de Busca (Enter confirma) ──
with st.form("previsao_form", clear_on_submit=False):
    var_objColSearch, var_objColBtn = st.columns([4, 1])

    with var_objColSearch:
        if "Nome" in var_strModoBusca:
            var_strGameSelected = st.selectbox(
                "🎮 Escolha o Jogo",
                options=[""] + list(var_dictResultadosBusca.keys()),
                index=0,
                label_visibility="collapsed",
            )
            var_strQuery = str(var_dictResultadosBusca[var_strGameSelected]) if var_strGameSelected else ""
        else:
            var_strQuery = st.text_input(
                "🎮 AppID do Jogo",
                placeholder="Ex: 1245620 — pressione Enter para prever",
                label_visibility="collapsed",
            )

    with var_objColBtn:
        var_strHorizonteChave = st.selectbox(
            "Horizonte",
            options=list(var_dictHorizonteOpcoes.keys()),
            format_func=lambda x: var_dictHorizonteOpcoes[x],
            label_visibility="collapsed",
        )
        var_boolPredictBtn = st.form_submit_button("🔮 Prever", width="stretch", type="primary")

# ── Jogos Populares (atalhos, fora do form) ──
st.markdown("**Jogos populares:**")
var_listPopularCols = st.columns(6)
var_listPopularGames = [
    ("Counter-Strike 2", "730"),
    ("ELDEN RING", "1245620"),
    ("Stardew Valley", "413150"),
    ("Cyberpunk 2077", "1091500"),
    ("Valheim", "892970"),
    ("Terraria", "105600"),
]

for var_intI, (var_strName, var_strAppid) in enumerate(var_listPopularGames):
    with var_listPopularCols[var_intI]:
        if st.button(var_strName, key=f"pop_{var_strAppid}", width="stretch"):
            var_strQuery = var_strAppid
            var_boolPredictBtn = True

st.divider()

# ── Resultado da Previsão ──
if var_boolPredictBtn and var_strQuery:
    with st.spinner("🔄 Analisando..."):
        try:
            with httpx.Client(timeout=30.0) as var_objClient:
                var_objResponse = var_objClient.post(
                    f"{var_strApiUrl}/predict/game",
                    json={"query": var_strQuery, "horizonte": var_strHorizonteChave},
                )

            if var_objResponse.status_code == 404:
                st.error(f"❌ Jogo não encontrado ou AppID inválido: **{var_strQuery}**")
                st.info("💡 Informe estritamente o AppID numérico do jogo.")

            elif var_objResponse.status_code == 200:
                var_dictData = var_objResponse.json()
                var_dictGame = var_dictData.get("game", {})
                var_dictClf = var_dictData.get("classificacao")
                var_dictReg = var_dictData.get("regressao")

                # ── Exibir Avisos da API ──
                var_listWarnings = var_dictData.get("warnings")
                if var_listWarnings:
                    for var_strW in var_listWarnings:
                        st.warning(f"⚠️ {var_strW}")

                # ── Info do Jogo ──
                st.markdown("---")
                var_objColImg, var_objColInfo = st.columns([1, 3])

                with var_objColImg:
                    var_strHeader = var_dictGame.get("header_image")
                    if var_strHeader:
                        st.image(var_strHeader, width="stretch")

                with var_objColInfo:
                    st.markdown(f"## 🎮 {var_dictGame.get('name', 'Jogo')}")
                    var_strReleaseDate = var_dictGame.get("release_date")
                    if var_strReleaseDate:
                        st.caption(f"📅 Lançamento: {var_strReleaseDate}")
                    var_objCi1, var_objCi2, var_objCi3 = st.columns(3)
                    with var_objCi1:
                        var_floatPrice = var_dictGame.get("price", 0)
                        var_boolIsComingSoon = var_dictGame.get("is_coming_soon", False)
                        if var_boolIsComingSoon:
                            st.metric("💰 Preço", "Não Lançado")
                        else:
                            st.metric("💰 Preço", f"R$ {var_floatPrice:.2f}" if var_floatPrice > 0 else "Gratuito")
                    with var_objCi2:
                        st.metric("⭐ Reviews", f"{var_dictGame.get('review_score', 'N/A')}%")
                    with var_objCi3:
                        st.metric("🆔 AppID", var_dictGame.get("appid", "N/A"))

                st.markdown("---")

                # Comparação com o desconto histórico — só aparece quando há algo a
                # reportar (backend omite quando o jogo nunca teve desconto e não
                # está em promoção agora).
                var_dictHistoricoDesconto = var_dictData.get("historico_desconto")
                if var_dictHistoricoDesconto:
                    var_intJanela = var_dictHistoricoDesconto["janela_anos"]
                    if var_dictHistoricoDesconto["eh_maior_historico"]:
                        st.success(f"🏆 Este é o maior desconto já registrado nos últimos {var_intJanela} anos!")
                    else:
                        st.info(
                            f"📊 O maior desconto histórico foi **{var_dictHistoricoDesconto['maior_desconto_pct']}%** "
                            f"em {var_dictHistoricoDesconto['data_maior_desconto']} (últimos {var_intJanela} anos)."
                        )

                var_boolIsOnSale = var_dictGame.get("is_on_sale", False)
                if var_boolIsOnSale:
                    var_intDiscount = var_dictGame.get("discount_percent", 0)
                    var_strSaleEnd = var_dictGame.get("sale_end_date")
                    var_strMsg = f"Este jogo já se encontra em promoção com **{var_intDiscount}% de desconto**!"
                    if var_strSaleEnd:
                        var_strMsg += f" Término estimado: {var_strSaleEnd}."
                    st.success(f"🎉 {var_strMsg}")
                    st.info("💡 A predição não é necessária para jogos que já estão com oferta ativa.")
                else:
                    # ── Resultados ──
                    var_objColClf, var_objColReg = st.columns(2)

                    # Classificação
                    with var_objColClf:
                        st.subheader("📊 Direção do Preço")
                        if var_dictClf:
                            # Classe principal
                            var_strClasseEmoji = var_dictClf.get("classe_emoji", var_dictClf.get("classe", "?"))
                            var_floatConfianca = var_dictClf.get("confianca", 0)

                            st.markdown(f"### {var_strClasseEmoji}")
                            st.markdown(f"**Confiança:** {var_floatConfianca:.1%}")

                            # Gráfico de probabilidades
                            var_dictProbas = var_dictClf.get("probabilidades", {})
                            if var_dictProbas:
                                var_dictColors = {"cai": "#2ed573", "mantem": "#ffa502", "sobe": "#ff4757"}

                                var_objFig = go.Figure(data=[
                                    go.Bar(
                                        x=list(var_dictProbas.keys()),
                                        y=list(var_dictProbas.values()),
                                        marker_color=[var_dictColors.get(var_strK, "#5352ed") for var_strK in var_dictProbas.keys()],
                                        text=[f"{var_floatV:.1%}" for var_floatV in var_dictProbas.values()],
                                        textposition="outside",
                                    )
                                ])
                                var_objFig.update_layout(
                                    title="Probabilidades por Classe",
                                    yaxis_title="Probabilidade",
                                    yaxis_range=[0, 1],
                                    template="plotly_dark",
                                    height=350,
                                    margin=dict(t=50, b=30),
                                )
                                st.plotly_chart(var_objFig, width="stretch")
                        else:
                            st.warning("Modelo de classificação não disponível")

                    # Regressão
                    with var_objColReg:
                        st.subheader("⏳ Próxima Promoção")
                        if var_dictReg:
                            var_intDias = var_dictReg.get("dias_estimados", 0)
                            var_strDescricao = var_dictReg.get("descricao", "")

                            var_strHorizonteNorm = var_strHorizonteChave.replace("_latest", "") if var_strHorizonteChave != "latest" else "latest"
                            var_intCapGauge = 60 if var_strHorizonteNorm == "60d" else (90 if var_strHorizonteNorm == "90d" else 30)
                            var_listPassosGauge = [
                                {"range": [0, min(30, var_intCapGauge)], "color": "rgba(46, 213, 115, 0.3)"},
                            ]
                            if var_intCapGauge > 30:
                                var_listPassosGauge.append(
                                    {"range": [30, var_intCapGauge], "color": "rgba(255, 165, 2, 0.3)"}
                                )

                            # Gauge chart
                            var_objFigGauge = go.Figure(go.Indicator(
                                mode="gauge+number+delta",
                                value=min(var_intDias, var_intCapGauge),
                                title={"text": "Dias estimados", "font": {"size": 16}},
                                number={"suffix": " dias", "font": {"size": 36}},
                                gauge={
                                    "axis": {"range": [0, var_intCapGauge], "tickwidth": 1},
                                    "bar": {"color": "#5352ed"},
                                    "bgcolor": "rgba(0,0,0,0)",
                                    "steps": var_listPassosGauge,
                                    "threshold": {
                                        "line": {"color": "white", "width": 2},
                                        "thickness": 0.8,
                                        "value": min(var_intDias, var_intCapGauge),
                                    },
                                },
                            ))
                            var_objFigGauge.update_layout(
                                template="plotly_dark",
                                height=350,
                                margin=dict(t=60, b=30),
                            )
                            st.plotly_chart(var_objFigGauge, width="stretch")
                            st.info(var_strDescricao)

                            # Exibir Desconto Previsto
                            var_intDesconto = var_dictReg.get("desconto_previsto_pct", 0)
                            var_floatMargem = var_dictReg.get("desconto_margem_erro", 0.0)
                            var_floatPrecoEst = var_dictReg.get("preco_estimado", 0.0)
                            if var_intDesconto > 0:
                                st.success(f"🏷️ Desconto Previsto: **{var_intDesconto}% (± {var_floatMargem}%)** (Estimativa: R$ {var_floatPrecoEst:.2f})")
                            else:
                                st.warning("📉 Modelo preditor de desconto ausente nos arquivos base.")
                        else:
                            st.warning("Modelo de regressão não disponível")

                # ── Features utilizadas ──
                if not var_boolIsOnSale:
                    var_dictFeatures = var_dictData.get("features_utilizadas")
                    if var_dictFeatures:
                        with st.expander("🔬 Features utilizadas na predição"):
                            var_listFeatCols = st.columns(3)
                            for var_intI, (var_strKey, var_anyVal) in enumerate(var_dictFeatures.items()):
                                with var_listFeatCols[var_intI % 3]:
                                    if isinstance(var_anyVal, float):
                                        st.metric(var_strKey, f"{var_anyVal:.4f}")
                                    else:
                                        st.metric(var_strKey, str(var_anyVal))
            else:
                st.error(f"Erro na API: {var_objResponse.status_code}")

        except httpx.ConnectError:
            st.error("🔴 Não foi possível conectar à API")
            st.info(f"Verifique se a API está rodando em **{var_strApiUrl}**")
        except Exception as e:
            st.error(f"Erro: {str(e)}")

elif var_boolPredictBtn:
    st.warning("Digite o nome de um jogo ou AppID para buscar")
