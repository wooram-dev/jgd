import asyncio

import discord
from discord import app_commands

from bot.config import Config
from commands.base import BaseCommand
from utils.minecraft import get_minecraft_rcon, load_known_minecraft_players


class MinecraftWealthRankingCommand(BaseCommand):
    """Sunlit Valley 전체 플레이어의 Numismatics 은행 잔액 순위."""

    # Minecraft RCON server responses become unreliable with parallel connections.
    _MAX_CONCURRENT_QUERIES = 1

    @property
    def name(self) -> str:
        return "마크_재산순위"

    @property
    def description(self) -> str:
        return "Sunlit Valley 서버 전체 플레이어의 은행 잔액 순위를 조회합니다"

    @property
    def required_permissions(self) -> list:
        return []

    async def execute(self, interaction: discord.Interaction):
        rcon = get_minecraft_rcon()
        if not rcon:
            await self.handle_error(
                interaction,
                "마인크래프트 서버 설정이 완료되지 않았습니다. 관리자에게 문의하세요.",
            )
            return

        await interaction.response.defer()

        try:
            players = load_known_minecraft_players(Config.MINECRAFT_USERCACHE_PATH)
        except (OSError, ValueError) as e:
            await self.handle_error(
                interaction,
                f"서버 전체 플레이어 명단을 읽을 수 없습니다: {e}",
            )
            return

        if not players:
            await self.handle_error(interaction, "조회할 마인크래프트 플레이어가 없습니다.")
            return

        semaphore = asyncio.Semaphore(self._MAX_CONCURRENT_QUERIES)

        async def get_balance(player: str):
            async with semaphore:
                return player, await rcon.get_numismatics_balance(player)

        results = await asyncio.gather(*(get_balance(player) for player in players))
        ranked = sorted(
            ((player, balance) for player, balance in results if balance is not None),
            key=lambda item: (-item[1], item[0].casefold()),
        )

        if not ranked:
            await self.handle_error(
                interaction,
                "Numismatics 은행 잔액을 가져오지 못했습니다. 서버 RCON 상태를 확인해 주세요.",
            )
            return

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines = []
        for rank, (player, balance) in enumerate(ranked, start=1):
            prefix = medals.get(rank, f"**{rank}.**")
            safe_player = discord.utils.escape_markdown(player)
            lines.append(f"{prefix} **{safe_player}** — `{balance:,} Spurs`")

        embed = discord.Embed(
            title="🪙 Sunlit Valley 재산 순위",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        embed.add_field(name="조회 인원", value=f"{len(ranked)}명", inline=True)

        failed_count = len(players) - len(ranked)
        if failed_count:
            embed.add_field(name="조회 실패", value=f"{failed_count}명", inline=True)

        embed.add_field(
            name="집계 기준",
            value="Create: Numismatics 은행 잔액 (Spur)",
            inline=False,
        )
        server_label = (Config.MINECRAFT_SERVER_DISPLAY_NAME or "").strip() or "마인크래프트 서버"
        embed.set_footer(text=server_label)

        await interaction.followup.send(embed=embed)


def setup_command(bot):
    ranking_cmd = MinecraftWealthRankingCommand(bot)

    @app_commands.command(name=ranking_cmd.name, description=ranking_cmd.description)
    async def minecraft_wealth_ranking(interaction: discord.Interaction):
        await ranking_cmd.run(interaction)

    return minecraft_wealth_ranking
