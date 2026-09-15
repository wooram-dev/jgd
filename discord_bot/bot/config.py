import os
from pathlib import Path
from dotenv import load_dotenv

# 1. 공통 환경 설정 (상위 디렉토리 .env)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if (ROOT_DIR / ".env").exists():
    load_dotenv(ROOT_DIR / ".env")

# 2. 봇 개별 환경 설정 (discord_bot/.env) - 상위 설정을 덮어씌움
BOT_DIR = Path(__file__).resolve().parent.parent
if (BOT_DIR / ".env").exists():
    load_dotenv(BOT_DIR / ".env", override=True)

class Config:
    """Bot configuration class"""
    
    # Discord settings
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    GUILD_ID = os.getenv('GUILD_ID')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_CHAT_CHANNEL_ID = os.getenv('GEMINI_CHAT_CHANNEL_ID')
    
    # Bot settings
    BOT_PREFIX = os.getenv('BOT_PREFIX', '!')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Disabled commands (comma-separated list, e.g., 'ping,ow')
    DISABLED_COMMANDS = [cmd.strip() for cmd in os.getenv('DISABLED_COMMANDS', '').split(',') if cmd.strip()]
    
    # Riot API settings
    RIOT_API_KEY = os.getenv('RIOT_API_KEY')
    
    # PUBG API settings
    PUBG_API_KEY = os.getenv('PUBG_API_KEY')
    
    # Steam API settings
    STEAM_API_KEY = os.getenv('STEAM_API_KEY')
    
    # Minecraft server settings (Sunlit Valley 컨테이너는 Compose에서 명시적으로 주입)
    # MINECRAFT_RCON_HOST / MC_SERVER_HOST, RCON_PASSWORD / MINECRAFT_RCON_PASSWORD
    MINECRAFT_RCON_HOST = os.getenv('MINECRAFT_RCON_HOST') or os.getenv('MC_SERVER_HOST', 'localhost')
    MINECRAFT_RCON_PORT = int(os.getenv('MINECRAFT_RCON_PORT', '25575'))
    MINECRAFT_RCON_PASSWORD = os.getenv('MINECRAFT_RCON_PASSWORD') or os.getenv('RCON_PASSWORD')
    # 마인크래프트 명령어 임베드 푸터에 표시할 서버 이름
    MINECRAFT_SERVER_DISPLAY_NAME = os.getenv('MINECRAFT_SERVER_DISPLAY_NAME', '종겜동 마인크래프트 서버')
    # 서버 전체 플레이어 명단 (봇 컨테이너에 읽기 전용으로 마운트)
    MINECRAFT_USERCACHE_PATH = os.getenv('MINECRAFT_USERCACHE_PATH', '/minecraft/usercache.json')
    SUNLIT_CONTAINER_NAME = os.getenv('SUNLIT_CONTAINER_NAME', 'sunlit-valley-server')
    
    # Palworld server settings (docker-compose 서비스 이름 'palworld-server' 사용)
    PALWORLD_API_BASE_URL = os.getenv('PALWORLD_API_BASE_URL', 'http://palworld-server:8212/v1/api')
    PALWORLD_API_USERNAME = os.getenv('PALWORLD_API_USERNAME', 'admin')
    PALWORLD_API_PASSWORD = os.getenv('PALWORLD_ADMIN_PASSWORD') or os.getenv('PALWORLD_API_PASSWORD')
    PALWORLD_RCON_HOST = os.getenv('PALWORLD_RCON_HOST', 'palworld-server')
    PALWORLD_RCON_PORT = int(os.getenv('PALWORLD_RCON_PORT', '25575'))
    PALWORLD_RCON_PASSWORD = os.getenv('PALWORLD_ADMIN_PASSWORD') or os.getenv('RCON_PASSWORD')
    PALWORLD_SERVER_DISPLAY_NAME = os.getenv('PALWORLD_SERVER_DISPLAY_NAME', '종겜동 팰월드 서버')
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN is required in .env file")
        
        if cls.DISCORD_TOKEN == "YOUR_BOT_TOKEN_HERE":
            raise ValueError("Please set a valid DISCORD_TOKEN in .env file")
    
    @classmethod
    def get_intents(cls):
        """Get Discord intents for the bot"""
        import discord
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        return intents
