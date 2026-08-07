"""Endpoint de health check."""

from fastapi import APIRouter, Request
from api.schemas import HealthResponse
from datetime import datetime

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """
    Verifica se a API está online e se os modelos foram carregados.
    """
    model_manager = request.app.state.model_manager
    models_status = model_manager.get_status()

    status = "healthy" if models_status["classificacao"] or models_status["regressao"] else "degraded"
    if not models_status["loaded"]:
        status = "unhealthy"

    return HealthResponse(
        status=status,
        models=models_status,
        timestamp=datetime.now().isoformat(),
    )
