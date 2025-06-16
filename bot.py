# Imports discord and essentials from discord
import discord
from discord.ext import commands
from discord import app_commands

# Load Environment Variables
import os
from dotenv import load_dotenv
load_dotenv()

# Set Discord Intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# Sets Guild and Category Id's to be used for the Temp Voice Channels
guildId = discord.Object(id=os.getenv("DISCORD_GUILD_ID"))
categoryId = int(os.getenv("DISCORD_VOICE_CATEGORY"))
permanentVoiceChannelId = int(os.getenv("DISCORD_PERM_VOICE_ID"))

class DiscordBot(commands.Bot):
    async def on_ready(self):
        print(f'Logged in as {bot.user.name}')
        try:
            guild = guildId
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(e)

        # Check for empty voice channels on bot load in the static guild
        print("Checking for empty voice channels on startup...")
        target_guild = self.get_guild(guildId.id)
        if target_guild:
            target_category = target_guild.get_channel(categoryId)
            if isinstance(target_category, discord.CategoryChannel):
                for voice_channel in target_category.voice_channels:
                    # Skip the permanent channel
                    if voice_channel.id == permanentVoiceChannelId:
                        print(f"Skipping permanent channel '{voice_channel.name}' from startup deletion check.")
                        continue

                    if len(voice_channel.members) == 0:
                        try:
                            print(
                                f"Deleting empty voice channel '{voice_channel.name}' (ID: {voice_channel.id}) on startup.")
                            await voice_channel.delete()
                        except discord.Forbidden:
                            print(f"Missing permissions to delete channel '{voice_channel.name}' on startup.")
                        except Exception as e:
                            print(f"Error deleting channel '{voice_channel.name}' on startup: {e}")
            else:
                print(
                    f"Warning: Configured CATEGORY_ID {categoryId} is not a valid category channel in guild {guildId} on startup.")
        else:
            print(
                f"Warning: Guild with ID {guildId} not found on startup. Cannot check voice channels for cleanup.")

    async def on_voice_state_update(self, member, before, after):
        # We only care if a member left a channel
        # or moved from one channel to another
        if before.channel is not None and before.channel != after.channel:
            # Add an ignore for a specific channel ID
            if before.channel.id == permanentVoiceChannelId:
                print(f"Ignored deletion for permanent voice channel: {before.channel.name}")
                return  # Do not proceed with deletion check
            # Check if the channel they left belongs to our designated category
            if before.channel.category_id == categoryId:
                # Check if the channel is now empty
                if len(before.channel.members) == 0:
                    try:
                        print(f"Deleting empty voice channel in designated category: {before.channel.name}")
                        await before.channel.delete()
                    except discord.Forbidden:
                        print(f"Missing permissions to delete channel: {before.channel.name}")
                    except Exception as e:
                        print(f"Error deleting channel {before.channel.name}: {e}")

bot = DiscordBot(command_prefix="!",intents=intents)
@bot.tree.command(name="create-voice",description="Creates temp voice channel", guild=guildId)
@app_commands.describe(channel_name="The name of the new voice channel")
async def create_voice(interaction: discord.Interaction, channel_name: str):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    # Check if the user is in a voice channel
    user_voice_state = interaction.user.voice
    if user_voice_state is None or user_voice_state.channel is None:
        await interaction.response.send_message("You must be in a voice channel to use this command and be moved.", ephemeral=True)
        return

    # Get the category
    category = guild.get_channel(categoryId)
    if not isinstance(category, discord.CategoryChannel):
        await interaction.response.send_message(
            f"The specified category with ID {categoryId} was not found or is not a category channel. Please contact an administrator.",
            ephemeral=True
        )
        return

    try:
        # Create the voice channel within the specified category
        voice_channel = await guild.create_voice_channel(channel_name, category=category)

        # Move the user to the newly created voice channel
        await interaction.user.edit(voice_channel=voice_channel)

        await interaction.response.send_message(
            f"Voice channel '{voice_channel.name}' created successfully in category '{category.name}' and you have been moved to it!",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "I don't have permission to create channels in that category or move members.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(f"Failed to create voice channel or move you: {e}", ephemeral=True)
bot.run(os.getenv("DISCORD_BOT_TOKEN"))