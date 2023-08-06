import discord
from discord.ext import commands


class Ping(commands.Cog):
    def init(self, app):
        self.app = app

    @commands.command(name="ping")
    async def ping(self, ctx):
        caller = ctx.author.global_name
        embed = discord.Embed(title="Ping Test", color=0x79B1C8)
        embed.add_field(name="caller", value=caller, inline=True)
        embed.add_field(name="status", value="live", inline=True)
        asdf = await ctx.reply(embed=embed)
        await ctx.reply(embed=embed)


async def setup(app):
    await app.add_cog(Ping(app))
