"""Enhanced error handling and notification system for Ritual War bot."""

import logging
import traceback
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import discord
from discord.ext import commands


logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling and notification system."""
    
    def __init__(self, bot: commands.Bot, owner_id: int):
        self.bot = bot
        self.owner_id = owner_id
        self.error_counts = {}
        self.last_notification = {}
        self.notification_cooldown = 300  # 5 minutes between same error types
        
    async def notify_owner(self, title: str, description: str, error: Exception = None):
        """Send a DM notification to the bot owner."""
        try:
            owner = self.bot.get_user(self.owner_id)
            if not owner:
                owner = await self.bot.fetch_user(self.owner_id)
            
            embed = discord.Embed(
                title=f"🚨 {title}",
                description=description,
                color=0xff0000,
                timestamp=datetime.utcnow()
            )
            
            if error:
                embed.add_field(
                    name="Error Details",
                    value=f"```{str(error)[:1000]}```",
                    inline=False
                )
                
                # Add traceback if available
                tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
                if len(tb) > 1000:
                    tb = tb[-1000:]  # Last 1000 chars
                embed.add_field(
                    name="Traceback",
                    value=f"```{tb}```",
                    inline=False
                )
            
            embed.set_footer(text="Ritual War Bot Error Handler")
            
            await owner.send(embed=embed)
            logger.info(f"Sent error notification to owner: {title}")
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
    
    async def handle_interaction_error(self, interaction: discord.Interaction, error: Exception):
        """Handle slash command interaction errors."""
        error_type = type(error).__name__
        now = datetime.utcnow()
        
        # Track error frequency
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        
        # Check if we should send notification (cooldown)
        should_notify = (
            error_type not in self.last_notification or
            now - self.last_notification[error_type] > timedelta(seconds=self.notification_cooldown)
        )
        
        if should_notify:
            self.last_notification[error_type] = now
            
            command_name = interaction.command.name if interaction.command else "Unknown"
            user = f"{interaction.user.display_name} ({interaction.user.id})"
            guild = f"{interaction.guild.name} ({interaction.guild.id})" if interaction.guild else "DM"
            
            description = (
                f"**Command:** /{command_name}\n"
                f"**User:** {user}\n"
                f"**Guild:** {guild}\n"
                f"**Error Count:** {self.error_counts[error_type]} (since restart)"
            )
            
            await self.notify_owner(f"Slash Command Error: {error_type}", description, error)
        
        logger.error(f"Interaction error in {interaction.command.name if interaction.command else 'unknown'}: {error}")
        
        # Send user-friendly error message
        try:
            error_embed = discord.Embed(
                title="❌ Command Error",
                description="An error occurred while processing your command. The bot owner has been notified.",
                color=0xff0000
            )
            
            if isinstance(error, discord.errors.NotFound) and "10062" in str(error):
                error_embed.description = "⏱️ The command took too long to process. Please try again."
            elif isinstance(error, commands.CommandOnCooldown):
                error_embed.description = f"🕒 Command is on cooldown. Try again in {error.retry_after:.1f} seconds."
            elif isinstance(error, commands.MissingPermissions):
                error_embed.description = "🔒 You don't have permission to use this command."
            
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                
        except Exception as followup_error:
            logger.error(f"Failed to send error message to user: {followup_error}")
    
    async def send_startup_notification(self):
        """Send notification when bot starts successfully."""
        try:
            owner = self.bot.get_user(self.owner_id) or await self.bot.fetch_user(self.owner_id)
            
            embed = discord.Embed(
                title="✅ Ritual War Bot Started",
                description=f"Bot is online and ready in {len(self.bot.guilds)} guild(s)",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            
            await owner.send(embed=embed)
            logger.info("Sent startup notification to owner")
            
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
