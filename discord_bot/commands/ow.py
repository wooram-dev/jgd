import discord
from discord import app_commands
from commands.base import BaseCommand
from utils.ow_api import OverwatchAPI
from utils.helpers import format_error_message
import logging

logger = logging.getLogger(__name__)

class OverwatchCommand(BaseCommand):
    """Overwatch 2 stats search command"""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.ow_api = OverwatchAPI()
    
    @property
    def name(self) -> str:
        return "전적_옵치"
    
    @property
    def description(self) -> str:
        return "오버워치 2 전적을 조회합니다. (예: 닉네임#1234)"
    
    async def execute(self, interaction: discord.Interaction, player_name: str):
        player_name = player_name.strip()
        logger.info(f"Overwatch stats requested for player: '{player_name}'")
        
        await interaction.response.defer()
            
        try:
            # 1. Format player_id
            player_id = self.ow_api.format_player_id(player_name)
            
            # 2. Fetch Player Summary
            summary = await self.ow_api.get_player_summary(player_id)
            
            if not summary:
                # Try finding player if not direct battle tag
                search_results = await self.ow_api.search_players(player_name)
                if search_results and search_results.get('results'):
                    # Pick the first exact match if possible, otherwise first result
                    player_id = search_results['results'][0]['player_id']
                    summary = await self.ow_api.get_player_summary(player_id)
                
            if not summary:
                escaped_name = discord.utils.escape_markdown(player_name)
                await interaction.followup.send(embed=format_error_message(f"'{escaped_name}' 플레이어를 찾을 수 없거나 프로필이 비공개입니다."))
                return

            # 3. Create Embed
            username = summary.get('username', 'Unknown')
            avatar = summary.get('avatar')
            title = summary.get('title', '플레이어')
            
            # Handle endorsement - could be a dict or an int
            endorsement_data = summary.get('endorsement')
            if isinstance(endorsement_data, dict):
                endorsement_level = endorsement_data.get('level', 1)
            elif isinstance(endorsement_data, int):
                endorsement_level = endorsement_data
            else:
                endorsement_level = 1
                
            embed = discord.Embed(
                title=f"🛡️ {username} 전적 프로필",
                description=f"**{title}** | 추천 레벨: **{endorsement_level}**",
                color=discord.Color.blue()
            )
            
            if avatar:
                embed.set_thumbnail(url=avatar)
                
            # Competitive Ranks
            ranks = summary.get('competitive')
            if isinstance(ranks, dict):
                rank_text = ""
                # Handle different role ranks if available
                pc_ranks = ranks.get('pc')
                if isinstance(pc_ranks, dict):
                    for role, data in pc_ranks.items():
                        if isinstance(data, dict):
                            tier = data.get('tier', 'Unknown')
                            division = data.get('division', '')
                            rank_text += f"- {role.capitalize()}: **{tier} {division}**\n"
                
                if not rank_text:
                    rank_text = "배치 전 또는 정보 없음"
                
                embed.add_field(name="🏆 경쟁전 등급 (PC)", value=rank_text, inline=False)
            else:
                embed.add_field(name="🏆 경쟁전 등급", value="정보 없음", inline=False)

            # Quick Summary Stats (if available in summary)
            # Some summaries have 'privacy' field
            privacy = summary.get('privacy', 'public')
            if privacy != 'public':
                embed.set_footer(text="⚠️ 프로필이 비공개 상태입니다. 상세 정보를 불러올 수 없습니다.")
            else:
                embed.set_footer(text="OverFast API 기반 리얼타임 데이터 (Overwatch 2)")

            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in ow command: {e}")
            await interaction.followup.send(embed=format_error_message(f"오류가 발생했습니다: {str(e)}"))

def setup_command(bot):
    """Setup function to register the command"""
    ow_cmd = OverwatchCommand(bot)
    
    @app_commands.command(name=ow_cmd.name, description=ow_cmd.description)
    @app_commands.describe(player_name="오버워치 닉네임 (예: 닉네임#1234)")
    async def ow(interaction: discord.Interaction, player_name: str):
        await ow_cmd.run(interaction, player_name=player_name)
    
    return ow
