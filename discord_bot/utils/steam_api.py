import aiohttp
import logging
import re
from bot.config import Config

logger = logging.getLogger(__name__)

class SteamAPI:
    """Steam Web API wrapper for fetching owned games and resolving Steam IDs"""
    
    BASE_URL = "https://api.steampowered.com"
    
    def __init__(self):
        self.api_key = Config.STEAM_API_KEY

    async def _get(self, interface: str, method: str, version: str, params: dict = None):
        """Internal method for GET requests to Steam API"""
        if not self.api_key:
            logger.error("STEAM_API_KEY is not set in Config")
            return None

        url = f"{self.BASE_URL}/{interface}/{method}/{version}/"
        
        request_params = {"key": self.api_key}
        if params:
            request_params.update(params)
            
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=request_params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"Steam API Error {response.status}: {error_text}")
                        return None
            except Exception as e:
                logger.error(f"Steam API Exception: {e}")
                return None

    async def resolve_vanity_url(self, vanity_url: str):
        """Resolve a Steam vanity URL to a SteamID64"""
        data = await self._get("ISteamUser", "ResolveVanityURL", "v1", {"vanityurl": vanity_url})
        if data and data.get("response", {}).get("success") == 1:
            return data["response"]["steamid"]
        return None

    async def get_steam_id(self, identifier: str):
        """
        Get SteamID64 from various input formats:
        - SteamID64 (17 digits)
        - Profile URL (https://steamcommunity.com/id/...)
        - Profiles URL (https://steamcommunity.com/profiles/...)
        - Vanity name (e.g., 'gabelogannewell')
        """
        # 1. Clean identifier
        identifier = identifier.strip().rstrip('/')
        
        # 2. Check if it's a URL
        if "steamcommunity.com/id/" in identifier:
            vanity_name = identifier.split("/id/")[-1]
            return await self.resolve_vanity_url(vanity_name)
        
        if "steamcommunity.com/profiles/" in identifier:
            return identifier.split("/profiles/")[-1]
            
        # 3. Check if it's already a SteamID64 (17 digits)
        if re.match(r'^\d{17}$', identifier):
            return identifier
            
        # 4. Assume it's a vanity name
        return await self.resolve_vanity_url(identifier)

    async def get_owned_games(self, steam_id: str):
        """Get list of games owned by a user"""
        params = {
            "steamid": steam_id,
            "format": "json",
            "include_appinfo": 1,
            "include_played_free_games": 1
        }
        data = await self._get("IPlayerService", "GetOwnedGames", "v1", params)
        
        if data and "response" in data and "games" in data["response"]:
            return data["response"]["games"]
        return []

    async def get_player_summaries(self, steam_ids: list):
        """Get player summaries (nickname, avatar, etc.)"""
        ids_str = ",".join(steam_ids)
        data = await self._get("ISteamUser", "GetPlayerSummaries", "v2", {"steamids": ids_str})
        
        if data and "response" in data and "players" in data["response"]:
            return data["response"]["players"]
        return []
