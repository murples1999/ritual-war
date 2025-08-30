"""Main entry point for the Ritual War Discord bot."""

import os
import sys
import asyncio
import logging
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from error_handler import ErrorHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ritual_war.log')
    ]
)
logger = logging.getLogger(__name__)


def load_or_prompt_env():
    """Load environment variables or prompt for token if missing."""
    load_dotenv()
    
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.warning("DISCORD_TOKEN not found in .env file")
        token = input("Please enter your Discord bot token: ").strip()
        
        if not token:
            logger.error("No token provided. Exiting.")
            sys.exit(1)
        
        # Save token to .env file
        env_path = Path('.env')
        with env_path.open('a') as f:
            f.write(f"\nDISCORD_TOKEN={token}\n")
        logger.info("Token saved to .env file")
    
    # Set timezone if not specified
    if not os.getenv('TIMEZONE'):
        with open('.env', 'a') as f:
            f.write("TIMEZONE=America/Los_Angeles\n")
    
    return token


class RitualWarBot(commands.Bot):
    """The main Ritual War bot class."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = False  # We only use slash commands
        # intents.members = True  # Optional - enable in Discord Developer Portal if needed
        
        super().__init__(
            command_prefix='!',  # Unused but required
            intents=intents,
            description="A Discord bot for playing Ritual War - a daily-move PvP game"
        )
        
        # Initialize error handler
        owner_id = int(os.getenv('BOT_OWNER_ID', '192433389855309833'))
        self.error_handler = ErrorHandler(self, owner_id)
    
    async def setup_hook(self):
        """Setup hook called when the bot is ready."""
        logger.info("Setting up Ritual War bot...")
        
        try:
            # Load the game commands cog
            await self.load_extension('game.commands')
            logger.info("Loaded game commands")
        except Exception as e:
            await self.error_handler.notify_owner("Failed to load game commands", str(e), e)
            logger.error(f"Failed to load game commands: {e}")
            raise
        
        try:
            # Load admin commands cog
            await self.load_extension('game.admin_commands')
            logger.info("Loaded admin commands")
        except Exception as e:
            await self.error_handler.notify_owner("Failed to load admin commands", str(e), e)
            logger.error(f"Failed to load admin commands: {e}")
            # Don't raise - admin commands are optional
        
        try:
            # Load daily scheduler
            await self.load_extension('game.scheduler')
            logger.info("Loaded daily notification scheduler")
        except Exception as e:
            await self.error_handler.notify_owner("Failed to load scheduler", str(e), e)
            logger.error(f"Failed to load scheduler: {e}")
            # Don't raise - scheduler is optional but recommended
        
        try:
            # Sync commands
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            await self.error_handler.notify_owner("Failed to sync commands", str(e), e)
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"Ritual War bot is ready! Logged in as {self.user}")
        logger.info(f"Bot is in {len(self.guilds)} guild(s)")
        
        # Set bot status
        try:
            activity = discord.Game(name="Ritual War | /leaderboard")
            await self.change_presence(activity=activity)
            
            # Send startup notification
            await self.error_handler.send_startup_notification()
        except Exception as e:
            logger.error(f"Error in on_ready: {e}")
    
    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        logger.error(f"Command error: {error}")
        await self.error_handler.notify_owner("Command Error", f"Context: {ctx.command}", error)
    
    async def on_app_command_error(self, interaction, error):
        """Handle application command errors."""
        await self.error_handler.handle_interaction_error(interaction, error)
    
    async def on_error(self, event, *args, **kwargs):
        """Handle general bot errors."""
        try:
            # Get the current exception
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if exc_value:
                context = {"event": event, "args": str(args)[:500]}
                await self.error_handler.notify_owner(f"Bot Error in {event}", str(context), exc_value)
            
            logger.error(f"Bot error in event {event}", exc_info=True)
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
    
    async def close(self):
        """Clean shutdown."""
        logger.info("Shutting down Ritual War bot...")
        try:
            await self.error_handler.notify_owner("Bot Shutdown", "Ritual War bot is shutting down normally")
        except Exception as e:
            logger.error(f"Error sending shutdown notification: {e}")
        await super().close()


async def main():
    """Main function to run the bot."""
    try:
        token = load_or_prompt_env()
        bot = RitualWarBot()
        
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        # Try to send crash notification if possible
        try:
            if 'bot' in locals() and hasattr(bot, 'error_handler'):
                await bot.error_handler.notify_owner("Bot Crashed", "Fatal error during startup", e)
        except:
            pass
        raise
    finally:
        if 'bot' in locals() and not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
