import aiohttp
import logging
from typing import Optional, List, Dict, Any
from bot.config import Config

logger = logging.getLogger(__name__)

class RiotAPI:
    """Riot API helper class for League of Legends data"""
    
    BASE_URL_ASIA = "https://asia.api.riotgames.com"
    BASE_URL_KR = "https://kr.api.riotgames.com"
    
    def __init__(self):
        self.api_key = Config.RIOT_API_KEY
        if not self.api_key:
            logger.error("RIOT_API_KEY is not set in Config")
            
    async def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Internal helper for GET requests"""
        if not self.api_key:
            return None
            
        headers = {"X-Riot-Token": self.api_key}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_data = await response.text()
                        logger.error(f"Riot API error: {response.status} for {url}. Response: {error_data}")
                        return None
            except Exception as e:
                logger.error(f"Failed to fetch from Riot API: {e}")
                return None

    async def get_account_by_riot_id(self, game_name: str, tag_line: str = "KR1") -> Optional[str]:
        """Fetch account by Riot ID (Name#Tag)"""
        import urllib.parse
        encoded_name = urllib.parse.quote(game_name)
        encoded_tag = urllib.parse.quote(tag_line)
        url = f"{self.BASE_URL_ASIA}/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
        return await self._get(url) or []

    async def get_summoner_by_puuid(self, puuid: str) -> Optional[Dict[str, Any]]:
        """Fetch summoner information by PUUID"""
        url = f"{self.BASE_URL_KR}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        return await self._get(url)

    async def get_league_entries(self, puuid: str) -> List[Dict[str, Any]]:
        """Fetch league entries (rank) for a PUUID"""
        url = f"{self.BASE_URL_KR}/lol/league/v4/entries/by-puuid/{puuid}"
        return await self._get(url) or []

    async def get_top_champion_masteries(self, puuid: str, count: int = 3) -> List[Dict[str, Any]]:
        """Fetch top champion masteries for a PUUID"""
        url = f"{self.BASE_URL_KR}/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top"
        params = {"count": count}
        return await self._get(url, params=params) or []

    async def get_match_ids(self, puuid: str, count: int = 5) -> List[str]:
        """Fetch recent match IDs for a PUUID"""
        url = f"{self.BASE_URL_ASIA}/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"start": 0, "count": count}
        return await self._get(url, params=params) or []

    async def get_match_detail(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed match information by match ID"""
        url = f"{self.BASE_URL_ASIA}/lol/match/v5/matches/{match_id}"
        return await self._get(url)

    async def get_latest_version(self) -> str:
        """Fetch the latest Data Dragon version"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("https://ddragon.leagueoflegends.com/api/versions.json") as resp:
                    if resp.status == 200:
                        versions = await resp.json()
                        return versions[0]
            except Exception as e:
                logger.error(f"Failed to fetch latest version: {e}")
        return "14.3.1"  # Fallback version

    async def get_champion_map(self) -> Dict[int, str]:
        """Fetch champion ID to name mapping from Data Dragon"""
        latest_version = await self.get_latest_version()
        async with aiohttp.ClientSession() as session:
            try:
                # Get champion data in Korean
                url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ko_KR/champion.json"
                async with session.get(url) as resp:
                    if resp.status != 200: return {}
                    data = await resp.json()
                    
                # 3. Create mapping (key is champion ID as int)
                champ_map = {}
                for champ_info in data['data'].values():
                    champ_map[int(champ_info['key'])] = champ_info['name']
                return champ_map
            except Exception as e:
                logger.error(f"Failed to fetch champion map: {e}")
                return {}