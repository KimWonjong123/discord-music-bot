import asyncio
import os
import discord
from discord import FFmpegPCMAudio
from discord.ext import commands
from googleapiclient.discovery import build
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
from isodate import parse_duration

load_dotenv()

filters = list(os.getenv("FILTERS").split(","))


async def callback(ctx):
    if ctx.invoked_with in ["join", "play", 'p', '재생', 'ㅈㅅ', 'ㅍㄹㅇ', 'ㅍ', 'j', '참가', 'ㅊㄱ', '들어와', 'ㄷㅇㄹ']:
        title = "Connected to voice channel"
    elif ctx.invoked_with in ["leave", 'l', '나가', 'ㄴㄱ']:
        title = "Leaving voice channel"
    channel = ctx.author.voice.channel
    embed = discord.Embed(title=title, color=0x79b1c8)
    embed.add_field(name="", value=channel.name, inline=True)
    await asyncio.create_task(ctx.send(embed=embed))


def check_filters(info):
    for k in filters:
        for s in info.values():
            if k in str(s).lower():
                return True


def info_to_dict(video_id, title, uploader):
    result = {
        "id": video_id,
        "url": f'https://youtu.be/{video_id}',
        "title": title,
        "uploader": uploader,
    }
    return result


class Music(commands.Cog):

    def __init__(self, app):
        self.app = app
        self.queue = []
        self.voice = None
        self.is_playing = False
        self.is_paused = False
        self.now_playing = None
        self.YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True', }
        self.FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                            'options': '-vn'}
        self.youtube = build(os.getenv('YOUTUBE_API_SERVICE_NAME'),
                             os.getenv('YOUTUBE_API_VERSION'),
                             developerKey=os.getenv('YOUTUBE_API_KEY'))

    def search(self, arg):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch:{arg}", download=False)['entries'][0]
            except Exception as e:
                return False
        try:
            if check_filters(info):
                return False
        except Exception as e:
            print(e)
        return {'source': info['url'], 'title': info['title']}

    def play_next(self, ctx):
        self.now_playing = None
        if len(self.queue) > 0:
            m_url = self.queue[0][0]['source']
            self.queue.pop(0)
            ctx.voice_client.play(FFmpegPCMAudio(m_url, **self.FFMPEG_OPTS), after=lambda e: self.play_next())
        else:
            self.is_playing = False

    @commands.command(name="join", aliases=['j', '참가', 'ㅊㄱ', '들어와', 'ㄷㅇㄹ'])
    async def join(self, ctx):
        if ctx.author.voice is None:
            await ctx.send("Join voice channel first")
            return
        self.now_playing = None
        if ctx.me.voice is None:
            await asyncio.create_task(ctx.author.voice.channel.connect())
        else:
            if ctx.me.voice.channel == ctx.author.voice.channel:
                await ctx.send("Already in the same channel")
                return
            ctx.voice_client.stop()
            await asyncio.create_task(ctx.voice_client.move_to(ctx.author.voice.channel))
        await callback(ctx)

    @commands.command(name="search", alliases=['검색', 'ㄱㅅ'])
    async def search_videos(self, ctx, *args):
        if ctx.author.voice is None:
            await ctx.send("Join voice channel first")
            return
        query = " ".join(args)
        video_list = self.youtube.search().list(
            q=query,
            order="relevance",
            part="snippet",
            maxResults=10,
            type="video",
        ).execute()
        result_json = {}
        for i, item in enumerate(video_list['items']):
            result_json[i] = info_to_dict(item['id']['videoId'],
                                          item['snippet']['title'],
                                          item['snippet']['channelTitle'])
        result_text = ''
        for k, v in result_json.items():
            video_info = self.youtube.videos().list(
                part="contentDetails",
                id=v['id'],
            ).execute()
            duration = str(parse_duration(video_info['items'][0]['contentDetails']['duration']))
            hours = int(duration.split(":")[0])
            minutes = int(duration.split(":")[1])
            seconds = int(duration.split(":")[2])
            if hours:
                minutes += hours * 60
            duration = '{:02d}:{:02d}'.format(minutes, seconds)
            result_text += f"**{k + 1}.** [*{v['title']}* | {v['uploader']}]({v['url']})  ``{duration}``\n"
        embed = discord.Embed(title="Search results", description=result_text, color=0x79b1c8)
        await ctx.send(embed=embed)

    @commands.command(name="leave", aliases=['l', '나가', 'ㄴㄱ'])
    async def leave(self, ctx):
        if ctx.me.voice is not None:
            self.queue.clear()
            self.now_playing = None
            try:
                self.voice.stop()
            except Exception:
                pass
            await asyncio.create_task(ctx.voice_client.disconnect(force=True))
        else:
            await asyncio.create_task(ctx.send("Not connected to any voice channel"))
            return
        await callback(ctx)

    async def play_music(self, ctx):
        if len(self.queue) > 0:
            voice_client = ctx.voice_client
            m_url = self.queue[0][0]['source']
            try:
                voice_client.play(FFmpegPCMAudio(m_url, **self.FFMPEG_OPTS), after=lambda e: self.play_next(ctx))
                await asyncio.create_task(ctx.send(f"Now playing {self.queue[0][0]['title']}"))
                self.now_playing = self.queue[0][0]['title']
            except Exception as err:
                print(err)
            self.queue.pop(0)

    @commands.command(name="play", aliases=['p', '재생', 'ㅈㅅ', 'ㅍㄹㅇ', 'ㅍ'], help="Plays a selected song from youtube")
    async def play(self, ctx, *args):
        query = " ".join(args)
        voice_client = ctx.voice_client
        if ctx.author.voice is None:
            await ctx.send("Join voice channel first")
            return
        voice_channel = ctx.author.voice.channel
        if voice_client is None:
            await voice_channel.connect(self_deaf=True)
            await asyncio.create_task(callback(ctx))
            voice_client = ctx.voice_client
        elif voice_client.channel != voice_channel:
            voice_client.stop()
            await asyncio.create_task(self.clear_queue(ctx))
            await voice_client.move_to(voice_channel)
            await asyncio.create_task(callback(ctx))
            await asyncio.sleep(0.5)

        if voice_client.is_paused():
            voice_client.resume()
        else:
            song = self.search(query)
            if not song:
                await ctx.send("Could not download the song. Incorrect format try another keyword")
            else:
                await asyncio.create_task(ctx.send(f"Added {song['title']} to the queue"))
                self.queue.append([song, voice_channel])
                if not voice_client.is_playing():
                    await self.play_music(ctx)

    @commands.command(name="pause", aliases=['일시정지', '정지', 'ㅈㅈ', '멈춰' 'ㅁㅊ'], help="Pauses the current song")
    async def pause(self, ctx):
        voice_client = ctx.voice_client
        if voice_client.channel == ctx.author.voice.channel and ctx.author.voice is not None:
            if voice_client.is_connected() and voice_client.is_playing():
                self.voice.pause()
            else:
                await ctx.send("Not connected to any voice channel or not playing")
        else:
            await ctx.send("Not in the same channel or Join voice channel first to pause")

    @commands.command(name="resume", help="Resumes the current song", alliases=['r'])
    async def resume(self, ctx):
        voice_client = ctx.voice_client
        if voice_client.channel == ctx.author.voice.channel and ctx.author.voice is not None:
            if voice_client.is_connected():
                if voice_client.channel == ctx.author.voice.channel and voice_client.is_paused():
                    voice_client.resume()
                else:
                    await ctx.send("Not in the same channel or not paused")
            else:
                await ctx.send("Not connected to any voice channel")
        else:
            await ctx.send("Not in the same channel or Join voice channel first to resume")

    @commands.command(name="skip", help="Skips the current song", aliases=['s', '다음', '다음곡', 'ㄷㅇ', '넘겨'])
    async def skip(self, ctx):
        voice_client = ctx.voice_client
        if voice_client.is_connected() and voice_client.is_playing() or voice_client.is_paused() \
                and voice_client.channel == ctx.author.voice.channel:
            self.now_playing = None
            voice_client.stop()
            await self.play_music(ctx)
        else:
            await ctx.send("Not connected to any voice channel or not playing")

    @commands.command(name="queue", aliases=['q', '큐', 'ㅋ', '대기열', 'ㄷㄱㅇ'], help="Shows the current queue")
    async def queue_info(self, ctx):
        voice_client = ctx.voice_client
        if voice_client.is_connected():
            embed = discord.Embed(title="Queue", color=discord.Color.red())
            retval = ""
            for i in range(len(self.queue)):
                retval = f"{i + 1}. {self.queue[i][0]['title']}"
                embed.add_field(name=retval, value="", inline=False)
            if retval == "":
                embed.add_field(name="Queue is currently empty", value="", inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Not connected to any voice channel")

    @commands.command(name="clear", help="Clears the current queue", aliases=['c', '클리어', 'ㅋㄹㅇ'])
    async def clear_queue(self, ctx):
        voice_client = ctx.voice_client
        if voice_client.is_connected() and voice_client.channel == ctx.author.voice.channel:
            voice_client.stop()
        self.queue.clear()
        await ctx.send("Queue cleared")

    @commands.command(name="nowplaying", aliases=['np', '재생중', 'ㅈㅅㅈ', '현재', '현재재생중', 'ㅎㅈ'],
                      help="Shows the current playing song")
    async def now_playing(self, ctx):
        voice_client = ctx.voice_client
        if voice_client.is_connected() and self.now_playing is not None:
            embed = discord.Embed(title="Now Playing", description="", color=discord.Color.red())
            embed.add_field(name="Song", value=self.now_playing, inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("No songs playing")

    @commands.command(name="voice_info", help="Shows the current voice client info")
    async def voice_info(self, ctx):
        voice_client = ctx.voice_client
        if voice_client.is_connected():
            embed = discord.Embed(title="Voice Client Info", color=discord.Color.red())
            embed.add_field(name="Channel", value=voice_client.channel.name, inline=False)
            embed.add_field(name="Connected", value=voice_client.is_connected(), inline=False)
            embed.add_field(name="Playing", value=voice_client.is_playing(), inline=False)
            embed.add_field(name="Paused", value=voice_client.is_paused(), inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Not connected to any voice channel")


async def setup(app):
    await app.add_cog(Music(app))
