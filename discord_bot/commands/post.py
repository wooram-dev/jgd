import discord
from discord import app_commands
from commands.base import BaseCommand
from utils.helpers import find_channel, format_success_message, format_error_message
import re

class PostCommand(BaseCommand):
    """Command to send rich messages (Markdown, Embeds, Images) to specific channels"""
    
    @property
    def name(self) -> str:
        return "관리자_포스트"
    
    @property
    def description(self) -> str:
        return "[Admin] 고급 메시지(마크다운, 이미지, Embed)를 지정된 채널에 전송합니다"
    
    @property
    def required_permissions(self) -> list:
        return ["administrator"]
    
    async def execute(self, interaction: discord.Interaction, channel: str, message: str, 
                      title: str = None, image: discord.Attachment = None, 
                      color: str = None, as_embed: bool = True):
        """
        Execute the post command
        """
        # Preprocess message: replace escaped \n with actual newline
        message = message.replace('\\n', '\n')
        if title:
            title = title.replace('\\n', '\n')
            
        # Find the target channel
        target_channel = await find_channel(interaction.guild, channel)
        
        if not target_channel:
            await self.handle_error(
                interaction, 
                f"채널 '{channel}'을(를) 찾을 수 없습니다."
            )
            return

        # Check if bot has permission to send messages and embed links in target channel
        bot_member = interaction.guild.get_member(self.bot.user.id)
        permissions = target_channel.permissions_for(bot_member)
        if not permissions.send_messages:
            await self.handle_error(interaction, f"봇이 {target_channel.mention} 채널에 메시지를 보낼 권한이 없습니다.")
            return
        
        if as_embed and not permissions.embed_links:
            await self.handle_error(interaction, f"봇이 {target_channel.mention} 채널에 링크(Embed)를 포함할 권한이 없습니다.")
            return

        try:
            # Prepare file if image is provided
            file = None
            if image:
                file = await image.to_file()

            if as_embed:
                # Create Embed
                embed_color = discord.Color.blue()
                if color:
                    # Validate Hex color
                    if re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color):
                        hex_val = int(color.lstrip('#'), 16)
                        embed_color = discord.Color(hex_val)
                
                embed = discord.Embed(
                    title=title,
                    description=message,
                    color=embed_color
                )
                
                if image:
                    embed.set_image(url=f"attachment://{image.filename}")
                
                await target_channel.send(embed=embed, file=file)
            else:
                # Send as plain text with markdown
                content = f"**{title}**\n\n{message}" if title else message
                await target_channel.send(content=content, file=file)

            # Success message to the user
            success_embed = format_success_message(
                f"{target_channel.mention} 채널에 메시지를 전송했습니다."
            )
            await interaction.response.send_message(embed=success_embed, ephemeral=True)

        except Exception as e:
            await self.handle_error(interaction, f"메시지 전송 중 오류가 발생했습니다: {str(e)}")

def setup_command(bot):
    """Setup function to register the command"""
    post_cmd = PostCommand(bot)
    
    @app_commands.command(name=post_cmd.name, description=post_cmd.description)
    @app_commands.describe(
        channel="메시지를 보낼 채널 (이름, #멘션, 또는 ID)",
        message="전송할 메시지 내용 (마크다운 지원)",
        title="엔베드 제목 (선택 사항)",
        image="첨부할 이미지 파일 (선택 사항)",
        color="사이드바 색상 (예: #FF0000) (선택 사항)",
        as_embed="엔베드 형식으로 보낼지 여부 (기본값: True)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def post(interaction: discord.Interaction, 
                   channel: str, 
                   message: str, 
                   title: str = None, 
                   image: discord.Attachment = None, 
                   color: str = None, 
                   as_embed: bool = True):
        await post_cmd.run(interaction, channel=channel, message=message, 
                           title=title, image=image, color=color, as_embed=as_embed)
    
    return post
