"""Daily notification scheduler for Ritual War."""

import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import List

import discord
from discord.ext import commands, tasks

from .storage import GameStorage
from .timeutils import get_timezone, today_key


logger = logging.getLogger(__name__)


class DailyScheduler:
    """Handles daily notifications to players."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = GameStorage()
        self.timezone = get_timezone()
        
        # Start the daily notification task
        self.daily_notifications.start()
    
    def cog_unload(self):
        """Clean shutdown of the scheduler."""
        self.daily_notifications.cancel()
    
    @tasks.loop(time=time(hour=8, minute=0, tzinfo=get_timezone()))  # 8 AM Pacific
    async def daily_notifications(self):
        """Send daily action reminder to all active players across all guilds."""
        try:
            logger.info("Starting daily notifications...")
            
            # Get all guilds the bot is in
            total_notifications = 0
            total_players = 0
            
            for guild in self.bot.guilds:
                guild_id = str(guild.id)
                logger.info(f"Processing notifications for guild: {guild.name} ({guild_id})")
                
                # Get active players for this guild
                players = await self.storage.get_active_players(guild_id)
                if not players:
                    logger.info(f"No active players found in guild {guild.name}")
                    continue
                
                guild_notifications = 0
                current_day = today_key()
                
                for player in players:
                    # Skip if player already acted today
                    if player.last_action_day == current_day:
                        continue
                    
                    try:
                        # Try to get Discord user
                        if player.user_id.startswith("test_user_"):
                            continue  # Skip test users
                        
                        user = self.bot.get_user(int(player.user_id))
                        if not user:
                            # Try to fetch user if not in cache
                            user = await self.bot.fetch_user(int(player.user_id))
                        
                        if user:
                            await self.send_daily_reminder(user, player.doom, guild.name)
                            guild_notifications += 1
                            total_notifications += 1
                            
                            # Small delay to avoid rate limits
                            await asyncio.sleep(0.5)
                            
                    except Exception as e:
                        logger.error(f"Failed to send daily notification to user {player.user_id} in guild {guild.name}: {str(e)}")
                        continue
                
                total_players += len(players)
                logger.info(f"Guild {guild.name}: Sent {guild_notifications} notifications to {len(players)} total players.")
            
            logger.info(f"Daily notifications complete. Sent {total_notifications} notifications to {total_players} total players across {len(self.bot.guilds)} guilds.")
            
        except Exception as e:
            logger.error(f"Error in daily notifications task: {str(e)}")
    
    async def send_daily_reminder(self, user: discord.User, doom: int, guild_name: str = "Unknown Server"):
        """Send a daily reminder DM to a player."""
        try:
            embed = discord.Embed(
                title="🎭 Ritual War - Daily Action Available",
                description=f"Your daily action is now available in **{guild_name}**! Choose wisely...",
                color=0x800080
            )
            
            embed.add_field(
                name="Current Status", 
                value=f"Doom: {doom}/12", 
                inline=True
            )
            
            embed.add_field(
                name="Available Actions",
                value="• `/hex @target` - Attack a player\n• `/shield` - Defend yourself\n• `/mend @target` - Heal a player",
                inline=False
            )
            
            embed.add_field(
                name="Game Info",
                value="• Use `/leaderboard` to see current standings\n• Use `/inspect` to check your status\n• Remember: Only one action per day!",
                inline=False
            )
            
            embed.set_footer(text="May the best Mage survive! ⚔️")
            
            await user.send(embed=embed)
            logger.debug(f"Sent daily reminder to {user.display_name} (ID: {user.id})")
            
        except discord.Forbidden:
            logger.warning(f"Cannot send DM to user {user.display_name} (ID: {user.id}) - DMs disabled")
        except Exception as e:
            logger.error(f"Error sending daily reminder to {user.display_name} (ID: {user.id}): {str(e)}")
    
    @daily_notifications.before_loop
    async def before_daily_notifications(self):
        """Wait for bot to be ready before starting notifications."""
        await self.bot.wait_until_ready()
        logger.info("Daily notification scheduler initialized")


async def setup(bot: commands.Bot):
    """Setup function to add the scheduler to the bot."""
    scheduler = DailyScheduler(bot)
    # Store reference so it doesn't get garbage collected
    bot.daily_scheduler = scheduler