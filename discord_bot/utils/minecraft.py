import asyncio
import json
import re
import logging
import struct
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from bot.config import Config

logger = logging.getLogger(__name__)

_MINECRAFT_PLAYER_NAME_RE = re.compile(r"[A-Za-z0-9_]{1,16}")


def load_known_minecraft_players(path: str) -> List[str]:
    """Minecraft usercache.json에서 중복 없는 유효한 플레이어 명단을 읽습니다."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Minecraft usercache 형식이 올바르지 않습니다")

    players: Dict[str, str] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if isinstance(name, str) and _MINECRAFT_PLAYER_NAME_RE.fullmatch(name):
            players.setdefault(name.casefold(), name)

    return sorted(players.values(), key=str.casefold)


def parse_numismatics_balance(player: str, response: str) -> Optional[int]:
    """`numismatics view <player> SPUR` 응답에서 총 Spur 잔액을 추출합니다."""
    if not _MINECRAFT_PLAYER_NAME_RE.fullmatch(player):
        return None

    clean = MinecraftRCON._strip_minecraft_formatting(response)
    match = re.fullmatch(
        rf"{re.escape(player)} has (\d+) spurs?\.",
        clean,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


class MinecraftRCON:
    """
    마인크래프트 서버 RCON 클라이언트.

    봇 이미지에 별도 CLI를 설치하지 않고 Source RCON 프로토콜로
    서버에 직접 연결합니다.
    """

    _AUTH_PACKET_TYPE = 3
    _COMMAND_PACKET_TYPE = 2
    _REQUEST_ID = 1
    _TIMEOUT_SECONDS = 5
    _MAX_PACKET_LENGTH = 4 * 1024 * 1024

    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password

    async def send_command(self, command: str) -> Optional[str]:
        """
        Source RCON 프로토콜을 사용하여 명령어를 전송.
        """
        writer: Optional[asyncio.StreamWriter] = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self._TIMEOUT_SECONDS,
            )

            await self._send_packet(writer, self._AUTH_PACKET_TYPE, self.password)
            auth_request_id, _, _ = await asyncio.wait_for(
                self._read_packet(reader),
                timeout=self._TIMEOUT_SECONDS,
            )
            if auth_request_id == -1:
                logger.error("RCON 인증에 실패했습니다")
                return None

            await self._send_packet(writer, self._COMMAND_PACKET_TYPE, command)
            response_request_id, _, response = await asyncio.wait_for(
                self._read_packet(reader),
                timeout=self._TIMEOUT_SECONDS,
            )
            if response_request_id != self._REQUEST_ID:
                logger.error("RCON 응답의 요청 ID가 일치하지 않습니다")
                return None

            command_name = command.split(maxsplit=1)[0] if command else "<empty>"
            logger.info(f"RCON 명령어 실행 성공: {command_name}")
            return response.strip()
        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            logger.error(f"RCON 연결 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"RCON 실행 중 예외 발생: {e}")
            return None
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except (ConnectionError, OSError):
                    pass

    async def _send_packet(
        self,
        writer: asyncio.StreamWriter,
        packet_type: int,
        body: str,
    ) -> None:
        payload = struct.pack("<ii", self._REQUEST_ID, packet_type)
        payload += body.encode("utf-8") + b"\x00\x00"
        writer.write(struct.pack("<i", len(payload)) + payload)
        await writer.drain()

    async def _read_packet(
        self,
        reader: asyncio.StreamReader,
    ) -> Tuple[int, int, str]:
        length = struct.unpack("<i", await reader.readexactly(4))[0]
        if length < 10 or length > self._MAX_PACKET_LENGTH:
            raise ValueError(f"잘못된 RCON 패킷 길이: {length}")

        payload = await reader.readexactly(length)
        request_id, packet_type = struct.unpack("<ii", payload[:8])
        if payload[-2:] != b"\x00\x00":
            raise ValueError("잘못된 RCON 패킷 종료 문자")

        body = payload[8:-2].decode("utf-8", errors="replace")
        return request_id, packet_type, body

    async def get_players(self) -> Tuple[int, List[str]]:
        """
        서버에 접속한 플레이어 수와 목록 조회 (list 명령어)
        """
        response = await self.send_command("list")
        
        if not response:
            return (0, [])
        
        try:
            clean = self._strip_minecraft_formatting(response)
            logger.debug(f"Raw list response: {clean}")
            
            # 플레이어가 없는 경우
            no_player_patterns = [
                r"There are 0",
                r"no players",
                r"0/\d+ players",
            ]
            if any(re.search(p, clean, re.I) for p in no_player_patterns):
                # "online:" 뒤에 텍스트가 없으면 진짜 0명
                if "online:" not in clean or not clean.split("online:")[1].strip():
                    return (0, [])

            # "online:" 키워드를 기준으로 분리 시도
            # 예: "There are 1 of a max of 20 players online: user1"
            # 예: "1/20 players online: user1"
            if "online:" in clean:
                parts = clean.split("online:")
                pre_text = parts[0]  # 앞부분: 숫자 정보
                post_text = parts[1] # 뒷부분: 플레이어 목록
                
                # 앞부분에서 첫 번째로 나오는 숫자 추출 (현재 인원)
                count_match = re.search(r"(\d+)", pre_text)
                count = int(count_match.group(1)) if count_match else 0
                
                # 뒷부분에서 쉼표로 분리하여 목록 추출
                # 공백 제거 및 빈 문자열 제외
                players = [p.strip() for p in post_text.split(",") if p.strip()]
                
                # 만약 숫자는 0이 아닌데 목록이 비어있다면, 파싱 실패 가능성보다는 실제 닉네임이 공백일 순 없으니
                # 그냥 count와 players 반환 (비어있으면 비어있는 대로)
                return (count, players)
            
            # "online:" 키워드가 없는 경우 (비표준 응답)
            # 그냥 숫자만이라도 찾아서 리턴
            match = re.search(r"(\d+)(?:\s*(?:/|of a max)\s*\d+)?\s+players", clean, re.I)
            if match:
                return (int(match.group(1)), [])
            
            return (0, [])
            
        except Exception as e:
            logger.error(f"플레이어 목록 파싱 실패: {response}, 오류: {e}")
            return (0, [])

    async def get_numismatics_balance(self, player: str) -> Optional[int]:
        """Create: Numismatics 플레이어 은행 잔액을 Spur 단위로 조회합니다."""
        if not _MINECRAFT_PLAYER_NAME_RE.fullmatch(player):
            logger.warning("잘못된 Minecraft 플레이어 이름을 거부했습니다")
            return None

        response = await self.send_command(f"numismatics view {player} SPUR")
        if not response:
            return None
        return parse_numismatics_balance(player, response)

    @staticmethod
    def _strip_minecraft_formatting(text: str) -> str:
        """마인크래프트 색/포맷 코드 및 ANSI 코드를 제거."""
        # ANSI escape codes (예: [0m, [31m) 제거
        text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        # §x§1§2§3§4§5§6 (RGB) 제거
        text = re.sub(r"§x(§[0-9a-fA-F]){6}", "", text)
        # § + 단일 문자 제거
        text = re.sub(r"§.", "", text)
        return text.strip()

    async def get_tps(self) -> Optional[List[Dict[str, Any]]]:
        """
        서버 TPS/틱 타임 조회. spark tps를 최우선으로 시도.
        """
        # 1. spark tps (Better MC 등 최신 모드팩 표준)
        spark_resp = await self.send_command("spark tps")
        if spark_resp and not re.search(r"unknown command", spark_resp, re.I):
            clean_spark = self._strip_minecraft_formatting(spark_resp)
            logger.debug(f"Raw spark tps response: {clean_spark}")
            parsed = self._parse_spark_tps(clean_spark)
            if parsed:
                return parsed

        # 2. forge tps / tps fallback
        for cmd in ("forge tps", "tps"):
            response = await self.send_command(cmd)
            if not response or re.search(r"unknown command", response, re.I):
                continue
            clean = self._strip_minecraft_formatting(response)
            parsed = self._parse_forge_tps(clean)
            if parsed:
                return parsed
        
        return None

    def _parse_spark_tps(self, response: str) -> Optional[List[Dict[str, Any]]]:
        """
        spark tps 응답 파싱.
        예: "TPS from last 1m, 5m, 15m: 20.0, 19.95, 20.0"
        MSPT(Tick Time)은 별도 명령(spark mspt)이 필요할 수 있으나, 일단 TPS만이라도 추출.
        """
        # TPS from last 1m, 5m, 15m: 20.0, 20.0, 20.0
        match = re.search(r"TPS from last 1m, 5m, 15m:\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)", response, re.I)
        if match:
            # 가장 최근인 1m TPS 사용
            tps_1m = float(match.group(1))
            return [{
                "dimension": "Server (Spark)",
                "tick_time_ms": 0.0, # spark tps엔 MSPT가 안 나올 수 있음
                "tps": tps_1m
            }]
        return None

    def _parse_forge_tps(self, response: str) -> Optional[List[Dict[str, Any]]]:
        """기존 forge tps 파싱 로직 개선."""
        result = []
        # Mean tick time: 5.432 ms. Mean TPS: 20.000
        tick_re = re.compile(r"tick\s+time:\s*([\d.]+)\s*ms", re.I)
        tps_re = re.compile(r"TPS:\s*([\d.]+)", re.I)
        dim_re = re.compile(r"Dim\s+([\w:]+)\s*\(", re.I)
        
        lines = [line.strip() for line in response.split("\n") if line.strip()]
        for line in lines:
            tick_m = tick_re.search(line)
            tps_m = tps_re.search(line)
            if not (tick_m and tps_m):
                continue
            
            dim_m = dim_re.search(line)
            if "Overall" in line:
                dim = "Overall"
            elif dim_m:
                dim = self._dimension_display_name(dim_m.group(1))
            else:
                dim = "Server"
                
            result.append({
                "dimension": dim,
                "tick_time_ms": float(tick_m.group(1)),
                "tps": float(tps_m.group(1)),
            })
        
        return result if result else None

    def _dimension_display_name(self, raw: str) -> str:
        known = {
            "minecraft:overworld": "Overworld",
            "minecraft:the_nether": "The Nether",
            "minecraft:the_end": "The End",
        }
        if raw in known:
            return known[raw]
        if ":" in raw:
            raw = raw.split(":")[-1]
        return raw.replace("_", " ").title()


def get_minecraft_rcon() -> Optional[MinecraftRCON]:
    host = Config.MINECRAFT_RCON_HOST
    port = Config.MINECRAFT_RCON_PORT
    password = Config.MINECRAFT_RCON_PASSWORD
    
    if not all([host, password]):
        logger.warning("마인크래프트 RCON 설정이 완료되지 않았습니다")
        return None
    
    return MinecraftRCON(host, port, password)
