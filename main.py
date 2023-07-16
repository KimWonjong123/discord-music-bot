import os
from dotenv import load_dotenv
import asyncio
import discord
from discord.ext import commands

load_dotenv()

intents = discord.Intents.all()
app = commands.Bot(command_prefix='!', intents=intents)

async def load_extensions():
    for filename in os.listdir("Cogs"):
        if filename.endswith(".py"):
            await app.load_extension(f"Cogs.{filename[:-3]}")


async def main():
    async with app:
        await load_extensions()
        await app.start(os.getenv("TOKEN"))


asyncio.run(main())
