"""View formatting for Ritual War displays."""

from typing import List, Dict, Any
import discord
from .models import Player, PlayerStatus
from .storage import GameStorage
from .logic import GameLogic
from .timeutils import hours_until
from .config import THRESHOLD


class GameView:
    """Handles formatting of game displays."""
    
    def __init__(self, storage: GameStorage, logic: GameLogic, guild_id: str):
        self.storage = storage
        self.logic = logic
        self.guild_id = guild_id
    
    async def format_leaderboard(self, guild: discord.Guild) -> discord.Embed:
        """Format the leaderboard display."""
        players = await self.storage.get_active_players(self.guild_id)
        
        if not players:
            embed = discord.Embed(
                title="🎭 Ritual War Leaderboard",
                description="No active players. Use `/join` to enter the game!",
                color=0x800080
            )
            return embed
        
        # Sort by doom (ascending - lower is better)
        players.sort(key=lambda p: p.doom)
        
        embed = discord.Embed(
            title="🎭 Ritual War Leaderboard",
            color=0x800080
        )
        
        description_lines = []
        
        for player in players:
            try:
                member = guild.get_member(int(player.user_id))
                display_name = member.display_name if member else f"<@{player.user_id}>"
            except:
                display_name = f"<@{player.user_id}>"
            
            # Get train statuses
            hex_train = await self.logic.get_train_status(player.user_id, "hex")
            mend_train = await self.logic.get_train_status(player.user_id, "mend")
            
            # Format doom with status indicator
            doom_display = f"{player.doom}/{THRESHOLD}"
            if player.doom >= THRESHOLD * 0.75:  # 75% threshold
                doom_display = f"💀 {doom_display}"
            elif player.doom >= THRESHOLD * 0.5:  # 50% threshold
                doom_display = f"⚠️ {doom_display}"
            
            # Format marks
            hex_display = f"{hex_train.count} Hex Mark{'s' if hex_train.count != 1 else ''}"
            if hex_train.count > 0:
                hex_display += f" ({hex_train.freshness})"
            
            mend_display = f"{mend_train.count} Mend Mark{'s' if mend_train.count != 1 else ''}"
            if mend_train.count > 0:
                mend_display += f" ({mend_train.freshness})"
            
            line = f"**{display_name}** - {doom_display} | {hex_display} | {mend_display}"
            description_lines.append(line)
        
        embed.description = "\n".join(description_lines)
        
        # Add footer with roster status
        if await self.storage.is_roster_locked(self.guild_id):
            embed.set_footer(text="🔒 Roster locked - no new players may join")
        else:
            embed.set_footer(text="✅ Open for new players - use /join to enter!")
        
        return embed
    
    async def format_inspect(self, user_id: str, target_id: str, guild: discord.Guild) -> discord.Embed:
        """Format player inspection display."""
        target = await self.storage.get_player(target_id, self.guild_id)
        if not target or not target.active:
            embed = discord.Embed(
                title="❌ Player Not Found",
                description="This player is not in the game.",
                color=0xff0000
            )
            return embed
        
        try:
            member = guild.get_member(int(target_id))
            display_name = member.display_name if member else f"<@{target_id}>"
        except:
            display_name = f"<@{target_id}>"
        
        is_self_inspect = user_id == target_id
        
        embed = discord.Embed(
            title=f"🔍 Inspecting {display_name}",
            color=0x4169E1
        )
        
        # Basic info
        doom_display = f"{target.doom}/{THRESHOLD}"
        if target.doom >= THRESHOLD * 0.75:
            doom_display = f"💀 {doom_display}"
        elif target.doom >= THRESHOLD * 0.5:
            doom_display = f"⚠️ {doom_display}"
        
        embed.add_field(name="Doom", value=doom_display, inline=True)
        
        # Veil info (only for self)
        if is_self_inspect and target.veil_until:
            veil_hours = hours_until(target.veil_until)
            if veil_hours > 0:
                embed.add_field(name="🛡️ Veil", value=f"{veil_hours:.1f}h remaining", inline=True)
        
        # Mark info
        hex_train = await self.logic.get_train_status(target_id, "hex")
        mend_train = await self.logic.get_train_status(target_id, "mend")
        
        hex_display = f"{hex_train.count} Hex Mark{'s' if hex_train.count != 1 else ''}"
        if hex_train.count > 0:
            hex_display += f" ({hex_train.freshness})"
        
        mend_display = f"{mend_train.count} Mend Mark{'s' if mend_train.count != 1 else ''}"
        if mend_train.count > 0:
            mend_display += f" ({mend_train.freshness})"
        
        embed.add_field(name="Hex Marks", value=hex_display, inline=True)
        embed.add_field(name="Mend Marks", value=mend_display, inline=True)
        
        # Lockouts (only for self)
        if is_self_inspect:
            lockouts = await self.storage.get_user_lockouts(user_id, self.guild_id)
            
            if lockouts["hex"] or lockouts["mend"]:
                lockout_lines = []
                
                if lockouts["hex"]:
                    hex_targets = []
                    for target_user_id in lockouts["hex"]:
                        try:
                            member = guild.get_member(int(target_user_id))
                            name = member.display_name if member else f"<@{target_user_id}>"
                            hex_targets.append(name)
                        except:
                            hex_targets.append(f"<@{target_user_id}>")
                    lockout_lines.append(f"**Hex blocked:** {', '.join(hex_targets)}")
                
                if lockouts["mend"]:
                    mend_targets = []
                    for target_user_id in lockouts["mend"]:
                        try:
                            member = guild.get_member(int(target_user_id))
                            name = member.display_name if member else f"<@{target_user_id}>"
                            mend_targets.append(name)
                        except:
                            mend_targets.append(f"<@{target_user_id}>")
                    lockout_lines.append(f"**Mend blocked:** {', '.join(mend_targets)}")
                
                embed.add_field(
                    name="🚫 Active Signatures (Lockouts)",
                    value="\n".join(lockout_lines),
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ No Active Lockouts",
                    value="You can target any player with Hex or Mend.",
                    inline=False
                )
        
        return embed
    
    def format_error(self, message: str) -> discord.Embed:
        """Format an error message."""
        embed = discord.Embed(
            title="❌ Error",
            description=message,
            color=0xff0000
        )
        return embed
    
    def format_success(self, message: str) -> discord.Embed:
        """Format a success message."""
        embed = discord.Embed(
            title="✅ Success",
            description=message,
            color=0x00ff00
        )