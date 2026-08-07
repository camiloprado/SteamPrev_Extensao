"""
Módulo de busca de jogos Steam por nome aproximado.
Carrega o catálogo steam_applist.json e permite busca fuzzy por nome.
"""

import json
import os
import logging
from pathlib import Path
from unidecode import unidecode

logger = logging.getLogger("core.game_search")

# Cache global do catálogo
_GAME_CATALOG: list[dict] = []
_GAME_CATALOG_NORMALIZED: list[tuple[str, int, str]] = []  # (nome_normalizado, appid, nome_original)


def _normalize_name(name: str) -> str:
    """Normaliza o nome do jogo para comparação: minúsculo, sem acentos, sem caracteres especiais."""
    return unidecode(name).lower().strip()


def _load_catalog() -> None:
    """Carrega o catálogo de jogos a partir do JSON."""
    global _GAME_CATALOG, _GAME_CATALOG_NORMALIZED

    if _GAME_CATALOG:
        return  # Já carregado

    catalog_path = os.getenv(
        "STEAM_APPLIST_PATH",
        str(Path(__file__).resolve().parents[1] / "resources" / "dados" / "steam_applist.json")
    )

    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            _GAME_CATALOG = json.load(f)

        _GAME_CATALOG_NORMALIZED = [
            (_normalize_name(game["name"]), game["appid"], game["name"])
            for game in _GAME_CATALOG
            if game.get("name")
        ]

        logger.info(f"Catálogo carregado: {len(_GAME_CATALOG_NORMALIZED)} jogos.")
    except FileNotFoundError:
        logger.warning(f"Arquivo de catálogo não encontrado: {catalog_path}")
    except Exception as e:
        logger.error(f"Erro ao carregar catálogo: {e}")


def search_games(query: str, max_results: int = 10) -> list[dict]:
    """
    Busca jogos por nome aproximado.

    Estratégia de ranking:
    1. Match exato (normalizado)
    2. Começa com a query
    3. Contém a query
    4. Todas as palavras da query presentes

    Parâmetros:
    - query (str): Nome ou parte do nome do jogo.
    - max_results (int): Máximo de resultados a retornar.

    Retorna:
    - list[dict]: Lista de dicts com 'appid' e 'name'.
    """
    _load_catalog()

    if not query or not query.strip():
        return []

    query_norm = _normalize_name(query)
    query_words = query_norm.split()

    exact_matches = []
    starts_with = []
    contains = []
    word_matches = []

    for name_norm, appid, name_original in _GAME_CATALOG_NORMALIZED:
        if name_norm == query_norm:
            exact_matches.append({"appid": appid, "name": name_original})
        elif name_norm.startswith(query_norm):
            starts_with.append({"appid": appid, "name": name_original})
        elif query_norm in name_norm:
            contains.append({"appid": appid, "name": name_original})
        elif all(word in name_norm for word in query_words):
            word_matches.append({"appid": appid, "name": name_original})

    # Combina resultados priorizando matches melhores
    results = exact_matches + starts_with + contains + word_matches
    return results[:max_results]


def get_game_by_appid(appid: int) -> dict | None:
    """
    Busca um jogo pelo AppID exato.

    Parâmetros:
    - appid (int): AppID do jogo na Steam.

    Retorna:
    - dict | None: Dict com 'appid' e 'name', ou None se não encontrado.
    """
    _load_catalog()

    for _, game_appid, name_original in _GAME_CATALOG_NORMALIZED:
        if game_appid == appid:
            return {"appid": appid, "name": name_original}

    return None


def get_game_by_name_or_id(query: str) -> dict | None:
    """
    Busca um jogo por AppID (se numérico) ou por nome (melhor match).

    Parâmetros:
    - query (str): AppID ou nome do jogo.

    Retorna:
    - dict | None: Dict com 'appid' e 'name', ou None se não encontrado.
    """
    # Tenta como AppID primeiro
    try:
        appid = int(query.strip())
        result = get_game_by_appid(appid)
        if result:
            return result
    except ValueError:
        pass

    # Busca por nome
    results = search_games(query, max_results=1)
    return results[0] if results else None
