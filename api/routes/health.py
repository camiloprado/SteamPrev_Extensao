"""Endpoint de health check."""

from fastapi import APIRouter, Request
from api.schemas import HealthResponse
from datetime import datetime

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """
    Verifica se a API está online e se os modelos foram carregados.

    Retorna:
    - HealthResponse: Status da API e dos modelos.
    """
    var_objModelManager = request.app.state.model_manager
    var_dictModelosStatus = var_objModelManager.get_status()

    var_strStatus = "healthy" if var_dictModelosStatus["classificacao"] or var_dictModelosStatus["regressao_dias"] else "degraded"
    if not var_dictModelosStatus["loaded"]:
        var_strStatus = "unhealthy"

    return HealthResponse(
        status=var_strStatus,
        models=var_dictModelosStatus,
        timestamp=datetime.now().isoformat(),
    )
