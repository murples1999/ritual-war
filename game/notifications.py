"""Notification system for Ritual War."""

import os
import discord
from .config import RITUAL_WAR_CHANNEL_ID
from .storage import GameStorage


class NotificationManager:
    """Handles channel restrictions and DM notifications."""
    
    def __init__(self, bot):
        self.bot = bot
        self.storage = GameStorage()
    
    async def send_public_message(self, interaction: discord.Interaction, content=None, embed=None):
        """Send public message to configured channel or fallback."""
        try:
            channel = None
            guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
            
            # Check if there's a configured channel for this guild
            configured_channel_id = await self.storage.get_state("public_channel", guild_id)
            
            if configured_channel_id:
                # Use the configured channel
                channel = self.bot.get_channel(int(configured_channel_id))
                if not channel:
                    # Channel was deleted or bot can't access it
                    print(f"Configured channel {configured_channel_id} not accessible, clearing setting")
                    await self.storage.set_state("public_channel", "", guild_id)  # Clear invalid setting
            
            # If no configured channel or it's not accessible, use fallback logic
            if not channel:
                # For your original server, use the hardcoded channel as default
                if interaction.guild_id == 1379345639904776273:
                    channel = self.bot.get_channel(RITUAL_WAR_CHANNEL_ID)
                
                # Final fallback to interaction channel
                if not channel:
                    channel = interaction.channel
            
            # Send the message
            if content:
                await channel.send(content)
            elif embed:
                await channel.send(embed=embed)
            
        except Exception as e:
            print(f"Failed to send public message: {e}")
            # Final fallback to interaction followup
            try:
                if content:
                    await interaction.followup.send(content)
                elif embed:
                    await interaction.followup.send(embed=embed)
            except:
                pass
    
    
    async def send_victory_announcement(self, interaction: discord.Interaction, winner_id: str, winner_name: str):
        """Send public victory announcement."""
        embed = discord.Embed(
            title="🎉 Ritual War Complete!",
            description=f"<@{winner_id}> is the last Mage standing and wins the game!",
            color=0xffd700
        )
        embed.add_field(
            name="🏆 Victory!",
            value=f"**{winner_name}** has emerged victorious in the Ritual War!",
            inline=False
        )
        embed.add_field(
            name="🎮 New Game",
            value="Use `/admin_reset_game` to start a new round!",
            inline=False
        )
        embed.set_footer(text="Congratulations to our champion!")
        
        await self.send_public_message(interaction, embed=embed)