import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("DISCORD_TOKEN")
TOKEN = token

# Intents: needed for reading messages
intents = discord.Intents.default()
intents.message_content = True  # IMPORTANT for text commands

# Prefix: what your commands start with (!ping, !hello, etc.)
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.load_extension("cogs.roll")
    print("Kal-os is running.")


# Simple command: !ping
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "No bot token found. Set DISCORD_BOT_TOKEN env variable or hard-code TOKEN."
        )
    bot.run(TOKEN)
