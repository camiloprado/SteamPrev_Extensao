"""
Página de Previsão Interativa — Previsor Steam
Formulário para buscar jogos e visualizar previsões.
"""

import streamlit as st
import httpx
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Previsão | Previsor Steam", page_icon="📊", layout="wide")

st.title("📊 Previsão de Preço")
st.caption("Busque um jogo por nome ou AppID e veja a previsão de Machine Learning")

api_url = st.session_state.get("api_url", "http://localhost:8000")

# ── Formulário de Busca ──
col_search, col_btn = st.columns([4, 1])

with col_search:
    query = st.text_input(
        "🎮 AppID do Jogo",
        placeholder="Ex: 1245620 (Elden Ring), 730 (CS2)...",
        label_visibility="collapsed",
    )

with col_btn:
    horizonte_opcoes = {
        "latest": "Padrão (Latest)",
        "30d_latest": "30 Dias",
        "60d_latest": "60 Dias",
        "90d_latest": "90 Dias"
    }
    
    horizonte_chave = st.selectbox(
        "Horizonte",
        options=list(horizonte_opcoes.keys()),
        format_func=lambda x: horizonte_opcoes[x],
        label_visibility="collapsed",
    )
    predict_btn = st.button("🔮 Prever", use_container_width=True, type="primary")

# ── Jogos Populares (atalhos) ──
st.markdown("**Jogos populares:**")
popular_cols = st.columns(6)
popular_games = [
    ("Counter-Strike 2", "730"),
    ("ELDEN RING", "1245620"),
    ("Stardew Valley", "413150"),
    ("Cyberpunk 2077", "1091500"),
    ("Valheim", "892970"),
    ("Terraria", "105600"),
]

for i, (name, appid) in enumerate(popular_games):
    with popular_cols[i]:
        if st.button(name, key=f"pop_{appid}", use_container_width=True):
            query = appid
            predict_btn = True

st.divider()

# ── Resultado da Previsão ──
if predict_btn and query:
    with st.spinner("🔄 Analisando..."):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{api_url}/predict/game",
                    json={"query": query, "horizonte": horizonte_chave},
                )

            if response.status_code == 404:
                st.error(f"❌ Jogo não encontrado ou AppID inválido: **{query}**")
                st.info("💡 Informe estritamente o AppID numérico do jogo.")

            elif response.status_code == 200:
                data = response.json()
                game = data.get("game", {})
                clf = data.get("classificacao")
                reg = data.get("regressao")

                # ── Info do Jogo ──
                st.markdown("---")
                col_img, col_info = st.columns([1, 3])

                with col_img:
                    header = game.get("header_image")
                    if header:
                        st.image(header, use_container_width=True)

                with col_info:
                    st.markdown(f"## 🎮 {game.get('name', 'Jogo')}")
                    ci1, ci2, ci3 = st.columns(3)
                    with ci1:
                        price = game.get("price", 0)
                        st.metric("💰 Preço", f"R$ {price:.2f}" if price > 0 else "Gratuito")
                    with ci2:
                        st.metric("⭐ Reviews", f"{game.get('review_score', 'N/A')}%")
                    with ci3:
                        st.metric("🆔 AppID", game.get("appid", "N/A"))

                st.markdown("---")

                is_on_sale = game.get("is_on_sale", False)
                if is_on_sale:
                    discount = game.get("discount_percent", 0)
                    sale_end = game.get("sale_end_date")
                    msg = f"Este jogo já se encontra em promoção com **{discount}% de desconto**!"
                    if sale_end:
                        msg += f" Término estimado: {sale_end}."
                    st.success(f"🎉 {msg}")
                    st.info("💡 A predição não é necessária para jogos que já estão com oferta ativa.")
                else:
                    # ── Resultados ──
                    col_clf, col_reg = st.columns(2)

                    # Classificação
                    with col_clf:
                        st.subheader("📊 Direção do Preço")
                        if clf:
                            # Classe principal
                            classe_emoji = clf.get("classe_emoji", clf.get("classe", "?"))
                            confianca = clf.get("confianca", 0)

                            st.markdown(f"### {classe_emoji}")
                            st.markdown(f"**Confiança:** {confianca:.1%}")

                            # Gráfico de probabilidades
                            probas = clf.get("probabilidades", {})
                            if probas:
                                colors = {"cai": "#2ed573", "mantem": "#ffa502", "sobe": "#ff4757"}

                                fig = go.Figure(data=[
                                    go.Bar(
                                        x=list(probas.keys()),
                                        y=list(probas.values()),
                                        marker_color=[colors.get(k, "#5352ed") for k in probas.keys()],
                                        text=[f"{v:.1%}" for v in probas.values()],
                                        textposition="outside",
                                    )
                                ])
                                fig.update_layout(
                                    title="Probabilidades por Classe",
                                    yaxis_title="Probabilidade",
                                    yaxis_range=[0, 1],
                                    template="plotly_dark",
                                    height=350,
                                    margin=dict(t=50, b=30),
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("Modelo de classificação não disponível")

                    # Regressão
                    with col_reg:
                        st.subheader("⏳ Próxima Promoção")
                        if reg:
                            dias = reg.get("dias_estimados", 0)
                            descricao = reg.get("descricao", "")

                            # Gauge chart
                            fig_gauge = go.Figure(go.Indicator(
                                mode="gauge+number+delta",
                                value=dias,
                                title={"text": "Dias estimados", "font": {"size": 16}},
                                number={"suffix": " dias", "font": {"size": 36}},
                                gauge={
                                    "axis": {"range": [0, 365], "tickwidth": 1},
                                    "bar": {"color": "#5352ed"},
                                    "bgcolor": "rgba(0,0,0,0)",
                                    "steps": [
                                        {"range": [0, 30], "color": "rgba(46, 213, 115, 0.3)"},
                                        {"range": [30, 90], "color": "rgba(255, 165, 2, 0.3)"},
                                        {"range": [90, 365], "color": "rgba(255, 71, 87, 0.3)"},
                                    ],
                                    "threshold": {
                                        "line": {"color": "white", "width": 2},
                                        "thickness": 0.8,
                                        "value": dias,
                                    },
                                },
                            ))
                            fig_gauge.update_layout(
                                template="plotly_dark",
                                height=350,
                                margin=dict(t=60, b=30),
                            )
                            st.plotly_chart(fig_gauge, use_container_width=True)
                            st.info(descricao)
                            
                            # Exibir Desconto Previsto
                            desconto = reg.get("desconto_previsto_pct", 0)
                            preco_est = reg.get("preco_estimado", 0.0)
                            if desconto > 0:
                                st.success(f"🏷️ Desconto Previsto: **{desconto}%** (Estimativa: R$ {preco_est:.2f})")
                            else:
                                st.warning("📉 Modelo preditor de desconto ausente nos arquivos base.")
                        else:
                            st.warning("Modelo de regressão não disponível")

                # ── Features utilizadas ──
                if not is_on_sale:
                    features = data.get("features_utilizadas")
                    if features:
                        with st.expander("🔬 Features utilizadas na predição"):
                            feat_cols = st.columns(3)
                            for i, (key, val) in enumerate(features.items()):
                                with feat_cols[i % 3]:
                                    if isinstance(val, float):
                                        st.metric(key, f"{val:.4f}")
                                    else:
                                        st.metric(key, str(val))
            else:
                st.error(f"Erro na API: {response.status_code}")

        except httpx.ConnectError:
            st.error("🔴 Não foi possível conectar à API")
            st.info(f"Verifique se a API está rodando em **{api_url}**")
        except Exception as e:
            st.error(f"Erro: {str(e)}")

elif predict_btn:
    st.warning("Digite o nome de um jogo ou AppID para buscar")
