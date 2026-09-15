import io
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any

import discord
from discord import app_commands

from commands.base import BaseCommand


def _enum_name(value: Any) -> str | None:
    if value is None:
        return None
    return getattr(value, "name", str(value))


def _permission_snapshot(channel: Any, guild: Any) -> dict[str, Any]:
    everyone = channel.permissions_for(guild.default_role)
    bot_member = getattr(guild, "me", None)
    bot = channel.permissions_for(bot_member) if bot_member is not None else None

    return {
        "access": "all_members" if everyone.view_channel else "restricted",
        "everyone_can_send": bool(everyone.send_messages),
        "bot": {
            "can_view": bool(bot and bot.view_channel),
            "can_read_history": bool(bot and bot.read_message_history),
            "can_send": bool(bot and bot.send_messages),
            "can_send_in_threads": bool(bot and bot.send_messages_in_threads),
        },
    }


def _forum_tags(channel: Any, include_ids: bool) -> list[dict[str, Any]] | None:
    tags = getattr(channel, "available_tags", None)
    if tags is None:
        return None

    result = []
    for tag in tags:
        item = {
            "name": tag.name,
            "moderated": bool(tag.moderated),
            "emoji": str(tag.emoji) if tag.emoji else None,
        }
        if include_ids:
            item["discord_id"] = str(tag.id)
        result.append(item)
    return result


def _serialize_channel(channel: Any, guild: Any, include_ids: bool) -> dict[str, Any]:
    channel_type = _enum_name(channel.type)
    item: dict[str, Any] = {
        "name": channel.name,
        "type": channel_type,
        "position": channel.position,
        "access": _permission_snapshot(channel, guild),
    }

    if include_ids:
        item["discord_id"] = str(channel.id)

    if hasattr(channel, "is_nsfw"):
        item["nsfw"] = bool(channel.is_nsfw())

    tags = _forum_tags(channel, include_ids)
    if tags is not None:
        item["forum_tags"] = tags
        item["default_sort_order"] = _enum_name(
            getattr(channel, "default_sort_order", None)
        )
        item["default_layout"] = _enum_name(getattr(channel, "default_layout", None))

    if hasattr(channel, "user_limit"):
        item["user_limit"] = int(channel.user_limit)

    return item


def build_server_structure(
    guild: Any,
    *,
    include_ids: bool = False,
    exported_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a structure-only snapshot without messages, members, or secrets."""
    exported_at = exported_at or datetime.now(timezone.utc)
    groups = []
    channel_type_counts: Counter[str] = Counter()

    for category, channels in guild.by_category():
        serialized_channels = []
        for channel in channels:
            serialized = _serialize_channel(channel, guild, include_ids)
            serialized_channels.append(serialized)
            channel_type_counts[serialized["type"]] += 1

        group: dict[str, Any] = {
            "name": category.name if category else None,
            "position": category.position if category else None,
            "channels": serialized_channels,
        }
        if include_ids and category:
            group["discord_id"] = str(category.id)
        groups.append(group)

    guild_info: dict[str, Any] = {
        "name": guild.name,
        "member_count": guild.member_count,
    }
    if include_ids:
        guild_info["discord_id"] = str(guild.id)

    return {
        "schema_version": 1,
        "exported_at": exported_at.astimezone(timezone.utc).isoformat(),
        "privacy": {
            "contains_messages": False,
            "contains_member_list": False,
            "contains_secrets": False,
            "discord_ids_included": include_ids,
        },
        "guild": guild_info,
        "summary": {
            "category_count": sum(1 for category, _ in guild.by_category() if category),
            "channel_count": sum(channel_type_counts.values()),
            "channel_types": dict(sorted(channel_type_counts.items())),
        },
        "categories": groups,
    }


class ServerStructureCommand(BaseCommand):
    @property
    def name(self) -> str:
        return "서버_구조_내보내기"

    @property
    def description(self) -> str:
        return "[Admin] 메시지와 멤버 정보 없이 서버 채널 구조를 JSON으로 내보냅니다"

    @property
    def required_permissions(self) -> list:
        return ["administrator"]

    async def execute(self, interaction: discord.Interaction, include_ids: bool = False):
        if interaction.guild is None:
            await self.handle_error(interaction, "Discord 서버 안에서만 사용할 수 있습니다.")
            return

        structure = build_server_structure(interaction.guild, include_ids=include_ids)
        payload = json.dumps(structure, ensure_ascii=False, indent=2).encode("utf-8")
        file = discord.File(io.BytesIO(payload), filename="discord-server-structure.json")

        id_notice = "Discord ID를 포함했습니다." if include_ids else "Discord ID는 제외했습니다."
        await interaction.response.send_message(
            content=(
                "서버 구조를 내보냈습니다. 메시지·첨부파일·멤버 목록·토큰·웹훅은 "
                f"포함하지 않습니다. {id_notice}"
            ),
            file=file,
            ephemeral=True,
        )


def setup_command(bot):
    structure_cmd = ServerStructureCommand(bot)

    @app_commands.command(name=structure_cmd.name, description=structure_cmd.description)
    @app_commands.describe(include_ids="서버·채널·포럼 태그의 Discord ID를 포함합니다")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def server_structure(interaction: discord.Interaction, include_ids: bool = False):
        await structure_cmd.run(interaction, include_ids=include_ids)

    return server_structure
