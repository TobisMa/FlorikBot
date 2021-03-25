import discord
from discord.ext import commands
from discord.ext.commands.errors import CommandError

import asyncio
import youtube_dl
import os

from helper_functions import *
from bot import on_command_error, is_bot_dev

youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'data/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


# https://github.com/Rapptz/discord.py/blob/master/examples/basic_voice.py
class Music(commands.Cog):
    """Musik-commands"""
    def __init__(self, bot):
        self.bot = bot

    @is_bot_dev()
    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Verbindet sich mit einem angegebenen voice-channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @is_bot_dev()
    @commands.command()
    async def play(self, ctx, *, query):
        """Spielt eine Datei aus dem Dateisystem ab"""
        if not os.path.isfile(query):
            await on_command_error(ctx, FileNotFoundError(f"Die gewünschte Datei {query} existiert nicht."))
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        print(str(source))
        ctx.voice_client.play(source, after=lambda e: self.raise_error(e) if e else None)

        await ctx.send('Spielt {} ab.'.format(query))


    @is_bot_dev()
    @commands.command()
    async def playfile(self, ctx):
        if len(ctx.message.attachments) == 0:
            await on_command_error(ctx, CommandError("Dieser Nachricht liegt keine Datei bei."))
            return
        
        try:
            await ctx.author.voice.channel.connect()
        except:
            pass
        msg = ctx.message
        f = open("test/tmp.mp3", "wb") 
        await msg.attachments[0].save(f)
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(f.name))
        self.bot.voice_clients[0].play(source, after=lambda e: self.raise_error(e) if e else None)
        await asyncio.sleep(10)
        os.remove(f.name)

    @is_bot_dev()
    @commands.command()
    async def yt(self, ctx, *, url):
        """Plays from a url (almost anything youtube_dl supports)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @is_bot_dev()
    @commands.command()
    async def stream(self, ctx, *, url):
        """Streamt den Audioinhalt einer URL"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: self.raise_error(e) if e else None)

        await ctx.send('Spielt {} ab.'.format(player.title))

    @is_bot_dev()
    @commands.command()
    async def volume(self, ctx, volume: int):
        """Ändert die Lautstärke des Bots"""

        if ctx.voice_client is None:
            return await ctx.send("Mit keinem Voicechannel verbunden")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Lautstärke geändert auf {}%".format(volume))

    @is_bot_dev()
    @commands.command()
    async def stop(self, ctx):
        """Trennt die Verbindung zum voicechannel"""
        await ctx.voice_client.disconnect()

    @yt.before_invoke
    @play.before_invoke
    @stream.before_invoke
    @playfile.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("Du bist zu keinem voicechannel verbunden.")
                # raise commands.CommandError("Author not connected to a voice channel")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    def raise_error(self, e):
        print(e)
        raise e

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)



def setup(bot):
    bot.add_cog(Music(bot))