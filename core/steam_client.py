"""
Cliente da Steam Store API.
Responsável por buscar os dados reais de jogos na Steam via HTTP.
"""

import logging
import httpx
import time
from datetime import datetime

logger = logging.getLogger("core.steam_client")

CON_STR_STEAM_API_URL = "https://store.steampowered.com/api/appdetails"

_steam_cache = {}
CON_INT_CACHE_TTL = 300  # 5 minutos

class SteamClient:
    """
    Cliente para a Steam Store API.
    Implementação real que consome os endpoints oficiais.
    """

    @staticmethod
    async def get_game_data(arg_intAppid: int) -> dict | None:
        """
        Obtém dados de um jogo pelo AppID chamando a Steam Store API.

        Parâmetros:
        - arg_intAppid (int): AppID do jogo na Steam.

        Retorna:
        Retorna:
        - dict | None: Dados do jogo parseados ou None se falhar.
        """
        var_floatNow = time.time()
        if arg_intAppid in _steam_cache:
            var_dictCachedData, var_floatTimestamp = _steam_cache[arg_intAppid]
            if var_floatNow - var_floatTimestamp < CON_INT_CACHE_TTL:
                logger.info(f"Steam API: Retornando appid {arg_intAppid} do cache local.")
                return var_dictCachedData

        try:
            async with httpx.AsyncClient(timeout=10.0) as var_objClient:
                var_objResponse = await var_objClient.get(
                    CON_STR_STEAM_API_URL,
                    params={"appids": str(arg_intAppid), "cc": "br"}
                )
                var_objResponse.raise_for_status()
                var_dictJson = var_objResponse.json()

                var_strAppid = str(arg_intAppid)
                if var_strAppid not in var_dictJson or not var_dictJson[var_strAppid].get("success"):
                    logger.warning(f"Steam API: Falha ao obter dados (sucesso=false) para appid {arg_intAppid}")
                    return None

                var_dictData = var_dictJson[var_strAppid]["data"]

                # Parse de preço
                var_boolIsFree = var_dictData.get("is_free", False)
                var_floatPrice = 0.0
                var_intDiscountPercent = 0
                var_boolIsOnSale = False
                
                if not var_boolIsFree:
                    if "price_overview" in var_dictData:
                        try:
                            var_dictPriceOverview = var_dictData["price_overview"]
                            if "final" not in var_dictPriceOverview:
                                raise ValueError("Chave 'final' não encontrada no nó 'price_overview'.")
                            
                            var_intFinalRaw = int(var_dictPriceOverview["final"])
                            var_floatPrice = round(var_intFinalRaw / 100.0, 2)
                            var_intDiscountPercent = int(var_dictPriceOverview.get("discount_percent", 0))
                            var_boolIsOnSale = var_intDiscountPercent > 0
                        except (ValueError, TypeError, KeyError) as e:
                            logger.error(f"Steam API: Erro crítico de parsing de preço para appid {arg_intAppid}. Estrutura JSON possivelmente alterada. Detalhes: {e}")
                            raise ValueError(f"Falha no parser de preço da Steam: {e}")
                    else:
                        # Jogos pagos sem price_overview não estão à venda (ex: removidos da loja)
                        var_floatPrice = 0.0

                # Parse reviews (appdetails tem metacritic)
                var_intReviewScore = 0
                if "metacritic" in var_dictData:
                    var_intReviewScore = var_dictData["metacritic"].get("score", 0)
                else:
                    var_intReviewScore = 50 # Default safe fallback

                # Monta dict compatível com a inferência
                var_dictResult = {
                    "name": var_dictData.get("name", f"Jogo {arg_intAppid}"),
                    "appid": arg_intAppid,
                    "is_free": var_boolIsFree,
                    "price": var_floatPrice,
                    "discount_percent": var_intDiscountPercent,
                    "is_on_sale": var_boolIsOnSale,
                    "sale_end_date": None, # Placeholder futuramente consumível via ITAD/web scraping
                    "review_score": var_intReviewScore,
                    "total_reviews": 1000,
                    "release_date": var_dictData.get("release_date", {}).get("date", "2020-01-01"),
                    "header_image": var_dictData.get("header_image", ""),
                }
                _steam_cache[arg_intAppid] = (var_dictResult, var_floatNow)
                return var_dictResult

        except Exception as e:
            logger.error(f"Steam API: Erro HTTP ao buscar appid {arg_intAppid}: {e}")
            return None

    @staticmethod
    async def get_game_price(arg_intAppid: int) -> float:
        """
        Obtém apenas o preço atual de um jogo.

        Parâmetros:
        - arg_intAppid (int): AppID do jogo.

        Retorna:
        - float: Preço do jogo em BRL.
        """
        var_dictData = await SteamClient.get_game_data(arg_intAppid)
        return var_dictData["price"] if var_dictData else 0.0
