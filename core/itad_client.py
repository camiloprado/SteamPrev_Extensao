"""
Cliente mockado da IsThereAnyDeal (ITAD) API.
Retorna histórico de preços simulado para desenvolvimento e testes.
Preparado para substituição por chamadas reais à API ITAD v2.
"""

import logging
import random
from datetime import datetime, timedelta

logger = logging.getLogger("core.itad_client")


def _generate_mock_history(base_price: float, years: int = 5) -> list[dict]:
    """
    Gera histórico de preços mockado para um jogo.

    Simula padrões reais:
    - Preço base estável com promoções periódicas
    - Descontos maiores em Steam Sales sazonais
    - Frequência de promoções varia por jogo

    Parâmetros:
    - base_price (float): Preço base do jogo.
    - years (int): Anos de histórico a gerar.

    Retorna:
    - list[dict]: Lista de pontos {timestamp, preco, desconto}.
    """
    if base_price <= 0:
        return []

    historico = []
    now = datetime.now()
    start = now - timedelta(days=years * 365)

    # Gera pontos a cada 15-45 dias
    current = start
    while current < now:
        # Determina se é período de promoção
        doy = current.timetuple().tm_yday
        is_sale_season = any(abs(doy - sale_day) < 15 for sale_day in [75, 177, 327, 355])

        if is_sale_season and random.random() < 0.6:
            # Promoção sazonal: desconto de 20-75%
            desconto = random.choice([20, 25, 30, 33, 40, 50, 60, 66, 75])
            preco = round(base_price * (1 - desconto / 100), 2)
        elif random.random() < 0.1:
            # Promoção aleatória: desconto de 10-40%
            desconto = random.choice([10, 15, 20, 25, 30, 33, 40])
            preco = round(base_price * (1 - desconto / 100), 2)
        else:
            # Preço normal
            desconto = 0
            preco = base_price

        historico.append({
            "timestamp": int(current.timestamp()),
            "preco": preco,
            "desconto": desconto,
        })

        # Próximo ponto: 7-45 dias
        current += timedelta(days=random.randint(7, 45))

    return historico


class ITADClient:
    """
    Cliente para a IsThereAnyDeal API v2.
    Implementação mockada para desenvolvimento.
    """

    @staticmethod
    def get_price_history(appid: int, base_price: float = 0.0) -> list[dict]:
        """
        Obtém o histórico de preços de um jogo.

        Parâmetros:
        - appid (int): AppID do jogo na Steam.
        - base_price (float): Preço base para gerar histórico simulado.

        Retorna:
        - list[dict]: Lista de pontos com timestamp, preco e desconto.
        """
        logger.debug(f"ITAD mock: gerando histórico para AppID {appid}")
        return _generate_mock_history(base_price)

    @staticmethod
    def get_lowest_price(appid: int, base_price: float = 0.0) -> dict:
        """
        Obtém o menor preço histórico de um jogo.

        Parâmetros:
        - appid (int): AppID do jogo.
        - base_price (float): Preço base para referência.

        Retorna:
        - dict: {price, discount, date}
        """
        history = ITADClient.get_price_history(appid, base_price)
        if not history:
            return {"price": base_price, "discount": 0, "date": "N/A"}

        lowest = min(history, key=lambda x: x["preco"])
        return {
            "price": lowest["preco"],
            "discount": lowest["desconto"],
            "date": datetime.fromtimestamp(lowest["timestamp"]).strftime("%Y-%m-%d"),
        }
