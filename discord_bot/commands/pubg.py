import discord
from discord import app_commands
from commands.base import BaseCommand
from utils.pubg_api import PUBGAPI
from utils.helpers import format_error_message
import logging

logger = logging.getLogger(__name__)

class PUBGCommand(BaseCommand):
    """Simplified and clean PUBG stats search command"""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.pubg_api = PUBGAPI()
    
    @property
    def name(self) -> str:
        return "전적_배그"
    
    @property
    def description(self) -> str:
        return "배틀그라운드(Steam) 전적을 깔끔하게 조회합니다."
    
    async def execute(self, interaction: discord.Interaction, nickname: str):
        nickname = nickname.strip()
        logger.info(f"PUBG stats requested for nickname: '{nickname}'")
        
        await interaction.response.defer()
            
        try:
            # 1. Player & Season Check
            player = await self.pubg_api.get_player_by_nickname(nickname)
            if not player:
                escaped_nick = discord.utils.escape_markdown(nickname)
                await interaction.followup.send(embed=format_error_message(f"'{escaped_nick}' 플레이어를 찾을 수 없습니다."))
                return
            
            account_id = player['id']
            actual_nickname = player['attributes']['name']
            
            season = await self.pubg_api.get_seasons()
            if not season:
                await interaction.followup.send(embed=format_error_message("시즌 정보를 가져올 수 없습니다."))
                return
            
            season_id = season['id']
            season_name = season_id.split('-')[-1] if '-' in season_id else "Current"

            # 2. Try Fetching Ranked Squad (Default)
            raw_ranked = await self.pubg_api.get_player_ranked_stats(account_id, season_id)
            stats = None
            match_type = "경쟁전"
            mode_display = "3인칭 스쿼드"
            
            if raw_ranked:
                stats = raw_ranked.get('data', {}).get('attributes', {}).get('rankedGameModeStats', {}).get('squad')
            
            # If no ranked squad, try normal squad
            if not stats or stats.get('roundsPlayed', 0) == 0:
                raw_normal = await self.pubg_api.get_player_season_stats(account_id, season_id)
                if raw_normal:
                    stats = raw_normal.get('data', {}).get('attributes', {}).get('gameModeStats', {}).get('squad')
                    match_type = "일반"
            
            # 3. Create Simplified Embed
            escaped_actual_nickname = discord.utils.escape_markdown(actual_nickname)
            color = discord.Color.gold() if match_type == "경쟁전" else discord.Color.green()
            embed = discord.Embed(
                title=f"🔫 {escaped_actual_nickname} 전적 프로필",
                url=f"https://pubg.op.gg/user/{actual_nickname}",
                description=f"📅 시즌: **PC 세트 {season_name}** | 🕹️ **{match_type} {mode_display}**",
                color=color
            )

            if not stats or stats.get('roundsPlayed', 0) == 0:
                embed.description += "\n\n> **⚠️ 최근 전적 데이터가 없습니다.**"
                await interaction.followup.send(embed=embed)
                return

            # Stats Calculation
            rounds = stats.get('roundsPlayed', 0)
            wins = stats.get('wins', 0)
            kills = stats.get('kills', 0)
            damage = stats.get('damageDealt', 0)
            top10s = stats.get('top10s', 0)
            # Deaths for KD
            deaths = stats.get('deaths', stats.get('losses', max(1, rounds - wins)))
            deaths = max(1, deaths)
            
            kd = kills / deaths
            win_rate = (wins / rounds) * 100
            top10_rate = (top10s / rounds) * 100
            avg_dmg = damage / rounds
            
            # Display Placement/Rank
            avg_rank = stats.get('rankAvg', 0)
            if avg_rank == 0 and 'rankSum' in stats:
                avg_rank = stats['rankSum'] / rounds

            # Main Layout
            if match_type == "경쟁전":
                tier_info = stats.get('currentTier', {})
                tier = tier_info.get('tier', 'Unranked')
                sub = tier_info.get('subTier', '')
                points = stats.get('currentRankPoint', 0)
                embed.add_field(name="🏆 등급", value=f"**{tier} {sub}**\n({points} RP)", inline=True)
                
                # Tier Image URL Mapping
                tier_img_url = "https://s-pubg.op.gg/images/tier/competitive/"
                if tier == "Unranked":
                    tier_img_url += "Unranked.png"
                elif tier in ["Master", "Survivor"]:
                    tier_img_url += f"{tier}-1.png"
                else:
                    tier_img_url += f"{tier}-{sub}.png"
                
                tier_img_url += "?image=w_200&v=1"
                embed.set_thumbnail(url=tier_img_url)
            else:
                embed.add_field(name="🥇 승률", value=f"**{win_rate:.1f}%**\n({wins}승)", inline=True)

            embed.add_field(name="🔥 K/D", value=f"**{kd:.2f}**\n({kills}킬/{deaths}데스)", inline=True)
            embed.add_field(name="🎮 게임수", value=f"**{rounds}회**", inline=True)

            embed.add_field(name="🎯 평균 딜량", value=f"**{avg_dmg:.0f}**", inline=True)
            embed.add_field(name="🎖️ Top 10", value=f"**{top10_rate:.1f}%**", inline=True)
            embed.add_field(name="📍 평균 순위", value=f"**#{avg_rank:.1f}**", inline=True)

            embed.set_footer(text="PUBG API 기반 리얼타임 데이터 (Steam)")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in pubg command: {e}")
            await interaction.followup.send(embed=format_error_message(f"오류가 발생했습니다: {str(e)}"))

def setup_command(bot):
    """Setup function to register the command"""
    pubg_cmd = PUBGCommand(bot)
    
    @app_commands.command(name=pubg_cmd.name, description=pubg_cmd.description)
    @app_commands.describe(nickname="PUBG 닉네임 (스팀)")
    async def pubg(interaction: discord.Interaction, nickname: str):
        await pubg_cmd.run(interaction, nickname=nickname)
    
    return pubg
