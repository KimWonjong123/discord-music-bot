import asyncio
import os
import discord
import concurrent.futures
from discord import FFmpegPCMAudio
from discord.ext import commands
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

from Cogs.utils.ytdl import YTDL

load_dotenv()

filters = list(os.getenv("FILTERS").split(","))


async def callback(ctx):
    if ctx.invoked_with in [
        "join",
        "play",
        "p",
        "재생",
        "ㅈㅅ",
        "ㅍㄹㅇ",
        "ㅍ",
        "j",
        "참가",
        "ㅊㄱ",
        "들어와",
        "ㄷㅇㄹ",
        "search",
        "ㄱㅅ",
        "검색",
    ]:
        title = "Connected to voice channel"
    elif ctx.invoked_with in ["leave", "l", "나가", "ㄴㄱ"]:
        title = "Leaving voice channel"
    channel = ctx.author.voice.channel
    embed = discord.Embed(title=title, color=0x79B1C8)
    embed.add_field(name="", value=channel.name, inline=True)
    await asyncio.create_task(ctx.send(embed=embed))


def check_filters(info):
    for k in filters:
        for s in info.values():
            if k in str(s).lower():
                return True


def info_to_dict(title, uploader, original_url, thumbnail, duration):
    result = {
        "title": title,
        "uploader": uploader,
        "url": original_url,
        "thumbnail": thumbnail,
        "duration": duration,
    }
    return result


class SelectMusic(discord.ui.Select):
    def __init__(self, music_info: list[dict], ctx: commands.Context):
        options = []
        self.info = music_info
        self.ctx = ctx
        for idx, info in enumerate(music_info):
            options.append(
                discord.SelectOption(
                    label=f"{info['title']}",
                    description=f"{info['uploader']}  |  재생시간: {info['duration']}",
                    value=idx,
                )
            )
        super().__init__(
            placeholder="음악 선택", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        info = self.info[int(interaction.data["values"][0])]
        embed = discord.Embed(
            title="선택한 음악",
            color=0x79B1C8,
            description=f"### [{info['title']}"
            "  |  "
            f"{info['uploader']}]({info['url']})",
        )
        embed.set_thumbnail(url=info["thumbnail"])
        await interaction.response.send_message(embed=embed)
        await interaction.message.delete()
        await self.ctx.invoke(self.ctx.bot.get_command("play"), info["url"])


class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.red, label="취소", row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()


class SelectView(discord.ui.View):
    def __init__(self, music_info: list[dict], ctx: commands.Context):
        super().__init__()
        self.add_item(SelectMusic(music_info, ctx))
        self.add_item(CancelButton())


class Music(commands.Cog):
    def __init__(self, app):
        self.app = app
        self.queue = []
        self.now_playing = None
        self.YDL_OPTIONS = {
            "format": "bestaudio",
            "noplaylist": "True",
        }
        self.FFMPEG_OPTS = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn",
        }

    def fetch_shorts(self, shorts):
        url = f"https://www.youtube.com/watch?v={shorts['id']}"
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch:{url}", download=False)["entries"][0]
            except Exception as e:
                return False
        if check_filters(info):
            return False
        return info

    def handle_shorts(self, shorts_list):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(self.fetch_shorts, shorts_list)
        return results

    def search(self, arg):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch:{arg}", download=False)["entries"][0]
            except Exception as e:
                return False
        if check_filters(info):
            return False
        return {"source": info["url"],
                "title": info["title"],
                "original_url": info["original_url"],
                "thumbnail": info["thumbnails"][0]['url'],}

    def search_list(self, arg, quantity):
        with YTDL(self.YDL_OPTIONS) as ydl:
            try:
                info = list(ydl.extract_urls(f"ytsearch{quantity}:{arg}", download=False)["entries"])
                shorts = []
                for i, entry in enumerate(info):
                    if 'shorts' in entry['url']:
                        shorts.append((i, entry))
                if len(shorts) > 0:
                    data = list(self.handle_shorts(list(map(lambda x: x[1], shorts))))
                    for i, entry in enumerate(data):
                        if entry:
                            entry['url'] = entry['original_url']
                            info[shorts[i][0]] = entry
                        else:
                            data[i] = None
                    for i, entry in enumerate(data):
                        if not entry:
                            info.pop(shorts[i][0])
            except Exception as e:
                return False
        for entry in info:
            if check_filters(entry):
                info.remove(entry)
        return info

    @commands.command(name="join", aliases=["j", "참가", "ㅊㄱ", "들어와", "ㄷㅇㄹ"])
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
            await asyncio.create_task(
                ctx.voice_client.move_to(ctx.author.voice.channel)
            )
        await callback(ctx)

    @commands.command(name="search", alliases=["검색", "ㄱㅅ"])
    async def search_videos(self, ctx, *args):
        query = " ".join(args)
        video_list = self.search_list(query, int(os.getenv("SEARCH_PAGE_SIZE")))
        result = []
        for item in video_list:
            duration = int(item["duration"])
            seconds, duration = duration % 60, duration // 60
            minutes, duration = duration % 60, duration // 60
            minutes += 60 * duration
            duration = "{:d}:{:02d}".format(minutes, seconds)
            result.append(
                info_to_dict(
                    item["title"],
                    item["uploader"],
                    item["url"],
                    item["thumbnails"][0]["url"],
                    duration,
                )
            )
        view = SelectView(result, ctx)
        await ctx.send("검색 결과", view=view)

    @commands.command(name="leave", aliases=["l", "나가", "ㄴㄱ"])
    async def leave(self, ctx):
        if ctx.me.voice is not None:
            self.queue.clear()
            self.now_playing = None
            try:
                ctx.voice_client.stop()
            except Exception:
                pass
            await asyncio.create_task(ctx.voice_client.disconnect(force=True))
        else:
            await asyncio.create_task(ctx.send("Not connected to any voice channel"))
            return
        await callback(ctx)

    async def play_song(self, ctx, song):
        voice_client = ctx.voice_client
        m_url = song["source"]
        voice_client.play(
            FFmpegPCMAudio(m_url, **self.FFMPEG_OPTS),
            after=lambda e: self.play_next(ctx),
        )
        embed = discord.Embed(
            title="Now Playing",
            description=f"### [{song['title']}]({song['original_url']})",
            color=0x79B1C8,
        )
        embed.set_thumbnail(url=song["thumbnail"])
        embed.add_field(name="Requested by", value=f"{song['requestor'].global_name}")
        await asyncio.create_task(ctx.send(embed=embed))
        self.now_playing = song

    def play_next(self, ctx):
        if len(self.queue) > 0:
            voice_client = ctx.voice_client
            song = self.queue.pop(0)
            m_url = song["source"]
            voice_client.play(
                FFmpegPCMAudio(m_url, **self.FFMPEG_OPTS),
                after=lambda e: self.play_next(ctx),
            )
        else:
            self.now_playing = None

    async def play_music(self, ctx):
        if len(self.queue) > 0:
            song = self.queue.pop(0)
            asyncio.create_task(self.play_song(ctx, song))

    @commands.command(
        name="play",
        aliases=["p", "재생", "ㅈㅅ", "ㅍㄹㅇ", "ㅍ"],
        help="Plays a selected song from youtube",
    )
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
                await ctx.send(
                    "Could not download the song. Incorrect format try another keyword"
                )
            else:
                song['requestor'] = ctx.author
                embed = discord.Embed(
                    title="Added to queue",
                    description=f"### [{song['title']}]({song['original_url']})",
                    color=0x79B1C8,
                )
                embed.set_thumbnail(url=song["thumbnail"])
                embed.add_field(name="Requested by", value=f"{song['requestor'].global_name}")
                await asyncio.create_task(
                    ctx.send(embed=embed)
                )
                self.queue.append(song)
                if not voice_client.is_playing():
                    await self.play_music(ctx)

    @commands.command(
        name="pause",
        aliases=["일시정지", "정지", "ㅈㅈ", "멈춰" "ㅁㅊ"],
        help="Pauses the current song",
    )
    async def pause(self, ctx):
        voice_client = ctx.voice_client
        if (
            ctx.author.voice is not None
            and voice_client.channel == ctx.author.voice.channel
        ):
            if voice_client.is_connected() and voice_client.is_playing():
                ctx.voice_client.pause()
            else:
                await ctx.send("Not connected to any voice channel or not playing")
        else:
            await ctx.send(
                "Not in the same channel or Join voice channel first to pause"
            )

    @commands.command(name="resume", help="Resumes the current song", alliases=["r"])
    async def resume(self, ctx):
        voice_client = ctx.voice_client
        if (
            voice_client.channel == ctx.author.voice.channel
            and ctx.author.voice is not None
        ):
            if voice_client.is_connected():
                if (
                    voice_client.channel == ctx.author.voice.channel
                    and voice_client.is_paused()
                ):
                    voice_client.resume()
                else:
                    await ctx.send("Not in the same channel or not paused")
            else:
                await ctx.send("Not connected to any voice channel")
        else:
            await ctx.send(
                "Not in the same channel or Join voice channel first to resume"
            )

    @commands.command(
        name="skip",
        help="Skips the current song",
        aliases=["s", "다음", "다음곡", "ㄷㅇ", "넘겨"],
    )
    async def skip(self, ctx):
        voice_client = ctx.voice_client
        if (
            voice_client.is_connected()
            and voice_client.is_playing()
            or voice_client.is_paused()
            and voice_client.channel == ctx.author.voice.channel
        ):
            self.now_playing = None
            voice_client.stop()
            await self.play_music(ctx)
        else:
            await ctx.send("Not connected to any voice channel or not playing")

    @commands.command(
        name="queue",
        aliases=["q", "큐", "ㅋ", "대기열", "ㄷㄱㅇ"],
        help="Shows the current queue",
    )
    async def queue_info(self, ctx):
        voice_client = ctx.voice_client
        if voice_client.is_connected():
            description = ""
            for i, song in enumerate(self.queue):
                description += (f"**{i + 1}. [{song['title']}]({song['original_url']})**"
                                f"Requested by {song['requestor'].global_name}\n\n")
            if description == "":
                description = "Queue is currently empty."
            embed = discord.Embed(title="Queue",
                                  description=description,
                                  color=0x79B1C8,)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Not connected to any voice channel")

    @commands.command(
        name="clear", help="Clears the current queue", aliases=["c", "클리어", "ㅋㄹㅇ"]
    )
    async def clear_queue(self, ctx):
        voice_client = ctx.voice_client
        if (
            voice_client.is_connected()
            and voice_client.channel == ctx.author.voice.channel
        ):
            voice_client.stop()
        self.queue.clear()
        await ctx.send("Queue cleared")

    @commands.command(
        name="nowplaying",
        aliases=["np", "재생중", "ㅈㅅㅈ", "현재", "현재재생중", "ㅎㅈ"],
        help="Shows the current playing song",
    )
    async def now_playing(self, ctx):
        voice_client = ctx.voice_client
        if voice_client is not None and voice_client.is_connected() and self.now_playing is not None:
            embed = discord.Embed(
                title="Now Playing",
                description=f"### [{self.now_playing['title']}]({self.now_playing['original_url']})",
                color=0x79B1C8,
            )
            embed.set_thumbnail(url=self.now_playing["thumbnail"])
            embed.add_field(name="Requested by", value=f"{self.now_playing['requestor'].global_name}")
            await asyncio.create_task(ctx.send(embed=embed))
        else:
            embed = discord.Embed(
                title="Now Playing",
                description=f"No song playing.",
                color=0x79B1C8,
            )
            await ctx.send(embed=embed)

    @commands.command(name="voice_info", help="Shows the current voice client info")
    async def voice_info(self, ctx):
        voice_client = ctx.voice_client
        if voice_client.is_connected():
            embed = discord.Embed(title="Voice Client Info", color=discord.Color.red())
            embed.add_field(
                name="Channel", value=voice_client.channel.name, inline=False
            )
            embed.add_field(
                name="Connected", value=voice_client.is_connected(), inline=False
            )
            embed.add_field(
                name="Playing", value=voice_client.is_playing(), inline=False
            )
            embed.add_field(name="Paused", value=voice_client.is_paused(), inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Not connected to any voice channel")


async def setup(app):
    await app.add_cog(Music(app))
