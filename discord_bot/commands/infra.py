import discord
import httpx
from discord import app_commands
from commands.base import BaseCommand


class InfraCommand(BaseCommand):
    """Command to trigger the infra monitoring and self-healing agent"""

    @property
    def name(self) -> str:
        return "인프라"

    @property
    def description(self) -> str:
        return "[Admin] 서버 상태 점검 및 장애 컨테이너 복구를 실시간 트리거합니다."

    @property
    def required_permissions(self) -> list:
        return ["administrator"]

    async def execute(self, interaction: discord.Interaction, additional_prompt: str = None):
        """
        Execute the infra command
        """
        # 1. 디스코드 3초 제한 회피를 위한 응답 연기(defer)
        await interaction.response.defer()

        # 2. infra-agent API 호출 (jgd_default 도커 네트워크 상의 호스트네임 사용)
        url = "http://infra-agent:8002/run"
        payload = {"additional_prompt": additional_prompt or ""}

        try:
            async with httpx.AsyncClient() as client:
                # 에이전트 구동 시간이 걸릴 수 있으므로 넉넉히 60초 타임아웃 설정
                response = await client.post(url, json=payload, timeout=60.0)

            if response.status_code == 200:
                res_data = response.json()
                if res_data.get("status") == "success":
                    report = res_data.get("final_report", "")

                    # 3. 디스코드 글자 제한(2000자) 대응을 위한 분할 전송 로직
                    if len(report) <= 2000:
                        await interaction.followup.send(content=report)
                    else:
                        chunks = []
                        current_chunk = ""
                        for line in report.splitlines(keepends=True):
                            # 여유 있게 1900자로 컷
                            if len(current_chunk) + len(line) > 1900:
                                chunks.append(current_chunk)
                                current_chunk = line
                            else:
                                current_chunk += line
                        if current_chunk:
                            chunks.append(current_chunk)

                        for i, chunk in enumerate(chunks):
                            if i == 0:
                                await interaction.followup.send(content=chunk)
                            else:
                                await interaction.channel.send(content=chunk)
                else:
                    err_msg = res_data.get("detail", "알 수 없는 에러")
                    await interaction.followup.send(content=f"❌ 에이전트 구동 실패: {err_msg}")
            else:
                await interaction.followup.send(content=f"❌ API 호출 실패 (상태 코드: {response.status_code})")

        except Exception as e:
            await interaction.followup.send(content=f"❌ 에러 발생: {str(e)}")


def setup_command(bot):
    """Setup function to register the command"""
    infra_cmd = InfraCommand(bot)

    @app_commands.command(name=infra_cmd.name, description=infra_cmd.description)
    @app_commands.describe(추가_지시사항="로그 분석 시 로컬 LLM에게 전달할 추가적인 지시사항(예: 'n8n 위주로 점검해줘')")
    @app_commands.checks.has_permissions(administrator=True)
    async def infra(interaction: discord.Interaction, 추가_지시사항: str = None):
        await infra_cmd.run(interaction, additional_prompt=추가_지시사항)

    return infra
