import json
import os
import logging
from typing import Optional

logger = logging.getLogger("core.search")

class GameSearcher:
    def __init__(self):
        self._var_listAppList = []
        self._var_boolLoaded = False

    def _load_data(self):
        if self._var_boolLoaded:
            return

        var_strApplistPath = os.getenv("STEAM_APPLIST_PATH", "resources/dados/steam_applist.json")
        try:
            with open(var_strApplistPath, "r", encoding="utf-8") as var_fileApplist:
                self._var_listAppList = json.load(var_fileApplist)
            self._var_boolLoaded = True
            logger.info(f"Lista de jogos carregada. Total: {len(self._var_listAppList)} jogos.")
        except Exception as e:
            logger.error(f"Não foi possível carregar steam_applist.json em {var_strApplistPath}: {e}")

    def search_by_name(self, arg_strNameQuery: str) -> Optional[int]:
        self._load_data()

        if not self._var_listAppList:
            return None

        var_strQueryLower = arg_strNameQuery.lower().strip()

        # 1. Tentativa de match exato
        for var_dictGame in self._var_listAppList:
            if var_dictGame.get("name", "").lower() == var_strQueryLower:
                return var_dictGame["appid"]

        # 2. Tentativa de match parcial (começa com)
        for var_dictGame in self._var_listAppList:
            if var_dictGame.get("name", "").lower().startswith(var_strQueryLower):
                return var_dictGame["appid"]

        # 3. Tentativa de substring
        for var_dictGame in self._var_listAppList:
            if var_strQueryLower in var_dictGame.get("name", "").lower():
                return var_dictGame["appid"]

        return None

var_objSearcher = GameSearcher()
