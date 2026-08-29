"""
Dashboard Streamlit — Previsor Steam
Página principal com visão geral do sistema.
"""

import os
import streamlit as st

CON_STR_DEFAULT_API_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

# ── Configuração da Página ──
st.set_page_config(
    page_title="Previsor Steam",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS Customizado ──
st.markdown("""
<style>
    /* Tema escuro personalizado */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        transition: transform 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
    }
    .metric-card h2 {
        font-size: 2.5rem;
        margin: 0;
        background: linear-gradient(90deg, #e94560, #533483);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-card p {
        color: #a0a0b0;
        margin: 0.5rem 0 0 0;
        font-size: 0.9rem;
    }

    /* Header */
    .hero-section {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        border-radius: 16px;
        padding: 3rem 2rem;
        text-align: center;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .hero-section h1 {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    .hero-section p {
        color: #a0a0b0;
        font-size: 1.1rem;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29 0%, #1a1a2e 100%);
    }

    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .status-online {
        background: rgba(46, 213, 115, 0.15);
        color: #2ed573;
        border: 1px solid rgba(46, 213, 115, 0.3);
    }
    .status-offline {
        background: rgba(255, 71, 87, 0.15);
        color: #ff4757;
        border: 1px solid rgba(255, 71, 87, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.image("https://store.steampowered.com/favicon.ico", width=40)
    st.title("🎮 Previsor Steam")
    st.caption("Previsão de preços via Machine Learning")

    st.divider()

    st.markdown("### ⚙️ Configuração da API")
    var_strApiUrl = st.text_input(
        "URL da API",
        value=st.session_state.get("api_url", CON_STR_DEFAULT_API_URL),
        help="Endereço da API FastAPI de inferência (API_BASE_URL no Render)",
    )

    # Salva no session state para uso nas pages
    st.session_state["api_url"] = var_strApiUrl

    st.divider()
    st.markdown(
        "**Navegação:**\n"
        "- 📊 **Previsão** — Preveja preços\n"
        "- 📈 **Histórico** — Análise de dados\n"
    )

# ── Página Principal ──
st.markdown("""
<div class="hero-section">
    <h1>🎮 Previsor Steam</h1>
    <p>Previsão inteligente de preços de jogos usando Machine Learning</p>
    <p style="color: #6c6c8a; font-size: 0.9rem; margin-top: 1rem;">
        Classificação (sobe/cai/mantém) • Regressão (dias até promoção) • Modelos XGBoost
    </p>
</div>
""", unsafe_allow_html=True)

# ── Métricas Resumo ──
var_objCol1, var_objCol2, var_objCol3, var_objCol4 = st.columns(4)

with var_objCol1:
    st.markdown("""
    <div class="metric-card">
        <h2>🧠</h2>
        <p>XGBoost + LightGBM<br/>Modelos treinados</p>
    </div>
    """, unsafe_allow_html=True)

with var_objCol2:
    st.markdown("""
    <div class="metric-card">
        <h2>18</h2>
        <p>Features<br/>Engenharia de dados</p>
    </div>
    """, unsafe_allow_html=True)

with var_objCol3:
    st.markdown("""
    <div class="metric-card">
        <h2>3</h2>
        <p>Classes<br/>Cai / Mantém / Sobe</p>
    </div>
    """, unsafe_allow_html=True)

with var_objCol4:
    st.markdown("""
    <div class="metric-card">
        <h2>📊</h2>
        <p>Regressão<br/>Dias até promoção</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Status da API ──
st.subheader("📡 Status do Sistema")

import httpx

try:
    with httpx.Client(timeout=5.0) as var_objClient:
        var_objResponse = var_objClient.get(f"{var_strApiUrl}/health")
        var_dictHealth = var_objResponse.json()

    var_strStatus = var_dictHealth.get("status", "desconhecido")
    var_dictModels = var_dictHealth.get("models", {})

    if var_strStatus == "healthy":
        st.success("🟢 API Online — Todos os modelos carregados")
    elif var_strStatus == "degraded":
        st.warning("🟡 API Degradada — Alguns modelos não carregados")
    else:
        st.error("🔴 API com problemas")

    var_objColS1, var_objColS2, var_objColS3 = st.columns(3)
    with var_objColS1:
        st.metric("Classificação", "✅ Ativo" if var_dictModels.get("classificacao") else "❌ Inativo")
    with var_objColS2:
        st.metric("Regressão", "✅ Ativo" if var_dictModels.get("regressao_dias") else "❌ Inativo")
    with var_objColS3:
        st.metric("Pipeline", "✅ Ativo" if var_dictModels.get("pipeline_escalonamento") else "❌ Inativo")

except Exception:
    st.error("🔴 API Offline — Verifique se a API está rodando em " + var_strApiUrl)
    st.info("💡 Execute: `uvicorn api.main:app --reload` para iniciar a API")

# ── Como Usar ──
st.divider()
st.subheader("🚀 Como Usar")

var_objColU1, var_objColU2, var_objColU3 = st.columns(3)

with var_objColU1:
    st.markdown("### 📊 Dashboard")
    st.markdown(
        "Use a página **Previsão** na sidebar para:\n"
        "- Buscar jogos por nome ou AppID\n"
        "- Ver previsão de direção de preço\n"
        "- Ver estimativa de dias até promoção"
    )

with var_objColU2:
    st.markdown("### 🤖 Bot Discord")
    st.markdown(
        "Use os slash commands:\n"
        "- `/prever Elden Ring`\n"
        "- `/buscar counter-strike`\n"
        "- `/status`"
    )

with var_objColU3:
    st.markdown("### 🌐 Extensão Chrome")
    st.markdown(
        "Instale a extensão para:\n"
        "- Verificar previsões diretamente\n"
        "- Buscar jogos pelo popup\n"
        "- Ver resultados inline"
    )
