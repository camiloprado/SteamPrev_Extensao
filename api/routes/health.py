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

    var_boolTemClassificacao = bool(var_dictModelosStatus.get("classificacao"))
    var_boolTemRegressao = bool(
        var_dictModelosStatus.get("regressao_dias") or var_dictModelosStatus.get("regressao")
    )
    var_strStatus = "healthy" if var_boolTemClassificacao or var_boolTemRegressao else "degraded"
    if not var_dictModelosStatus["loaded"]:
        var_strStatus = "unhealthy"

    # Modelo carregado na memória, mas com features diferentes das geradas pela
    # inferência atual (ex.: Fábrica retreinou com uma feature nova e o deploy
    # da Extensão ficou desatualizado) — prediz "com sucesso" só que sempre None,
    # sem isso o /health mentiria "healthy" com a predição de fato quebrada.
    if var_dictModelosStatus.get("features_incompativeis"):
        var_strStatus = "degraded"

    return HealthResponse(
        status=var_strStatus,
        models=var_dictModelosStatus,
        timestamp=datetime.now().isoformat(),
    )
