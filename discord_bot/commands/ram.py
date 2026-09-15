import discord
from discord import app_commands
from commands.base import BaseCommand
import psutil

class RamCommand(BaseCommand):
    """Command to check the host machine's RAM usage"""
    
    @property
    def name(self) -> str:
        return "관리자_메모리"
    
    @property
    def description(self) -> str:
        return "[Admin] 서버의 현재 RAM 점유율을 확인합니다"
    
    @property
    def required_permissions(self) -> list:
        return ["administrator"]
    
    def format_bytes(self, size):
        """Helper to format bytes to human readable form"""
        power = 2**10
        n = 0
        power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        while size > power:
            size /= power
            n += 1
        return f"{size:.2f} {power_labels[n]}B"

    async def execute(self, interaction: discord.Interaction):
        """
        Execute the ram command
        """
        try:
            # Get virtual memory stats
            vm = psutil.virtual_memory()
            
            # htop-like used memory calculation (Linux)
            # Used = Total - Free - Buffers - Cached
            # psutil vm.used might include buffers/cache depending on version, 
            # so we calculate "Actual Used" for transparency.
            actual_used_bytes = vm.total - vm.available
            
            total = self.format_bytes(vm.total)
            used = self.format_bytes(vm.used) # psutil base used
            actual_used = self.format_bytes(actual_used_bytes) # closer to htop green bar
            available = self.format_bytes(vm.available)
            cached = self.format_bytes(getattr(vm, 'cached', 0))
            buffers = self.format_bytes(getattr(vm, 'buffers', 0))
            free = self.format_bytes(vm.free)
            
            percent = (actual_used_bytes / vm.total) * 100
            
            # Create Embed
            embed = discord.Embed(
                title="📊 서버 메모리 상태 (상세)",
                description="`htop` 수치와 유사하게 계산된 실시간 현황입니다.",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="전체 용량", value=f"**{total}**", inline=True)
            embed.add_field(name="실제 사용량 (htop 기준)", value=f"**{actual_used}**", inline=True)
            embed.add_field(name="사용 가능 (여유+캐시)", value=available, inline=True)
            
            # Progress bar representation
            bar_length = 20
            filled_length = int(bar_length * percent / 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            embed.add_field(name="실제 점유율", value=f"**{percent:.1f}%**\n`{bar}`", inline=False)
            
            details = (
                f"• **순수 여유(Free):** {free}\n"
                f"• **캐시(Cached):** {cached}\n"
                f"• **버퍼(Buffers):** {buffers}\n"
                f"*리눅스는 성능을 위해 남는 램을 캐시/버퍼로 활용합니다.*"
            )
            embed.add_field(name="🛠 상세 내역", value=details, inline=False)
            
            embed.set_footer(text=f"요청자: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await self.handle_error(interaction, f"메모리 정보를 가져오는 중 오류가 발생했습니다: {str(e)}")

def setup_command(bot):
    """Setup function to register the command"""
    ram_cmd = RamCommand(bot)
    
    @app_commands.command(name=ram_cmd.name, description=ram_cmd.description)
    @app_commands.checks.has_permissions(administrator=True)
    async def ram(interaction: discord.Interaction):
        await ram_cmd.run(interaction)
    
    return ram
