import aiohttp
import logging
from bot.config import Config

logger = logging.getLogger(__name__)

class OverwatchAPI:
    """Overwatch 2 API wrapper using OverFast API"""
    
    BASE_URL = "https://overfast-api.tekrop.fr"
    
    def __init__(self):
        # OverFast API doesn't require an API key for public endpoints
        self.headers = {
            "Accept": "application/json"
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
                        logger.warning(f"Overwatch API 404: {url}")
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Overwatch API Error {response.status}: {error_text}")
                        return None
            except Exception as e:
                logger.error(f"Overwatch API Exception: {e}")
                return None

    async def search_players(self, nickname: str):
        """Search for players by nickname"""
        endpoint = "/players"
        params = {"name": nickname}
        return await self._get(endpoint, params=params)

    async def get_player_summary(self, player_id: str):
        """Get player summary by player_id (e.g., Name-1234)"""
        endpoint = f"/players/{player_id}/summary"
        return await self._get(endpoint)

    async def get_player_stats(self, player_id: str, gamemode: str = "competitive"):
        """Get player career stats by player_id"""
        endpoint = f"/players/{player_id}/stats/career"
        params = {"gamemode": gamemode}
        return await self._get(endpoint, params=params)

    @staticmethod
    def format_player_id(battletag: str) -> str:
        """Helper to format BattleTag (Name#1234) to player_id (Name-1234)"""
        return battletag.replace("#", "-")
