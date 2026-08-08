"""Cliente HTTP assíncrono para a API FastAPI de inferência."""

import httpx
import logging
import os

logger = logging.getLogger("bot.api_client")

CON_STR_API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class APIClient:
    """Cliente para comunicação com a API de inferência."""

    def __init__(self, arg_strBaseUrl: str = None):
        self._var_strBaseUrl = arg_strBaseUrl or CON_STR_API_BASE_URL
        self._var_objClient = httpx.AsyncClient(base_url=self._var_strBaseUrl, timeout=30.0)

    async def close(self):
        """Fecha a sessão HTTP."""
        await self._var_objClient.aclose()

    async def health(self) -> dict:
        """
        Verifica status da API.

        Retorna:
        - dict: Status da API.
        """
        try:
            var_objResponse = await self._var_objClient.get("/health")
            var_objResponse.raise_for_status()
            return var_objResponse.json()
        except Exception as e:
            logger.error(f"Erro ao verificar health: {e}")
            return {"status": "offline", "error": str(e)}

    async def predict_game(self, arg_strQuery: str, arg_strHorizonte: str = "latest") -> dict | None:
        """
        Faz predição completa (classificação + regressão) para um jogo.

        Parâmetros:
        - arg_strQuery (str): AppID do jogo.
        - arg_strHorizonte (str): Horizonte da predição.

        Retorna:
        - dict | None: Resposta da API ou None se falhar.
        """
        try:
            var_objResponse = await self._var_objClient.post(
                "/predict/game",
                json={"query": arg_strQuery, "horizonte": arg_strHorizonte},
            )
            var_objResponse.raise_for_status()
            return var_objResponse.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Jogo não encontrado: {arg_strQuery}")
                return None
            logger.error(f"Erro HTTP na predição: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro na predição: {e}")
            return None

