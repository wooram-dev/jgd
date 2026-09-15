import discord
from discord import app_commands
from commands.base import BaseCommand
from utils.helpers import format_success_message, format_error_message
from bot.config import Config
from utils.palworld import get_palworld_api

class PlayersCommand(BaseCommand):
    """팰월드 서버 플레이어 조회 명령어"""
    
    @property
    def name(self) -> str:
        return "팰월드_플레이어"
    
    @property
    def description(self) -> str:
        return "팰월드 서버에 접속한 플레이어 수와 목록을 조회합니다"
    
    @property
    def required_permissions(self) -> list:
        return []  # 모든 사용자가 사용 가능
    
    async def execute(self, interaction: discord.Interaction):
        """
        플레이어 조회 명령어 실행
        
        Args:
            interaction: Discord interaction
        """
        # REST API 클라이언트 가져오기
        api = get_palworld_api()
        
        if not api:
            await self.handle_error(
                interaction,
                "팰월드 서버 설정이 완료되지 않았습니다. 관리자에게 문의하세요."
            )
            return
        
        try:
            # 플레이어 정보 조회
            player_count, players = await api.get_players()
            
            # 임베드 생성
            embed = discord.Embed(
                title="🦊 팰월드 서버 플레이어 정보",
                color=discord.Color.blue()
            )
            
            if player_count == 0:
                embed.description = "현재 서버에 접속한 플레이어가 없습니다."
                embed.add_field(
                    name="접속 인원",
                    value="0명",
                    inline=True
                )
            else:
                embed.description = f"현재 **{player_count}명**의 플레이어가 팰월드 여행 중입니다!"
                embed.add_field(
                    name="접속 인원",
                    value=f"{player_count}명",
                    inline=True
                )
                
                # 플레이어 목록 추가
                if players:
                    players_text = "\n".join([f"• {player}" for player in players])
                    if len(players_text) > 1024:
                        players_text = players_text[:1021] + "..."
                    
                    embed.add_field(
                        name="접속 중인 플레이어",
                        value=players_text,
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="참고",
                        value="플레이어 숫자는 확인되었으나 목록을 가져오지 못했습니다.",
                        inline=False
                    )
            
            # 서버 정보 추가
            server_label = (Config.PALWORLD_SERVER_DISPLAY_NAME or "").strip() or "팰월드 서버"
            embed.set_footer(text=server_label)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await self.handle_error(
                interaction,
                f"서버 정보를 가져오는 중 오류가 발생했습니다: {str(e)}"
            )

def setup_command(bot):
    """Setup function to register the command"""
    players_cmd = PlayersCommand(bot)
    
    @app_commands.command(name=players_cmd.name, description=players_cmd.description)
    async def players(interaction: discord.Interaction):
        await players_cmd.run(interaction)
    
    return players
