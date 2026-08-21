"""
Cliente da ITAD (IsThereAnyDeal) API v2.
Responsável por buscar o histórico de preços real.
Requer ITAD_API_KEY no .env.
"""

import logging
import httpx
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("core.itad_client")

CON_STR_ITAD_HISTORY_URL = "https://api.isthereanydeal.com/games/history/v2"
CON_STR_ITAD_API_KEY = os.getenv("ITAD_API_KEY")

_itad_cache = {}
CON_INT_CACHE_TTL = 300  # 5 minutos

class ITADClient:
    """
    Cliente para a ITAD API v2.
    """
    
    rate_limit_until = 0.0

    @staticmethod
    def _generate_mock_history(arg_intAppid: int, arg_floatPrecoBase: float) -> list[dict]:
        """Gera um histórico falso determinístico (para testes locais/fallback)."""
        import random
        from datetime import datetime, timedelta
        
        random.seed(arg_intAppid)
        var_listHistorico = []
        var_floatCurrentPrice = arg_floatPrecoBase if arg_floatPrecoBase > 0 else random.uniform(20.0, 200.0)
        var_dtNow = datetime.now()

        # Adicionar o primeiro ponto (início do histórico há 3 anos)
        var_listHistorico.append({
            "timestamp": int((var_dtNow - timedelta(days=365*3)).timestamp()),
            "preco": float(var_floatCurrentPrice),
            "desconto": 0,
            "fonte": "mock",
        })

        var_intNumPromos = random.randint(5, 15)
        for i in range(var_intNumPromos):
            var_intDaysAgo = random.randint(30, 365 * 3)
            var_dtPromo = var_dtNow - timedelta(days=var_intDaysAgo)

            var_intDiscount = random.choice([20, 30, 50, 60, 75, 80])
            var_floatPrecoPromo = var_floatCurrentPrice * (1 - (var_intDiscount / 100.0))

            var_listHistorico.append({
                "timestamp": int(var_dtPromo.timestamp()),
                "preco": float(var_floatPrecoPromo),
                "desconto": var_intDiscount,
                "fonte": "mock",
            })

            var_dtEndPromo = var_dtPromo + timedelta(days=random.randint(7, 14))
            var_listHistorico.append({
                "timestamp": int(var_dtEndPromo.timestamp()),
                "preco": float(var_floatCurrentPrice),
                "desconto": 0,
                "fonte": "mock",
            })

        var_listHistorico.sort(key=lambda x: x["timestamp"])

        var_listHistorico.append({
            "timestamp": int(var_dtNow.timestamp()),
            "preco": float(var_floatCurrentPrice),
            "desconto": 0,
            "fonte": "mock",
        })

        return var_listHistorico

    @staticmethod
    async def _get_with_retry(client: httpx.AsyncClient, url: str, params: dict, max_retries: int = 3) -> httpx.Response:
        import asyncio
        for attempt in range(max_retries):
            response = await client.get(url, params=params)
            if response.status_code == 429:
                try:
                    wait_time = int(response.headers.get("Retry-After", (2 ** attempt) * 2))
                except ValueError:
                    wait_time = (2 ** attempt) * 2
                    
                if wait_time > 10:
                    ITADClient.rate_limit_until = time.time() + wait_time
                    logger.error(f"ITAD API limite (429). Tempo de espera ({wait_time}s) é muito longo. Rate limit global ativado.")
                    return response
                    
                logger.warning(f"ITAD API limite (429). Retentando em {wait_time}s (tentativa {attempt+1}/{max_retries})...")
                await asyncio.sleep(wait_time)
                continue
            return response
        return await client.get(url, params=params)

    @staticmethod
    async def get_price_history(arg_intAppid: int, arg_floatPrecoBase: float = 0.0, arg_intAnos: int = 5) -> list[dict]:
        """
        Busca o histórico de preços real de um jogo via ITAD API.
        Usa o ITAD_API_KEY do .env. Se não configurado, gera erro ou lista vazia.

        Parâmetros:
        - arg_intAppid (int): AppID Steam.
        - arg_floatPrecoBase (float): (Usado no mock antigo, ignorado aqui).
        - arg_intAnos (int): Filtrar últimos anos.

        Retorna:
        - list[dict]: Lista de {timestamp, preco, desconto, fonte}, onde "fonte" é
          "real" (dados vindos da API ITAD) ou "mock" (fallback gerado localmente,
          usado quando ITAD_API_KEY está ausente, a API está em rate limit, ou
          qualquer erro impede a chamada real). Chamadores que exibem esse
          histórico ao usuário devem checar "fonte" e sinalizar quando os dados
          forem simulados.
        """
        if not CON_STR_ITAD_API_KEY:
            logger.error("ITAD_API_KEY não está configurado no .env. Impossível buscar histórico ITAD.")
            return ITADClient._generate_mock_history(arg_intAppid, arg_floatPrecoBase)
            
        var_floatNow = time.time()
        if var_floatNow < ITADClient.rate_limit_until:
            logger.warning(f"ITAD API bloqueada temporariamente (429). Tempo restante: {int(ITADClient.rate_limit_until - var_floatNow)}s")
            return ITADClient._generate_mock_history(arg_intAppid, arg_floatPrecoBase)
        var_strCacheKey = f"{arg_intAppid}_{arg_floatPrecoBase}"
        if var_strCacheKey in _itad_cache:
            var_listCachedData, var_floatTimestamp = _itad_cache[var_strCacheKey]
            if var_floatNow - var_floatTimestamp < CON_INT_CACHE_TTL:
                logger.info(f"ITAD API: Retornando histórico do appid {arg_intAppid} do cache local.")
                return var_listCachedData

        try:
            # Precisamos resolver o appid da steam para o plain/id do ITAD primeiro.
            # Mas a API v2 suporta busca direta por loja/appid dependendo do endpoint.
            # Vamos simplificar para o propósito do teste de integração da extensão:
            # O endpoint oficial v2 para steam precisa do id ITAD, mas /lookup/id/shop/appid existe.
            # Para não complicar a extensão que só tem 1 chamada, e porque os dados vêm da API:
            
            # 1. Lookup ID via Steam AppID
            var_strLookupUrl = "https://api.isthereanydeal.com/games/lookup/v1"
            var_dictHeaders = {"User-Agent": "SteamPrev-Extensao/1.0"}
            async with httpx.AsyncClient(timeout=10.0, headers=var_dictHeaders) as var_objClient:
                var_objResponseLookup = await ITADClient._get_with_retry(
                    var_objClient,
                    var_strLookupUrl,
                    params={"key": CON_STR_ITAD_API_KEY, "appid": arg_intAppid}
                )
                
                if var_objResponseLookup.status_code != 200:
                    logger.warning(f"ITAD API: Falha no lookup do appid {arg_intAppid} ({var_objResponseLookup.status_code})")
                    return []
                    
                var_dictLookup = var_objResponseLookup.json()
                if not var_dictLookup.get("found"):
                    return ITADClient._generate_mock_history(arg_intAppid, arg_floatPrecoBase)
                    
                var_strItadId = var_dictLookup["game"]["id"]
                
                # 2. Buscar Histórico
                var_objResponseHist = await ITADClient._get_with_retry(
                    var_objClient,
                    CON_STR_ITAD_HISTORY_URL,
                    params={"key": CON_STR_ITAD_API_KEY, "id": var_strItadId, "shops": 61, "country": "BR"} # 61 = Steam
                )
                
                if var_objResponseHist.status_code != 200:
                    logger.warning(f"ITAD API: Falha ao obter histórico ({var_objResponseHist.status_code})")
                    return ITADClient._generate_mock_history(arg_intAppid, arg_floatPrecoBase)
                    
                var_dictHistJson = var_objResponseHist.json()
                
                # 3. Parse e cálculo do desconto em cima do arg_floatPrecoBase
                var_listHistorico = []
                var_listDeals = var_dictHistJson if isinstance(var_dictHistJson, list) else var_dictHistJson.get("history", [])
                
                for var_dictDeal in var_listDeals:
                    var_dictDealInfo = var_dictDeal.get("deal") or {}
                    var_dictPrice = var_dictDealInfo.get("price") or {}
                    var_floatPrecoDeal = var_dictPrice.get("amount", 0.0)
                    var_dtDeal = datetime.fromisoformat(var_dictDeal["timestamp"].replace("Z", "+00:00"))
                    
                    # Calcula desconto real se o preço base for conhecido, senão usa do payload
                    var_intDesconto = var_dictDealInfo.get("cut", 0)
                    if arg_floatPrecoBase > 0 and var_floatPrecoDeal < arg_floatPrecoBase:
                        var_intDesconto = int(round((1 - (var_floatPrecoDeal / arg_floatPrecoBase)) * 100))
                    
                    var_listHistorico.append({
                        "timestamp": int(var_dtDeal.timestamp()),
                        "preco": float(var_floatPrecoDeal),
                        "desconto": var_intDesconto,
                        "fonte": "real",
                    })
                
                _itad_cache[var_strCacheKey] = (var_listHistorico, var_floatNow)
                return var_listHistorico

        except Exception as e:
            logger.error(f"ITAD API: Erro HTTP ao buscar histórico do appid {arg_intAppid}: {e}")
            return ITADClient._generate_mock_history(arg_intAppid, arg_floatPrecoBase)
