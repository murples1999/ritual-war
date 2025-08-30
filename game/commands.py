"""Discord slash commands for Ritual War."""

import discord
from discord.ext import commands
from discord import app_commands
from .storage import GameStorage
from .logic import GameLogic
from .view import GameView
from .notifications import NotificationManager


class RitualWarCommands(commands.Cog):
    """Cog containing all Ritual War slash commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = GameStorage()
        self.notifications = NotificationManager(bot)
    
    async def cog_load(self):
        """Initialize the database when the cog loads."""
        await self.storage.initialize()
    
    def _get_guild_logic(self, guild_id: str) -> GameLogic:
        """Get a GameLogic instance for the specified guild."""
        return GameLogic(self.storage, guild_id)
    
    def _get_guild_view(self, guild_id: str) -> GameView:
        """Get a GameView instance for the specified guild."""
        logic = self._get_guild_logic(guild_id)
        return GameView(self.storage, logic, guild_id)
    
    @app_commands.command(name="join", description="Join the Ritual War")
    async def join(self, interaction: discord.Interaction):
        """Join the game."""
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        logic = self._get_guild_logic(guild_id)
        view = self._get_guild_view(guild_id)
        
        # Migrate legacy data if needed for this guild
        await self.storage.migrate_legacy_data(guild_id)
        
        result = await logic.join_game(str(interaction.user.id))
        
        if result.success:
            await interaction.response.send_message(result.message, ephemeral=True)
            if result.public_message:
                await self.notifications.send_public_message(interaction, content=result.public_message)
        else:
            embed = view.format_error(result.message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="leave", description="Leave the Ritual War")
    async def leave(self, interaction: discord.Interaction):
        """Leave the game."""
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        logic = self._get_guild_logic(guild_id)
        view = self._get_guild_view(guild_id)
        
        result = await logic.leave_game(str(interaction.user.id))
        
        if result.success:
            await interaction.response.send_message(result.message, ephemeral=True)
            if result.public_message:
                await self.notifications.send_public_message(interaction, content=result.public_message)
        else:
            embed = view.format_error(result.message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="hex", description="Cast Hex on a target")
    @app_commands.describe(target="The player to hex")
    async def hex(self, interaction: discord.Interaction, target: discord.Member):
        """Cast Hex on a target."""
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        logic = self._get_guild_logic(guild_id)
        view = self._get_guild_view(guild_id)
        
        result = await logic.hex_target(str(interaction.user.id), str(target.id))
        
        if result.success:
            await interaction.response.send_message(result.message, ephemeral=True)
            if result.public_message:
                await self.notifications.send_public_message(interaction, content=result.public_message)
                
                # If someone won, trigger XP reward
                if result.winner_id:
                    winner_name = target.display_name if result.winner_id == str(target.id) else "Unknown"
                    await self.notifications.send_victory_announcement(interaction, result.winner_id, winner_name)
        else:
            embed = view.format_error(result.message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="shield", description="Cast Shield to protect yourself")
    async def shield(self, interaction: discord.Interaction):
        """Cast Shield on self."""
        # Defer response immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        logic = self._get_guild_logic(guild_id)
        view = self._get_guild_view(guild_id)
        
        try:
            result = await logic.shield_self(str(interaction.user.id))
            
            if result.success:
                # Send the private response first
                await interaction.followup.send(result.message, ephemeral=True)
                
                # Send public message separately, with error handling
                if result.public_message:
                    try:
                        await self.notifications.send_public_message(interaction, content=result.public_message)
                    except Exception as pub_e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Failed to send public shield message for user {interaction.user.id}: {pub_e}")
            else:
                embed = view.format_error(result.message)
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except discord.errors.NotFound:
            # Interaction expired/invalid - shield was likely still applied, just log it
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Shield command interaction expired for user {interaction.user.id}, but shield may have been applied")
            
        except discord.errors.HTTPException as http_e:
            # Handle HTTP exceptions (like already acknowledged)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Shield command HTTP error for user {interaction.user.id}: {http_e}")
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Shield command error for user {interaction.user.id}: {e}")
            
            try:
                error_embed = discord.Embed(
                    title="❌ Shield Command Error",
                    description="An error occurred while casting Shield. Please try again.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            except:
                # If we can't even send the error message, just log it
                logger.error(f"Could not send error message to user {interaction.user.id}")

    @app_commands.command(name="mend", description="Cast Mend to heal a target")
    @app_commands.describe(target="The player to mend")
    async def mend(self, interaction: discord.Interaction, target: discord.Member):
        """Cast Mend on a target."""
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        logic = self._get_guild_logic(guild_id)
        view = self._get_guild_view(guild_id)
        
        result = await logic.mend_target(str(interaction.user.id), str(target.id))
        
        if result.success:
            await interaction.response.send_message(result.message, ephemeral=True)
            if result.public_message:
                await self.notifications.send_public_message(interaction, content=result.public_message)
        else:
            embed = view.format_error(result.message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="inspect", description="Inspect a player's status")
    @app_commands.describe(player="The player to inspect (leave empty for self)")
    async def inspect(self, interaction: discord.Interaction, player: discord.Member = None):
        """Inspect a player's status."""
        # Defer response immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        view = self._get_guild_view(guild_id)
        
        try:
            target_id = str(player.id) if player else str(interaction.user.id)
            
            embed = await view.format_inspect(
                str(interaction.user.id), 
                target_id, 
                interaction.guild
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except discord.errors.NotFound:
            # Interaction expired/invalid - just log it
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Inspect command interaction expired for user {interaction.user.id}")
            
        except discord.errors.HTTPException as http_e:
            # Handle HTTP exceptions (like already acknowledged)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Inspect command HTTP error for user {interaction.user.id}: {http_e}")
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Inspect command error for user {interaction.user.id}: {e}")
            
            try:
                error_embed = discord.Embed(
                    title="❌ Inspect Command Error",
                    description="An error occurred while inspecting. Please try again.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            except:
                # If we can't even send the error message, just log it
                logger.error(f"Could not send error message to user {interaction.user.id}")

    
    @app_commands.command(name="leaderboard", description="View the current game state")
    async def leaderboard(self, interaction: discord.Interaction):
        """Display the leaderboard."""
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        view = self._get_guild_view(guild_id)
        
        embed = await view.format_leaderboard(interaction.guild)
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="claimhex", description="Publicly claim you hexed a player")
    @app_commands.describe(target="The player you claim to have hexed")
    async def claimhex(self, interaction: discord.Interaction, target: discord.Member):
        """Claim to have hexed a player."""
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        logic = self._get_guild_logic(guild_id)
        view = self._get_guild_view(guild_id)
        
        result = await logic.claim_signature(str(interaction.user.id), str(target.id), "hex")
        
        if result.success:
            await interaction.response.send_message(result.message, ephemeral=True)
            if result.public_message:
                await self.notifications.send_public_message(interaction, content=result.public_message)
        else:
            embed = view.format_error(result.message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="claimmend", description="Publicly claim you mended a player")
    @app_commands.describe(target="The player you claim to have mended")
    async def claimmend(self, interaction: discord.Interaction, target: discord.Member):
        """Claim to have mended a player."""
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        logic = self._get_guild_logic(guild_id)
        view = self._get_guild_view(guild_id)
        
        result = await logic.claim_signature(str(interaction.user.id), str(target.id), "mend")
        
        if result.success:
            await interaction.response.send_message(result.message, ephemeral=True)
            if result.public_message:
                await self.notifications.send_public_message(interaction, content=result.public_message)
        else:
            embed = view.format_error(result.message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="unclaim", description="Remove a public claim")
    @app_commands.describe(
        target="The target to remove your claim from",
        action="Which claim to remove"
    )
    async def unclaim(
        self, 
        interaction: discord.Interaction, 
        target: discord.Member,
        action: str
    ):
        """Remove a public claim."""
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        logic = self._get_guild_logic(guild_id)
        view = self._get_guild_view(guild_id)
        
        result = await logic.unclaim_signature(
            str(interaction.user.id), 
            str(target.id), 
            action
        )
        
        if result.success:
            embed = view.format_success(result.message)
        else:
            embed = view.format_error(result.message)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @unclaim.autocomplete('action')
    async def unclaim_action_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Provide choices for unclaim action."""
        return [
            app_commands.Choice(name='Hex', value='hex'),
            app_commands.Choice(name='Mend', value='mend'),
        ]
    
    @app_commands.command(name="admin_setchannel", description="[ADMIN] Set the channel for public game messages")
    @app_commands.describe(channel="The channel where public game messages should be sent")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the channel for public game messages."""
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only server administrators can set the game channel.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        
        # Check if bot can send messages in the specified channel
        if not channel.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message(f"❌ I don't have permission to send messages in {channel.mention}.", ephemeral=True)
            return
        
        # Store the channel preference in the database
        await self.storage.set_state(f"public_channel", str(channel.id), guild_id)
        
        embed = discord.Embed(
            title="✅ Channel Set Successfully",
            description=f"Public game messages will now be sent to {channel.mention}",
            color=0x00ff00
        )
        embed.add_field(
            name="Test Message",
            value="Here's a test message in your configured channel!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Send a test message to the configured channel
        try:
            test_embed = discord.Embed(
                title="🎭 Ritual War Channel Configured",
                description="This channel has been set for public game messages!",
                color=0x800080
            )
            await channel.send(embed=test_embed)
        except Exception as e:
            await interaction.followup.send(f"⚠️ Channel set but failed to send test message: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(RitualWarCommands(bot))