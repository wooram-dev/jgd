import discord
from typing import Optional, Union
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def find_channel(guild: discord.Guild, channel_identifier: Union[str, int]) -> Optional[discord.TextChannel]:
    """
    Find a channel by name, mention, or ID
    
    Args:
        guild: Discord guild to search in
        channel_identifier: Channel name, mention (#channel), or ID
    
    Returns:
        TextChannel if found, None otherwise
    """
    # If it's a channel mention, extract the ID
    if isinstance(channel_identifier, str):
        if channel_identifier.startswith('<#') and channel_identifier.endswith('>'):
            try:
                channel_id = int(channel_identifier[2:-1])
                return guild.get_channel(channel_id)
            except ValueError:
                pass
        
        # Try to find by name
        for channel in guild.text_channels:
            if channel.name.lower() == channel_identifier.lower():
                return channel
            if channel.name.lower() == channel_identifier.lower().replace('#', ''):
                return channel
    
    # Try to find by ID
    try:
        channel_id = int(channel_identifier)
        return guild.get_channel(channel_id)
    except (ValueError, TypeError):
        pass
    
    return None

def has_permission(member: discord.Member, permission: str) -> bool:
    """
    Check if a member has a specific permission
    
    Args:
        member: Discord member to check
        permission: Permission name (e.g., 'manage_messages', 'administrator')
    
    Returns:
        True if member has permission, False otherwise
    """
    if member.guild_permissions.administrator:
        return True
    
    return getattr(member.guild_permissions, permission, False)

def format_error_message(error: str) -> discord.Embed:
    """
    Create a formatted error embed
    
    Args:
        error: Error message
    
    Returns:
        Discord embed with error formatting
    """
    embed = discord.Embed(
        title="❌ 오류",
        description=error,
        color=discord.Color.red()
    )
    return embed

def format_success_message(message: str) -> discord.Embed:
    """
    Create a formatted success embed
    
    Args:
        message: Success message
    
    Returns:
        Discord embed with success formatting
    """
    embed = discord.Embed(
        title="✅ 성공",
        description=message,
        color=discord.Color.green()
    )
    return embed

def log_command_usage(user: discord.User, command: str, guild: Optional[discord.Guild] = None):
    """
    Log command usage for monitoring
    
    Args:
        user: User who executed the command
        command: Command name
        guild: Guild where command was executed (optional)
    """
    guild_name = guild.name if guild else "DM"
    logger.info(f"Command '{command}' used by {user} ({user.id}) in {guild_name}")