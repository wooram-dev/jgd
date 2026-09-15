import discord
from discord import app_commands

from bot.config import Config
from commands.base import BaseCommand
from utils.palworld import get_palworld_api


class PalworldLevelsCommand(BaseCommand):
    """팰월드 접속 플레이어 레벨 랭킹 명령어."""

    @property
    def name(self) -> str:
        return "팰월드_레벨랭킹"

    @property
    def description(self) -> str:
        return "현재 접속 중인 팰월드 플레이어의 레벨 랭킹을 조회합니다"

    @property
    def required_permissions(self) -> list:
        return []

    async def execute(self, interaction: discord.Interaction):
        api = get_palworld_api()
        if not api:
            await self.handle_error(
                interaction,
                "팰월드 서버 설정이 완료되지 않았습니다. 관리자에게 문의하세요.",
            )
            return

        try:
            players = await api.get_player_details()

            embed = discord.Embed(
                title="팰월드 접속자 레벨 랭킹",
                color=discord.Color.gold(),
            )

            if not players:
                embed.description = "현재 서버에 접속한 플레이어가 없습니다."
            else:
                ranked = sorted(
                    players,
                    key=lambda player: (
                        -(player.level if player.level is not None else -1),
                        player.name.casefold(),
                    ),
                )

                lines = []
                for index, player in enumerate(ranked, start=1):
                    level = f"Lv. {player.level}" if player.level is not None else "Lv. ?"
                    extras = []
                    if player.ping is not None:
                        extras.append(f"핑 {player.ping:.0f}ms")
                    if player.building_count is not None:
                        extras.append(f"건축물 {player.building_count}개")

                    suffix = f" · {' · '.join(extras)}" if extras else ""
                    lines.append(f"**{index}. {player.name}** - {level}{suffix}")

                ranking_text = "\n".join(lines)
                if len(ranking_text) > 4096:
                    ranking_text = ranking_text[:4093] + "..."

                embed.description = ranking_text
                embed.add_field(name="접속 인원", value=f"{len(players)}명", inline=True)

            server_label = (Config.PALWORLD_SERVER_DISPLAY_NAME or "").strip() or "팰월드 서버"
            embed.set_footer(text=server_label)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await self.handle_error(
                interaction,
                f"레벨 랭킹을 가져오는 중 오류가 발생했습니다: {str(e)}",
            )


def setup_command(bot):
    levels_cmd = PalworldLevelsCommand(bot)

    @app_commands.command(name=levels_cmd.name, description=levels_cmd.description)
    async def palworld_levels(interaction: discord.Interaction):
        await levels_cmd.run(interaction)

    return palworld_levels
