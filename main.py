import os
from dotenv import load_dotenv
import asyncio
import discord
import json
from discord.ext import commands

load_dotenv()

intents = discord.Intents.all()
app = commands.Bot(command_prefix='~', intents=intents)


def check_owner(ctx):
    return ctx.author.id in list(map(int, os.getenv("WHITELIST").split(",")))


async def load_extensions():
    for filename in os.listdir("Cogs"):
        if filename.endswith(".py"):
            await app.load_extension(f"Cogs.{filename[:-3]}")


@app.command(name="reload")
@commands.check(check_owner)
async def reload_extension(ctx, extension=None):
    if extension is not None:
        await unload_function(extension)
        try:
            await app.load_extension(f"Cogs.{extension}")
        except commands.ExtensionNotFound:
            await ctx.send(f":x: '{extension}'을(를) 파일을 찾을 수 없습니다!")
        except (commands.NoEntryPointError, commands.ExtensionFailed):
            await ctx.send(f":x: '{extension}'을(를) 불러오는 도중 에러가 발생했습니다!")
        else:
            await ctx.send(f":white_check_mark: '{extension}'을(를) 다시 불러왔습니다!")
    else:
        for filename in os.listdir("Cogs"):
            if filename.endswith(".py"):
                await unload_function(filename[:-3])
                try:
                    await app.load_extension(f"Cogs.{filename[:-3]}")
                except commands.ExtensionNotFound:
                    await ctx.send(f":x: '{filename[:-3]}'을(를) 파일을 찾을 수 없습니다!")
                except (commands.NoEntryPointError, commands.ExtensionFailed):
                    await ctx.send(f":x: '{filename[:-3]}'을(를) 불러오는 도중 에러가 발생했습니다!")
        await ctx.send(":white_check_mark: reload 작업을 완료하였습니다!")


@app.command(name="unload")
@commands.check(check_owner)
async def unload_extension(ctx, extension=None):
    if extension is not None:
        await unload_function(extension)
        await ctx.send(f":white_check_mark: {extension}기능을 종료했습니다!")
    else:
        await unload_function(None)
        await ctx.send(":white_check_mark: 모든 확장기능을 종료했습니다!")


async def unload_function(extension=None):
    if extension is not None:
        try:
            await app.unload_extension(f"Cogs.{extension}")
        except (commands.ExtensionNotLoaded, commands.ExtensionNotFound):
            pass
    else:
        for filename in os.listdir("Cogs"):
            if filename.endswith(".py"):
                try:
                    await app.unload_extension(f"Cogs.{filename[:-3]}")
                except (commands.ExtensionNotLoaded, commands.ExtensionNotFound):
                    pass


async def main():
    async with app:
        await load_extensions()
        print("========== MUSIC BOT STARTED!! ==========")
        await app.start(os.getenv("TOKEN"))


asyncio.run(main())
