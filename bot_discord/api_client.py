"""Cliente HTTP assíncrono para a API FastAPI de inferência."""

import httpx
import logging
import os

logger = logging.getLogger("bot.api_client")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class APIClient:
    """Cliente para comunicação com a API de inferência."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or API_BASE_URL
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def close(self):
        """Fecha a sessão HTTP."""
        await self._client.aclose()

    async def health(self) -> dict:
        """Verifica status da API."""
        try:
            response = await self._client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao verificar health: {e}")
            return {"status": "offline", "error": str(e)}

    async def predict_game(self, query: str) -> dict | None:
        """
        Faz predição completa (classificação + regressão) para um jogo.

        Parâmetros:
        - query (str): Nome ou AppID do jogo.

        Retorna:
        - dict | None: Resposta da API ou None se falhar.
        """
        try:
            response = await self._client.post(
                "/predict/game",
                json={"query": query},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Jogo não encontrado: {query}")
                return None
            logger.error(f"Erro HTTP na predição: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro na predição: {e}")
            return None

    async def search_games(self, query: str, limit: int = 5) -> list[dict]:
        """
        Busca jogos por nome.

        Parâmetros:
        - query (str): Query de busca.
        - limit (int): Máximo de resultados.

        Retorna:
        - list[dict]: Lista de jogos encontrados.
        """
        try:
            response = await self._client.get("/search", params={"q": query, "limit": limit})
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            logger.error(f"Erro na busca: {e}")
            return []
