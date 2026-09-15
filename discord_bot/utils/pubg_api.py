import aiohttp
import logging
import time
from bot.config import Config

logger = logging.getLogger(__name__)

class PUBGAPI:
    """PUBG API wrapper for Steam platform with caching support"""
    
    BASE_URL = "https://api.pubg.com"
    SHARD = "steam"
    
    # Caching
    _season_cache = {"id": None, "timestamp": 0}
    _player_cache = {} # nickname -> account_id
    SEASON_CACHE_TTL = 86400 # 24 hours
    
    def __init__(self):
        self.api_key = Config.PUBG_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/vnd.api+json"
        }

    async def _get(self, endpoint: str, params: dict = None):
        """Internal method for GET requests"""
        url = f"{self.BASE_URL}{endpoint}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        logger.warning(f"PUBG API 404: {url}")
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(f"PUBG API Error {response.status}: {error_text}")
                        return None
            except Exception as e:
                logger.error(f"PUBG API Exception: {e}")
                return None

    async def get_player_by_nickname(self, nickname: str):
        """Get player info (including account id) by nickname with caching"""
        # Check cache first
        if nickname in self._player_cache:
            return {"id": self._player_cache[nickname], "attributes": {"name": nickname}}

        endpoint = f"/shards/{self.SHARD}/players"
        params = {"filter[playerNames]": nickname}
        data = await self._get(endpoint, params=params)
        
        if data and "data" in data and len(data["data"]) > 0:
            player_data = data["data"][0]
            # Save to cache
            self._player_cache[nickname] = player_data["id"]
            return player_data
        return None

    async def get_seasons(self):
        """Get current season info with caching"""
        now = time.time()
        if self._season_cache["id"] and (now - self._season_cache["timestamp"] < self.SEASON_CACHE_TTL):
            return {"id": self._season_cache["id"], "attributes": {"isCurrentSeason": True}}

        endpoint = f"/shards/{self.SHARD}/seasons"
        data = await self._get(endpoint)
        
        if data and "data" in data:
            for season in data["data"]:
                if season.get("attributes", {}).get("isCurrentSeason"):
                    # Update cache
                    self._season_cache["id"] = season["id"]
                    self._season_cache["timestamp"] = now
                    return season
        return None

    async def get_player_season_stats(self, account_id: str, season_id: str):
        """Get player stats for a specific season"""
        endpoint = f"/shards/{self.SHARD}/players/{account_id}/seasons/{season_id}"
        return await self._get(endpoint)

    async def get_player_lifetime_stats(self, account_id: str):
        """Get player lifetime stats"""
        endpoint = f"/shards/{self.SHARD}/players/{account_id}/seasons/lifetime"
        return await self._get(endpoint)

    async def get_player_ranked_stats(self, account_id: str, season_id: str):
        """Get player ranked stats for a specific season"""
        endpoint = f"/shards/{self.SHARD}/players/{account_id}/seasons/{season_id}/ranked"
        return await self._get(endpoint)
