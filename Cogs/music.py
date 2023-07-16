import discord
from discord import FFmpegPCMAudio
from discord.ext import commands
from youtube_dl import YoutubeDL


async def callback(ctx):
    if ctx.invoked_with == "join":
        title = "Connected to voice channel"
    elif ctx.invoked_with == "leave":
        title = "Leaving voice channel"
    channel = ctx.author.voice.channel
    embed = discord.Embed(title=title, color=0x79b1c8)
    embed.add_field(name="", value=channel.name, inline=True)
    await ctx.reply(embed=embed)


class Music(commands.Cog):

    def __init__(self, app):
        self.app = app
        self.queue = []
        self.voice = None
        self.is_playing = False
        self.is_paused = False
        self.YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True',}
        self.FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                            'options': '-vn'}

    def search(self, arg):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch:{arg}", download=False)['entries'][0]
            except Exception as e:
                return False
        return {'source': info['formats'][0]['url'], 'title': info['title']}

    def play_next(self):
        if len(self.queue) > 0:
            m_url = self.queue[0][0]['source']
            self.queue.pop(0)
            self.voice.play(FFmpegPCMAudio(m_url, **self.FFMPEG_OPTS), after=lambda e: self.play_next())
        else:
            self.is_playing = False

    @commands.command(name="join")
    async def join(self, ctx):
        if ctx.author.voice is None:
            await ctx.reply("Join voice channel first")
            return
        if ctx.me.voice is None:
            await ctx.author.voice.channel.connect()
        else:
            if ctx.me.voice.channel == ctx.author.voice.channel:
                await ctx.reply("Already in the same channel")
                return
            await ctx.voice_client.move_to(ctx.author.voice.channel)
        await callback(ctx)

    @commands.command(name="leave")
    async def leave(self, ctx):
        if ctx.me.voice is not None:
            self.is_playing = False
            self.queue = []
            self.voice.stop()
            self.is_paused = False
            await ctx.voice_client.disconnect()
        else:
            await ctx.reply("Not connected to any voice channel")
            return
        await callback(ctx)

    async def play_music(self, ctx):
        if len(self.queue) > 0:
            self.is_playing = True
            m_url = self.queue[0][0]['source']

            try:
                self.voice.play(FFmpegPCMAudio(m_url, **self.FFMPEG_OPTS), after=lambda e: self.play_next())
                await ctx.reply(f"Now playing {self.queue[0][0]['title']}")
            except Exception as err:
                print(err)
            self.queue.pop(0)

        else:
            self.is_playing = False

    @commands.command(name="play", aliases=['p', 'playing'], help="Plays a selected song from youtube")
    # @commands.check(check_owner)
    async def play(self, ctx, *args):
        query = " ".join(args)

        voice_channel = ctx.author.voice.channel
        if voice_channel is None:
            await ctx.reply("Join voice channel first")
            return
        elif self.is_paused:
            self.voice.resume()
        else:
            song = self.search(query)
            if not song:
                await ctx.reply("Could not download the song. Incorrect format try another keyword")
            else:
                await ctx.send(f"Added {song['title']} to the queue")
                self.queue.append([song, voice_channel])
                self.voice = ctx.voice_client

                if not self.is_playing:
                    await self.play_music(ctx)

    @commands.command(name="pause", help="Pauses the current song")
    async def pause(self, ctx):
        if self.voice.is_playing():
            self.is_playing = False
            self.is_paused = True
            self.voice.pause()
        else:
            self.is_playing = True
            self.is_paused = False
            self.voice.resume()

    @commands.command(name="resume", help="Resumes the current song", alliases=['r'])
    async def resume(self, ctx):
        if self.voice.is_paused():
            self.is_playing = True
            self.is_paused = False
            self.voice.resume()

    @commands.command(name="skip", help="Skips the current song")
    async def skip(self, ctx):
        if self.voice is not None and self.voice.is_playing():
            self.voice.stop()
            await self.play_music(ctx)

    @commands.command(name="queue", help="Shows the current queue")
    async def queue_info(self, ctx):
        retval = ""
        for i in range(len(self.queue)):
            retval += f"{i + 1}. {self.queue[i][0]['title']}\n"
        if retval != "":
            await ctx.send(retval)
        else:
            await ctx.send("No songs in queue")

    @commands.command(name="clear", help="Clears the current queue")
    async def clear_queue(self, ctx):
        if self.voice is not None and self.is_playing:
            self.voice.stop()
        self.queue.clear()
        await ctx.send("Queue cleared")


async def setup(app):
    await app.add_cog(Music(app))
