"""Admin commands for testing and game management."""

import os
import discord
from discord.ext import commands
from discord import app_commands
from .storage import GameStorage
from .logic import GameLogic
from .view import GameView
from .models import Player
from .notifications import NotificationManager


class AdminCommands(commands.Cog):
    """Admin-only commands for testing and management."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = GameStorage()
        self.notifications = NotificationManager(bot)
        
        # Get owner ID from environment or set a default for testing
        self.owner_id = int(os.getenv('BOT_OWNER_ID', '0'))
    
    def _get_guild_logic(self, guild_id: str) -> GameLogic:
        """Get a GameLogic instance for the specified guild."""
        return GameLogic(self.storage, guild_id)
    
    def _get_guild_view(self, guild_id: str) -> GameView:
        """Get a GameView instance for the specified guild."""
        logic = self._get_guild_logic(guild_id)
        return GameView(self.storage, logic, guild_id)
    
    def is_owner(self, user_id: int) -> bool:
        """Check if user is the bot owner."""
        # Check BOT_OWNER_ID from environment
        if user_id == self.owner_id:
            return True
        
        # Check if user is the Discord application owner
        try:
            if hasattr(self.bot.application, 'owner') and self.bot.application.owner:
                return user_id == self.bot.application.owner.id
        except:
            pass
        
        return False
    
    @app_commands.command(name="admin_reset_game", description="[ADMIN] Reset the entire game state")
    async def reset_game(self, interaction: discord.Interaction):
        """Reset the game state completely."""
        if not self.is_owner(interaction.user.id):
            await interaction.response.send_message("❌ This command is restricted to bot owners.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        logic = self._get_guild_logic(guild_id)
        view = self._get_guild_view(guild_id)
        
        success = await logic.reset_game()
        
        if success:
            embed = discord.Embed(
                title="🔄 Game Reset Complete",
                description="All game data has been cleared. Players can now use `/join` to start a new game!",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed)
        else:
            embed = view.format_error("Failed to reset game. Check logs for details.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    
    @app_commands.command(name="admin_force_winner", description="[ADMIN] Declare a winner and award XP")
    @app_commands.describe(winner="The player who should win")
    async def force_winner(self, interaction: discord.Interaction, winner: discord.Member):
        """Force a winner for testing XP integration."""
        if not self.is_owner(interaction.user.id):
            await interaction.response.send_message("❌ This command is restricted to bot owners.", ephemeral=True)
            return
        
        await self.notifications.send_victory_announcement(interaction, str(winner.id), winner.display_name)
        await interaction.response.send_message(f"🎉 Forced victory for {winner.mention} and triggered XP reward!", ephemeral=True)
    
    
    @app_commands.command(name="admin_advance_day", description="[ADMIN] Clear all daily action limits for testing")
    async def advance_day(self, interaction: discord.Interaction):
        """Advance to next day by clearing all daily action limits."""
        if not self.is_owner(interaction.user.id):
            await interaction.response.send_message("❌ This command is restricted to bot owners.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        view = self._get_guild_view(guild_id)
        
        try:
            # Clear all players' last_action_day to allow new actions
            players = await self.storage.get_active_players(guild_id)
            for player in players:
                player.last_action_day = None
                await self.storage.update_player(player)
            
            embed = discord.Embed(
                title="📅 Day Advanced",
                description=f"All {len(players)} players can now act again. Daily action limits have been reset.",
                color=0x0099ff
            )
            embed.set_footer(text="Use this to test multiple 'days' worth of actions quickly")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = view.format_error(f"Failed to advance day: {str(e)}")
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    """Setup function to add the admin cog to the bot."""
    await bot.add_cog(AdminCommands(bot))