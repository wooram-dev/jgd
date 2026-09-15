import discord
from discord import app_commands
from commands.base import BaseCommand
from utils.helpers import format_success_message

class PingCommand(BaseCommand):
    """Simple ping command to test bot responsiveness"""
    
    @property
    def name(self) -> str:
        return "핑"
    
    @property
    def description(self) -> str:
        return "봇의 응답 시간을 확인합니다"
    
    @property
    def required_permissions(self) -> list:
        return []  # No special permissions required
    
    async def execute(self, interaction: discord.Interaction):
        """
        Execute the ping command
        
        Args:
            interaction: Discord interaction
        """
        # Calculate bot latency
        latency = round(self.bot.latency * 1000)
        
        # Create success embed with ping information
        embed = format_success_message(f"🏓 Pong! {latency}ms")
        embed.add_field(
            name="📊 상태 정보",
            value=f"• 지연시간: {latency}ms\n• 연결된 서버: {len(self.bot.guilds)}개",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

def setup_command(bot):
    """Setup function to register the command"""
    ping_cmd = PingCommand(bot)
    
    @app_commands.command(name=ping_cmd.name, description=ping_cmd.description)
    async def ping(interaction: discord.Interaction):
        await ping_cmd.run(interaction)
    
    return ping