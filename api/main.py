"""
API de Inferência — Previsor Steam
FastAPI app com carregamento de modelos no startup e CORS configurado.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys

from api.config import api_settings
from api.models_loader import ModelManager
from api.routes import health, predict

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("api.main")


# ── Lifespan ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carrega modelos na inicialização e libera recursos no shutdown."""
    logger.info("═" * 60)
    logger.info("🚀 Iniciando API de Inferência — Previsor Steam")
    logger.info("═" * 60)

    # Carrega modelos
    var_objModelManager = ModelManager(api_settings.MODELS_PATH)
    var_objModelManager.load_models()
    app.state.model_manager = var_objModelManager

    logger.info("API pronta para receber requisições.")
    yield

    # Cleanup
    logger.info("Encerrando API...")


# ── App ──
app = FastAPI(
    title="Previsor Steam — API de Inferência",
    description=(
        "API para previsão de direção de preço e tempo até promoção de jogos na Steam. "
        "Consome modelos .joblib treinados pelo projeto base (Fábrica/ETL)."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──
# Em produção, a variável de ambiente CORS_ORIGINS pode ser definida.
# Por padrão, restringimos o acesso para localhost e para extensões de navegadores.
import os
var_strCorsOrigins = os.getenv("CORS_ORIGINS", "")
if var_strCorsOrigins:
    var_listOrigins = [var_strOrigin.strip() for var_strOrigin in var_strCorsOrigins.split(",")]
    var_strOriginRegex = None
else:
    var_listOrigins = []
    # Expressão regular para aceitar conexões locais e extensões (Chrome, Edge, Brave, Opera, Firefox)
    var_strOriginRegex = r"https?://localhost:\d+|https?://127\.0\.0\.1:\d+|chrome-extension://.*|moz-extension://.*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=var_listOrigins,
    allow_origin_regex=var_strOriginRegex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rotas ──
app.include_router(health.router)
app.include_router(predict.router)


@app.get("/")
async def root():
    """Rota raiz com informações da API."""
    return {
        "name": "Previsor Steam — API de Inferência",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=api_settings.API_HOST,
        port=api_settings.API_PORT,
        reload=True,
    )
