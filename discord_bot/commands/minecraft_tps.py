import discord
from discord import app_commands
from commands.base import BaseCommand
from bot.config import Config
from utils.minecraft import get_minecraft_rcon


class TpsCommand(BaseCommand):
    """마인크래프트 서버 TPS/틱 타임 조회 명령어"""

    @property
    def name(self) -> str:
        return "마크_tps"

    @property
    def description(self) -> str:
        return "마인크래프트 서버의 TPS(초당 틱)와 틱 타임(ms)을 조회합니다"

    @property
    def required_permissions(self) -> list:
        return []

    def _tps_color(self, tps: float) -> discord.Color:
        if tps >= 19.0:
            return discord.Color.green()
        if tps >= 15.0:
            return discord.Color.gold()
        return discord.Color.red()

    async def execute(self, interaction: discord.Interaction):
        rcon = get_minecraft_rcon()
        if not rcon:
            await self.handle_error(
                interaction,
                "마인크래프트 서버 설정이 완료되지 않았습니다. 관리자에게 문의하세요.",
            )
            return

        try:
            data = await rcon.get_tps()
            if not data:
                await self.handle_error(
                    interaction,
                    "서버에서 TPS 정보를 가져올 수 없습니다. 원인:\n"
                    "- 서버가 오프라인이거나 RCON 연결 실패\n"
                    "- 서버가 `spark tps`, `forge tps`, `tps` 명령어를 지원하지 않음",
                )
                return

            # 데이터가 있으면 (Spark의 경우 MSPT가 0일 수 있음)
            main = next((d for d in data if "overworld" in d["dimension"].lower() or "Server" in d["dimension"]), data[0])
            color = self._tps_color(main["tps"])

            embed = discord.Embed(
                title="⏱ 마인크래프트 서버 TPS / 틱 타임",
                color=color,
            )
            
            spark_info = " (Spark 측정)" if "Spark" in main["dimension"] else ""
            embed.description = (
                f"**TPS**(Ticks Per Second): 20이 정상입니다.{spark_info}\n"
                "**틱 타임**: 한 틱당 걸린 시간(ms). 50ms 이하면 양호합니다."
            )

            for d in data:
                tps = d["tps"]
                ms = d["tick_time_ms"]
                status = "🟢 양호" if tps >= 19 else ("🟡 보통" if tps >= 15 else "🔴 부하")
                
                if ms > 0:
                    value = f"TPS **{tps:.1f}** · 틱 타임 **{ms:.2f}** ms\n{status}"
                else:
                    value = f"TPS **{tps:.1f}**\n{status}"
                    
                embed.add_field(name=d["dimension"], value=value, inline=True)

            server_label = (Config.MINECRAFT_SERVER_DISPLAY_NAME or "").strip() or "마인크래프트 서버"
            embed.set_footer(text=server_label)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await self.handle_error(
                interaction,
                f"서버 정보를 가져오는 중 오류가 발생했습니다: {str(e)}",
            )


def setup_command(bot):
    tps_cmd = TpsCommand(bot)

    @app_commands.command(name=tps_cmd.name, description=tps_cmd.description)
    async def tps(interaction: discord.Interaction):
        await tps_cmd.run(interaction)

    return tps
