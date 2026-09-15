import discord
from discord import app_commands
from commands.base import BaseCommand
from utils.steam_api import SteamAPI
from utils.helpers import format_error_message, logger
import re

class SteamCommand(BaseCommand):
    """Command to find common games between multiple Steam users"""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.steam_api = SteamAPI()
    
    @property
    def name(self) -> str:
        return "스팀_비교"
    
    @property
    def description(self) -> str:
        return "여러 스팀 ID를 입력하여 공통으로 소유한 게임 목록을 찾습니다."
    
    async def execute(self, interaction: discord.Interaction, identifiers: str):
        """
        Execute the compare command
        - identifiers: space or comma separated steam IDs, URLs, or vanity names
        """
        logger.info(f"Steam compare requested for identifiers: '{identifiers}'")
        
        await interaction.response.defer()
        
        # 1. Parse identifiers
        id_list = re.split(r'[,\s]+', identifiers.strip())
        id_list = [i for i in id_list if i] # remove empty strings
        
        if len(id_list) < 2:
            await interaction.followup.send(embed=format_error_message("최소 2개 이상의 스팀 ID 또는 URL을 입력해주세요."))
            return

        if len(id_list) > 10:
            await interaction.followup.send(embed=format_error_message("최대 10개까지만 입력 가능합니다."))
            return

        try:
            # 2. Resolve all identifiers to SteamID64
            steam_ids = []
            for identifier in id_list:
                sid = await self.steam_api.get_steam_id(identifier)
                if sid:
                    steam_ids.append(sid)
                else:
                    await interaction.followup.send(embed=format_error_message(f"ID를 찾을 수 없습니다: `{identifier}`"))
                    return
            
            # 3. Fetch player summaries for names
            players = await self.steam_api.get_player_summaries(steam_ids)
            player_map = {p['steamid']: p for p in players}
            
            # Check if all IDs were resolved to valid players
            valid_names = []
            for sid in steam_ids:
                if sid in player_map:
                    valid_names.append(player_map[sid]['personaname'])
                else:
                    # If player summary fails, use the ID itself
                    valid_names.append(sid)

            # 4. Fetch owned games for each player
            user_game_sets = []
            for sid in steam_ids:
                games = await self.steam_api.get_owned_games(sid)
                if not games:
                    # Profile might be private or error occurred
                    name = player_map.get(sid, {}).get('personaname', sid)
                    await interaction.followup.send(embed=format_error_message(f"'{name}'님의 게임 목록을 가져올 수 없습니다. 프로필이 비공개이거나 게임 목록이 숨겨져 있을 수 있습니다."))
                    return
                
                # Store as a dictionary of appid -> name for later lookup
                game_dict = {g['appid']: g['name'] for g in games}
                user_game_sets.append(game_dict)

            # 5. Find intersection of appids
            common_appids = set(user_game_sets[0].keys())
            for game_dict in user_game_sets[1:]:
                common_appids &= set(game_dict.keys())

            # 6. Prepare result
            if not common_appids:
                embed = discord.Embed(
                    title="🎮 스팀 게임 교집합 결과",
                    description=f"**{', '.join(valid_names)}** 님들 사이에 공통 게임이 없습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # Sort common games by name
            all_games_map = {}
            for g_dict in user_game_sets:
                all_games_map.update(g_dict)
            
            common_games_sorted = sorted([all_games_map[appid] for appid in common_appids])
            
            # 7. Create Embed
            embed = discord.Embed(
                title="🎮 스팀 공통 게임 목록",
                description=f"비교 대상: **{', '.join(valid_names)}**\n공통 게임: **{len(common_games_sorted)}개**",
                color=discord.Color.blue()
            )
            
            # Split games into multiple fields to avoid 1024 character limit per field
            current_field_text = ""
            field_count = 0
            MAX_FIELDS = 10
            
            for i, game_name in enumerate(common_games_sorted):
                line = f"• {game_name}\n"
                
                # If current field is getting full, add it and start a new one
                if len(current_field_text) + len(line) > 1000:
                    field_count += 1
                    embed.add_field(name=f"목록 ({field_count})", value=current_field_text, inline=False)
                    current_field_text = ""
                
                # Check if we've reached max fields
                if field_count >= MAX_FIELDS:
                    remaining = len(common_games_sorted) - i
                    embed.set_footer(text=f"Steam Web API 기반 | 외 {remaining}개의 게임이 더 있으나 표시 한계를 초과했습니다.")
                    break
                
                current_field_text += line
            else:
                # Add the last field if not empty
                if current_field_text:
                    field_count += 1
                    name = "목록" if field_count == 1 else f"목록 ({field_count})"
                    embed.add_field(name=name, value=current_field_text, inline=False)
                embed.set_footer(text="Steam Web API 기반 | 모든 프로필/게임 목록은 '공개'여야 합니다.")
            
            # Optional: set thumbnail of the first player
            if players:
                embed.set_thumbnail(url=players[0]['avatarfull'])

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in steam_compare command: {e}")
            await interaction.followup.send(embed=format_error_message(f"오류가 발생했습니다: {str(e)}"))

def setup_command(bot):
    """Setup function to register the command"""
    steam_cmd = SteamCommand(bot)
    
    @app_commands.command(name=steam_cmd.name, description=steam_cmd.description)
    @app_commands.describe(identifiers="스팀 ID, 커스텀 URL 또는 프로필 URL (공백 또는 쉼표 구분)")
    async def steam_compare(interaction: discord.Interaction, identifiers: str):
        await steam_cmd.run(interaction, identifiers=identifiers)
    
    return steam_compare
