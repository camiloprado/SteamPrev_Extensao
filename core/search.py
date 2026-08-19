import json
import os
import logging
from typing import Optional

logger = logging.getLogger("core.search")

class GameSearcher:
    def __init__(self):
        self.app_list = []
        self._loaded = False

    def _load_data(self):
        if self._loaded:
            return
            
        applist_path = os.getenv("STEAM_APPLIST_PATH", "resources/dados/steam_applist.json")
        try:
            with open(applist_path, "r", encoding="utf-8") as f:
                self.app_list = json.load(f)
            self._loaded = True
            logger.info(f"Lista de jogos carregada. Total: {len(self.app_list)} jogos.")
        except Exception as e:
            logger.error(f"Não foi possível carregar steam_applist.json em {applist_path}: {e}")

    def search_by_name(self, name_query: str) -> Optional[int]:
        self._load_data()
        
        if not self.app_list:
            return None
            
        query_lower = name_query.lower().strip()
        
        # 1. Tentativa de match exato
        for game in self.app_list:
            if game.get("name", "").lower() == query_lower:
                return game["appid"]
                
        # 2. Tentativa de match parcial (começa com)
        for game in self.app_list:
            if game.get("name", "").lower().startswith(query_lower):
                return game["appid"]

        # 3. Tentativa de substring
        for game in self.app_list:
            if query_lower in game.get("name", "").lower():
                return game["appid"]
                
        return None

searcher = GameSearcher()
