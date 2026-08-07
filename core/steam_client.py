"""
Cliente mockado da Steam Store API.
Retorna dados simulados para desenvolvimento e testes.
Preparado para substituição por chamadas reais à API.
"""

import logging
from datetime import datetime, timedelta
import random

logger = logging.getLogger("core.steam_client")

# Dados mockados de jogos populares
MOCK_GAMES = {
    730: {
        "name": "Counter-Strike 2",
        "appid": 730,
        "is_free": True,
        "price": 0.0,
        "review_score": 83,
        "total_reviews": 7500000,
        "release_date": "2012-08-21",
        "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/730/header.jpg",
    },
    1245620: {
        "name": "ELDEN RING",
        "appid": 1245620,
        "is_free": False,
        "price": 249.90,
        "review_score": 81,
        "total_reviews": 650000,
        "release_date": "2022-02-25",
        "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1245620/header.jpg",
    },
    413150: {
        "name": "Stardew Valley",
        "appid": 413150,
        "is_free": False,
        "price": 24.99,
        "review_score": 97,
        "total_reviews": 600000,
        "release_date": "2016-02-26",
        "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/413150/header.jpg",
    },
    1091500: {
        "name": "Cyberpunk 2077",
        "appid": 1091500,
        "is_free": False,
        "price": 199.90,
        "review_score": 76,
        "total_reviews": 800000,
        "release_date": "2020-12-10",
        "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1091500/header.jpg",
    },
    892970: {
        "name": "Valheim",
        "appid": 892970,
        "is_free": False,
        "price": 69.99,
        "review_score": 95,
        "total_reviews": 400000,
        "release_date": "2021-02-02",
        "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/892970/header.jpg",
    },
    570: {
        "name": "Dota 2",
        "appid": 570,
        "is_free": True,
        "price": 0.0,
        "review_score": 77,
        "total_reviews": 2000000,
        "release_date": "2013-07-09",
        "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/570/header.jpg",
    },
    1174180: {
        "name": "Red Dead Redemption 2",
        "appid": 1174180,
        "is_free": False,
        "price": 299.90,
        "review_score": 85,
        "total_reviews": 450000,
        "release_date": "2019-12-05",
        "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1174180/header.jpg",
    },
    105600: {
        "name": "Terraria",
        "appid": 105600,
        "is_free": False,
        "price": 39.99,
        "review_score": 97,
        "total_reviews": 1000000,
        "release_date": "2011-05-16",
        "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/105600/header.jpg",
    },
}


def _generate_mock_price(base_price: float) -> float:
    """Gera preço com pequena variação aleatória."""
    if base_price == 0:
        return 0.0
    variation = random.uniform(-0.15, 0.05)
    return round(max(base_price * (1 + variation), base_price * 0.3), 2)


def _generate_default_mock(appid: int) -> dict:
    """Gera dados mockados genéricos para AppIDs desconhecidos."""
    return {
        "name": f"Jogo Steam #{appid}",
        "appid": appid,
        "is_free": False,
        "price": round(random.uniform(19.99, 299.90), 2),
        "review_score": random.randint(50, 95),
        "total_reviews": random.randint(100, 50000),
        "release_date": f"{random.randint(2015, 2025)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
        "header_image": f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg",
    }


class SteamClient:
    """
    Cliente para a Steam Store API.
    Implementação mockada para desenvolvimento.
    """

    @staticmethod
    def get_game_data(appid: int) -> dict | None:
        """
        Obtém dados de um jogo pelo AppID.

        Parâmetros:
        - appid (int): AppID do jogo na Steam.

        Retorna:
        - dict | None: Dados do jogo ou None se não encontrado.
        """
        if appid in MOCK_GAMES:
            logger.debug(f"Steam mock: retornando dados de {MOCK_GAMES[appid]['name']}")
            return MOCK_GAMES[appid].copy()

        # Gera dados genéricos para AppIDs desconhecidos
        logger.debug(f"Steam mock: gerando dados genéricos para AppID {appid}")
        return _generate_default_mock(appid)

    @staticmethod
    def get_game_price(appid: int) -> float:
        """
        Obtém o preço atual de um jogo.

        Parâmetros:
        - appid (int): AppID do jogo.

        Retorna:
        - float: Preço do jogo em BRL.
        """
        data = SteamClient.get_game_data(appid)
        return data["price"] if data else 0.0
