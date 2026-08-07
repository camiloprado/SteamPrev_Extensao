"""
API de Inferência — Previsor Steam
FastAPI app com carregamento de modelos no startup e CORS configurado.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys

from api.config import settings
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
    model_manager = ModelManager(settings.MODELS_PATH)
    model_manager.load_models()
    app.state.model_manager = model_manager

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

# ── CORS (permitir extensão Chrome, Streamlit, e desenvolvimento local) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )
