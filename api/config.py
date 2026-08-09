"""Configuração centralizada da API via variáveis de ambiente."""

from pydantic_settings import BaseSettings
from pathlib import Path


class APISettings(BaseSettings):
    """
    Settings da API de inferência.
    Renomeada para APISettings para evitar colisão com a classe Settings do projeto base.
    """

    # Servidor
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Modelos
    MODELS_PATH: str = str(Path(__file__).resolve().parents[1] / "resources" / "models")
    MODELS_BASE_URL: str = "https://github.com/camiloprado/SteamPrev_Machine_Learning/releases/latest/download"

    # APIs externas (opcionais)
    STEAM_API_KEY: str = ""
    ITAD_API_KEY: str = ""

    # Catálogo
    STEAM_APPLIST_PATH: str = str(
        Path(__file__).resolve().parents[1] / "resources" / "dados" / "steam_applist.json"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


api_settings = APISettings()
