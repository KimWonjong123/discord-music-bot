import os
from dotenv import load_dotenv
import asyncio
import discord
from discord.ext import commands

load_dotenv()

intents = discord.Intents.all()
app = commands.Bot(command_prefix='!', intents=intents)


async def main():
    async with app:
        await app.start(os.getenv("TOKEN"))


@app.command(name="ping")
async def ping(ctx):
    caller = ctx.author.global_name
    embed = discord.Embed(title="Ping Test", color=0x79b1c8)
    embed.add_field(name="caller", value=caller, inline=True)
    embed.add_field(name="status", value="live", inline=True)
    await ctx.send(embed=embed)

asyncio.run(main())
