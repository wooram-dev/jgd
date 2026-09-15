import discord
from discord import app_commands
import random
from commands.base import BaseCommand
from utils.helpers import format_success_message, format_error_message

class TeamsCommand(BaseCommand):
    """Command to split users in a voice channel into teams"""
    
    @property
    def name(self) -> str:
        return "팀나누기"
    
    @property
    def description(self) -> str:
        return "음성 채널의 인원들을 무작위로 팀을 나눕니다"
    
    @property
    def required_permissions(self) -> list:
        return []
    
    async def execute(self, interaction: discord.Interaction, count: int = 2):
        """
        Execute the teams command
        
        Args:
            interaction: Discord interaction
            count: Number of teams to split into
        """
        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await self.handle_error(interaction, "이 명령어를 사용하려면 음성 채널에 참여하고 있어야 합니다.")
            return

        voice_channel = interaction.user.voice.channel
        members = voice_channel.members
        
        # Filter out bots
        members = [m for m in members if not m.bot]
        
        if len(members) < count:
            await self.handle_error(interaction, f"인원이 부족합니다. 현재 {len(members)}명이지만 {count}개 팀으로 나누려고 합니다.")
            return

        # Shuffle members
        random.shuffle(members)
        
        # Split into teams
        teams = [[] for _ in range(count)]
        for i, member in enumerate(members):
            teams[i % count].append(member)
            
        # Create embed
        embed = format_success_message(f"🔊 **{voice_channel.name}** 채널의 인원들을 {count}개 팀으로 나누었습니다.")
        
        for i, team_members in enumerate(teams):
            member_mentions = "\n".join([f"• {m.display_name}" for m in team_members])
            embed.add_field(
                name=f"🚩 팀 {i+1} ({len(team_members)}명)",
                value=member_mentions or "비어 있음",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

def setup_command(bot):
    """Setup function to register the command"""
    teams_cmd = TeamsCommand(bot)
    
    @app_commands.command(name=teams_cmd.name, description=teams_cmd.description)
    @app_commands.describe(count="나눌 팀의 수 (기본값: 2)")
    async def teams(interaction: discord.Interaction, count: int = 2):
        if count < 2:
            await interaction.response.send_message("팀 수는 최소 2개 이상이어야 합니다.", ephemeral=True)
            return
        await teams_cmd.run(interaction, count=count)
    
    return teams
