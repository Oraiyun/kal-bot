import asyncio
import os
from typing import cast

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = cast(str, os.getenv("DISCORD_TOKEN"))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Kal-os is running.")


async def main():
    async with bot:
        await bot.load_extension("cogs.roll")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
