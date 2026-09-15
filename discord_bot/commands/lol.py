import discord
from discord import app_commands
from commands.base import BaseCommand
from utils.riot_api import RiotAPI
from utils.helpers import format_error_message, format_success_message
from utils.lol_constants import get_queue_info
import logging

logger = logging.getLogger(__name__)

class LoLCommand(BaseCommand):
    """League of Legends match search command"""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.riot_api = RiotAPI()
    
    @property
    def name(self) -> str:
        return "전적_롤"
    
    @property
    def description(self) -> str:
        return "LoL 전적을 검색합니다 (예: 닉네임#KR1)"
    
    @property
    def required_permissions(self) -> list:
        return []
    
    async def execute(self, interaction: discord.Interaction, riot_id: str):
        """
        Execute the lol search command
        
        Args:
            interaction: Discord interaction
            riot_id: User's Riot ID (Name#Tag)
        """
        await interaction.response.defer()
        
        # Parse Riot ID
        if "#" in riot_id:
            game_name, tag_line = riot_id.split("#", 1)
        else:
            game_name = riot_id
            tag_line = "KR1" # Default tag
            
        try:
            # 1. 소환사 고유 ID 가져오기
            account = await self.riot_api.get_account_by_riot_id(game_name, tag_line)
            logger.info(f"Account found: {account}")
            if not account:
                await interaction.followup.send(embed=format_error_message(f"'{game_name}#{tag_line}' 사용자를 찾을 수 없습니다."))
                return
            else:
                puuid = account['puuid']
                game_name = account['gameName']
                tag_line = account['tagLine']

            # 2. 소환사 상세 정보 가져오기 (레벨 및 아이콘 정보용)
            summoner = await self.riot_api.get_summoner_by_puuid(puuid)
            if not summoner:
                await interaction.followup.send(embed=format_error_message("소환사 정보를 가져오는 중 오류가 발생했습니다."))
                return

            # 3. 랭크 정보 가져오기
            league_entries = await self.riot_api.get_league_entries(puuid)
            logger.info(f"League entries found: {league_entries}")
            if league_entries is None:
                await interaction.followup.send(embed=format_error_message("랭크 정보를 가져오는 중 오류가 발생했습니다."))
                return
            
            # 4. 최근 5경기 정보 가져오기
            match_ids = await self.riot_api.get_match_ids(puuid, count=5)
            
            # 5. 기타 정보 (숙련도 및 버전) 가져오기
            top_masteries = await self.riot_api.get_top_champion_masteries(puuid, count=3)
            champ_map = await self.riot_api.get_champion_map()
            latest_version = await self.riot_api.get_latest_version()
            
            # Embed 생성
            embed = discord.Embed(
                title=f"🎮 {game_name}#{tag_line} 전적 검색 결과",
                description=f"Level: {summoner['summonerLevel']}",
                color=discord.Color.blue()
            )
            
            # 썸네일 (아이콘)
            icon_id = summoner['profileIconId']
            embed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/img/profileicon/{icon_id}.png")
            
            # 랭크 정보 추가
            if not league_entries:
                embed.add_field(name="🏆 랭크", value="Unranked", inline=False)
            for entry in league_entries:
                queue_type = "솔로 랭크" if entry['queueType'] == "RANKED_SOLO_5x5" else "자유 랭크"
                tier = entry['tier']
                rank = entry['rank']
                lp = entry['leaguePoints']
                wins = entry['wins']
                losses = entry['losses']
                win_rate = (wins / (wins + losses)) * 100
                
                embed.add_field(
                    name=f"🏆 {queue_type}",
                    value=f"**{tier} {rank}** ({lp} LP)\n{wins}승 {losses}패 (승률 {win_rate:.1f}%)",
                    inline=True
                )
            
            # 챔피언 숙련도 TOP 3 추가
            if top_masteries:
                mastery_text = ""
                for mastery in top_masteries:
                    champ_name = champ_map.get(mastery['championId'], f"Unknown({mastery['championId']})")
                    lvl = mastery['championLevel']
                    pts = format(mastery.get('championPoints', 0), ',') 
                    mastery_text += f"• **{champ_name}** | Lv.{lvl} ({pts} pts)\n"
                embed.add_field(name="✨ 챔피언 숙련도 TOP 3", value=mastery_text, inline=False)

            # 최근 경기 정보 추가
            if match_ids:
                matches_summary = ""
                for m_id in match_ids:
                    match_detail = await self.riot_api.get_match_detail(m_id)
                    if match_detail:
                        # Find the participant (self)
                        participant = next((p for p in match_detail['info']['participants'] if p['puuid'] == puuid), None)
                        if participant:
                            result = "✅ 승리" if participant['win'] else "❌ 패배"
                            # 게임 모드
                            queue_id = match_detail['info']['queueId']
                            queue_info = get_queue_info(queue_id)
                            # 챔피언 이름
                            champion_name = champ_map.get(participant['championId'], participant['championName'])
                            # K/D/A
                            k = participant['kills']
                            d = participant['deaths']
                            a = participant['assists']
                            matches_summary += f"• [{queue_info}] {result} | {champion_name} ({k}/{d}/{a})\n"
                
                if matches_summary:
                    embed.add_field(name="⚔️ 최근 5경기", value=matches_summary, inline=False)
            else:
                embed.add_field(name="⚔️ 최근 5경기", value="최근 기록이 없습니다.", inline=False)
                
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in lol command: {e}")
            await interaction.followup.send(embed=format_error_message(f"오류가 발생했습니다: {str(e)}"))

def setup_command(bot):
    """Setup function to register the command"""
    lol_cmd = LoLCommand(bot)
    
    @app_commands.command(name=lol_cmd.name, description=lol_cmd.description)
    @app_commands.describe(riot_id="닉네임#태그 명칭 (예: 닉네임#KR1)")
    async def lol(interaction: discord.Interaction, riot_id: str):
        await lol_cmd.run(interaction, riot_id=riot_id)
    
    return lol
