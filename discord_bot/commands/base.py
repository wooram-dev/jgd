import discord
from discord.ext import commands
from abc import ABC, abstractmethod
from typing import Optional
from utils.helpers import log_command_usage, format_error_message

class BaseCommand(ABC):
    """Base class for all bot commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Command name"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Command description"""
        pass
    
    @property
    def required_permissions(self) -> list:
        """List of required permissions for this command"""
        return []
    
    async def check_permissions(self, interaction: discord.Interaction) -> bool:
        """
        Check if user has required permissions
        
        Args:
            interaction: Discord interaction
            
        Returns:
            True if user has permissions, False otherwise
        """
        if not self.required_permissions:
            return True
        
        member = interaction.user
        if isinstance(member, discord.Member):
            # Administrator always has permission
            if member.guild_permissions.administrator:
                return True
            
            # Check specific permissions
            for permission in self.required_permissions:
                if not getattr(member.guild_permissions, permission, False):
                    return False
        
        return True
    
    async def handle_error(self, interaction: discord.Interaction, error: str):
        """
        Handle command errors
        
        Args:
            interaction: Discord interaction
            error: Error message
        """
        embed = format_error_message(error)
        
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def log_usage(self, interaction: discord.Interaction):
        """Log command usage"""
        log_command_usage(
            user=interaction.user,
            command=self.name,
            guild=interaction.guild
        )
    
    @abstractmethod
    async def execute(self, interaction: discord.Interaction, **kwargs):
        """
        Execute the command
        
        Args:
            interaction: Discord interaction
            **kwargs: Command arguments
        """
        pass
    
    async def run(self, interaction: discord.Interaction, **kwargs):
        """
        Run the command with error handling and permission checks
        
        Args:
            interaction: Discord interaction
            **kwargs: Command arguments
        """
        try:
            # Log command usage
            await self.log_usage(interaction)
            
            # Check permissions
            if not await self.check_permissions(interaction):
                await self.handle_error(
                    interaction, 
                    f"이 명령어를 사용할 권한이 없습니다. 필요한 권한: {', '.join(self.required_permissions)}"
                )
                return
            
            # Execute command
            await self.execute(interaction, **kwargs)
            
        except Exception as e:
            await self.handle_error(interaction, f"명령어 실행 중 오류가 발생했습니다: {str(e)}")
            raise e