import asyncio
import logging

import discord
from discord import app_commands
import docker
from commands.base import BaseCommand
from bot.config import Config
from utils.minecraft import get_minecraft_rcon


logger = logging.getLogger(__name__)
_restart_lock = asyncio.Lock()


class MinecraftRestartCommand(BaseCommand):
    """관리자가 Sunlit Valley를 저장 후 재시작하는 명령어."""

    @property
    def name(self) -> str:
        return "마크_재시작"

    @property
    def description(self) -> str:
        return "[Admin] Sunlit Valley 월드를 저장한 뒤 서버를 재시작합니다."

    @property
    def required_permissions(self) -> list:
        return ["administrator"]

    async def execute(self, interaction: discord.Interaction):
        # 재시작과 graceful shutdown은 오래 걸릴 수 있으므로 Discord 응답을 먼저 연기합니다.
        await interaction.response.defer(ephemeral=True, thinking=True)

        if _restart_lock.locked():
            await interaction.followup.send(
                "이미 Sunlit Valley 재시작이 진행 중입니다.", ephemeral=True
            )
            return

        rcon = get_minecraft_rcon()
        if not rcon:
            await interaction.followup.send(
                "마인크래프트 RCON 설정이 완료되지 않았습니다.", ephemeral=True
            )
            return

        async with _restart_lock:
            # 접속자에게 먼저 안내하고, 컨테이너 종료 전에 월드 저장을 요청합니다.
            await rcon.send_command(
                "say [Server] An administrator requested a restart. Saving world and shutting down now."
            )
            save_result = await rcon.send_command("save-all flush")
            if save_result is None:
                logger.warning("Sunlit Valley RCON save failed; continuing with graceful restart")

            try:
                await asyncio.to_thread(self._restart_container)
            except docker.errors.DockerException as error:
                logger.exception("Failed to restart Sunlit Valley container")
                await interaction.followup.send(
                    f"Sunlit Valley 재시작에 실패했습니다: {error}", ephemeral=True
                )
                return

        await interaction.followup.send(
            "Sunlit Valley 월드 저장을 요청했고 서버 재시작을 완료했습니다.", ephemeral=True
        )

    @staticmethod
    def _restart_container():
        client = docker.from_env()
        try:
            container = client.containers.get(Config.SUNLIT_CONTAINER_NAME)
            # 기존 운영 스크립트와 같은 120초 종료 유예를 적용합니다.
            container.restart(timeout=120)
        finally:
            client.close()


def setup_command(bot):
    restart_cmd = MinecraftRestartCommand(bot)

    @app_commands.command(name=restart_cmd.name, description=restart_cmd.description)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 300.0)
    async def minecraft_restart(interaction: discord.Interaction):
        await restart_cmd.run(interaction)

    return minecraft_restart
