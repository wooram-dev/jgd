import logging
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

import httpx

from bot.config import Config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PalworldPlayer:
    """팰월드 REST API의 접속 플레이어 정보."""

    name: str
    level: Optional[int]
    ping: Optional[float] = None
    building_count: Optional[int] = None


class PalworldAPI:
    """팰월드 REST API 클라이언트."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)

    async def _get_players_payload(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/players", auth=self.auth)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("Palworld REST API 응답 오류: %s", e)
            return {}
        except httpx.HTTPError as e:
            logger.error("Palworld REST API 요청 실패: %s", e)
            return {}
        except ValueError as e:
            logger.error("Palworld REST API JSON 파싱 실패: %s", e)
            return {}

    def _player_name(self, player: dict[str, Any]) -> str:
        return str(player.get("name") or player.get("accountName") or "").strip()

    def _optional_int(self, value: Any) -> Optional[int]:
        if value is None or value == "":
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _optional_float(self, value: Any) -> Optional[float]:
        if value is None or value == "":
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def get_players(self) -> Tuple[int, List[str]]:
        """서버에 접속한 플레이어 수와 목록을 조회합니다."""
        payload = await self._get_players_payload()

        players = []
        for player in payload.get("players", []):
            name = self._player_name(player)
            if name:
                players.append(name)

        return (len(players), players)

    async def get_player_details(self) -> List[PalworldPlayer]:
        """서버에 접속한 플레이어의 공개 가능한 상세 정보를 조회합니다."""
        payload = await self._get_players_payload()

        players: List[PalworldPlayer] = []
        for player in payload.get("players", []):
            name = self._player_name(player)
            if not name:
                continue

            players.append(
                PalworldPlayer(
                    name=name,
                    level=self._optional_int(player.get("level")),
                    ping=self._optional_float(player.get("ping")),
                    building_count=self._optional_int(player.get("building_count")),
                )
            )

        return players


def get_palworld_api() -> Optional[PalworldAPI]:
    base_url = Config.PALWORLD_API_BASE_URL
    username = Config.PALWORLD_API_USERNAME
    password = Config.PALWORLD_API_PASSWORD

    if not all([base_url, username, password]):
        logger.warning("팰월드 REST API 설정이 완료되지 않았습니다")
        return None

    return PalworldAPI(base_url, username, password)


def get_palworld_rcon() -> Optional[PalworldAPI]:
    """이전 command 코드와 호환하기 위한 alias."""
    return get_palworld_api()
