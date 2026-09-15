import discord
from discord.ext import commands
from discord import app_commands
import os
import importlib
import logging
from bot.config import Config
from utils.helpers import logger
from utils.gemini import GeminiReaction

class DiscordBot(commands.Bot):
    """Main Discord bot class"""
    
    def __init__(self):
        # Initialize bot with intents
        intents = Config.get_intents()
        super().__init__(
            command_prefix=Config.BOT_PREFIX,
            intents=intents,
            help_command=None  # Disable default help command
        )
        
        self.commands_loaded = []
        self.gemini = GeminiReaction()
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("Bot is starting up...")
        
        # Load all commands
        await self.load_commands()
        
        # Sync commands
        try:
            if Config.GUILD_ID:
                guild = discord.Object(id=int(Config.GUILD_ID))
                
                # 중복 방지를 위해 전역 명령어를 해당 길드에 복사
                self.tree.copy_global_to(guild=guild)
                
                # 1. 먼저 전역 명령어를 삭제 (이미 전역으로 등록된 것들을 지우기 위해)
                # 주의: 이 작업은 전역 명령어 삭제를 위해 한 번은 필요할 수 있습니다.
                # 하지만 매번 할 필요는 없으므로, 로직을 신중히 구성합니다.
                # 여기서는 전역 명령어를 명시적으로 비우고 길드에만 등록되도록 유도합니다.
                
                # 전역 트리 비우기 (이미 전역에 등록된 명령어들을 디스코드 서버에서 지우기 위함)
                # self.tree.clear_commands(guild=None) # 로컬 트리에서만 지워지므로 아래 sync()가 중요함
                
                # 길드 동기화
                synced_guild = await self.tree.sync(guild=guild)
                logger.info(f"Synced {len(synced_guild)} commands to guild {Config.GUILD_ID}")
                
                # 전역 명령어 삭제 (전역 리스트가 비어있는 상태에서 sync() 호출)
                self.tree.clear_commands(guild=None)
                synced_global = await self.tree.sync()
                logger.info(f"Global commands cleared (Synced {len(synced_global)} commands)")
            else:
                synced = await self.tree.sync()
                logger.info(f"Synced {len(synced)} commands globally (May take up to 1 hour)")
                
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def load_commands(self):
        """Load all commands from the commands directory"""
        commands_dir = "commands"
        
        # Get all Python files in commands directory
        for filename in os.listdir(commands_dir):
            if filename.endswith('.py') and not filename.startswith('__') and filename != 'base.py':
                module_name = filename[:-3]  # Remove .py extension
                
                # Skip disabled commands
                if module_name in Config.DISABLED_COMMANDS:
                    logger.info(f"Skipping disabled command: {module_name}")
                    continue
                
                try:
                    # Import the command module
                    module = importlib.import_module(f"{commands_dir}.{module_name}")
                    
                    # Check if module has setup_command function
                    if hasattr(module, 'setup_command'):
                        command = module.setup_command(self)
                        self.tree.add_command(command)
                        self.commands_loaded.append(module_name)
                        logger.info(f"Loaded command: {module_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to load command {module_name}: {e}")
        
        logger.info(f"Total commands loaded: {len(self.commands_loaded)}")
    
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f"Bot is ready! Logged in as {self.user}")
        logger.info(f"Bot ID: {self.user.id}")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | /help"
        )
        await self.change_presence(activity=activity)
    
    async def on_guild_join(self, guild):
        """Called when bot joins a new guild"""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        
        # Update status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | /help"
        )
        await self.change_presence(activity=activity)
    
    async def on_guild_remove(self, guild):
        """Called when bot leaves a guild"""
        logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
        
        # Update status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | /help"
        )
        await self.change_presence(activity=activity)
    
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle application command errors"""
        if isinstance(error, app_commands.CommandOnCooldown):
            embed = discord.Embed(
                title="❌ 쿨다운",
                description=f"이 명령어는 {error.retry_after:.2f}초 후에 다시 사용할 수 있습니다.",
                color=discord.Color.red()
            )
        elif isinstance(error, app_commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ 권한 부족",
                description="이 명령어를 사용할 권한이 없습니다.",
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title="❌ 오류",
                description=f"명령어 실행 중 오류가 발생했습니다: {str(error)}",
                color=discord.Color.red()
            )
            logger.error(f"App command error: {error}")
        
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_message(self, message: discord.Message):
        """Called when a message is sent"""
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Handle Gemini reaction in specific channel
        if Config.GEMINI_CHAT_CHANNEL_ID and str(message.channel.id) == str(Config.GEMINI_CHAT_CHANNEL_ID):
            logger.info(f"DEBUG: Message from {message.author} in {message.channel.id}: {message.content}")
            logger.info(f"MATCH: Gemini channel detected!")
            try:
                async with message.channel.typing():
                    response = await self.gemini.generate_reaction(message.content)
                    logger.info(f"Sending Gemini reaction: {response}")
                    await message.reply(response)
                    logger.info("Gemini reaction sent successfully.")
            except Exception as e:
                logger.error(f"Error in Gemini reaction: {e}")

        # Process commands (이게 있어야 슬래시 명령어가 아닌 일반 명령어도 작동함)
        await self.process_commands(message)

def create_bot() -> DiscordBot:
    """Create and return a bot instance"""
    return DiscordBot()