import discord
from discord.ext import commands

import datetime
import json
import random
import aiohttp
from discord.ext.commands.errors import MemberNotFound
import requests

import public_config
from helper_functions import *
from bot import is_bot_dev

class Wholesome(commands.Cog):
    """Wholesome commands um deine Seele zu reinigen"""
    def __init__(self, bot):
        self.bot = bot
        self.cmds = [c.name for c in self.get_commands()]
        self.cmds.remove("add")


    @commands.command()
    async def hug(self, ctx, *, arg : discord.Member):
        """umarme einen anderen Benutzer mit `hug @user`"""
        await self.send(ctx, arg, "hug", "umarmt", cat_ascii="(^・ω・^ )")

    @commands.command()
    async def pat(self, ctx, *, arg : discord.Member):
        """patte einen anderen Benutzer mit `pat @user`"""
        await self.send(ctx, arg, "pat", "gepattet", cat_ascii="(ฅ`･ω･´)っ=")

    @commands.command()
    async def feed(self, ctx, *, arg : discord.Member):
        """füttere einen anderen Benutzer mit `feed @user`"""
        await self.send(ctx, arg, "feed", "gefüttert", cat_ascii="~(=^‥^)_旦~")

    @commands.command()
    async def cuddle(self, ctx, *, arg : discord.Member):
        """knuddle einen anderen Benutzer mit `cuddle @user`"""
        await self.send(ctx, arg, "cuddle", "geknuddelt", cat_ascii="(=^･ω･^)y＝")

    @commands.command()
    async def kiss(self, ctx, *, arg : discord.Member):
        """küsse einen anderen Benutzer mit `kiss @user`"""
        await self.send(ctx, arg, "kiss", "geküsst", cat_ascii="╭(╯ε╰)╮")


    @commands.command()
    async def poke(self, ctx, *, arg : discord.Member):
        """stupst einen anderen Benutzer mit `hug @user` an"""
        await self.send(ctx, arg, "poke", "angestupst", cat_ascii="ヾ(=｀ω´=)ノ”")

    @commands.command()
    async def slap(self, ctx, *, arg : discord.Member):
        """schlage einen anderen Benutzer mit `slap @user`"""
        await self.send(ctx, arg, "slap", "geschlagen", cat_ascii="(ↀДↀ)⁼³₌₃")

    @commands.command()
    async def bite(self, ctx, *, arg : discord.Member):
        """beiße einen anderen Benutzer mit `bite @user`"""
        await self.send(ctx, arg, "bite", "gebissen", cat_ascii="(・∀・)")


    async def send(self, ctx, arg, command, verb, content_type="gif", cat_ascii="(^･o･^)ﾉ”"):
        if arg == ctx.author:
            await ctx.send(embed=simple_embed(ctx.author, "No u", color=discord.Color.red()))
            return
        
        e = discord.Embed(title=f"**{arg.display_name}**, du wurdest von **{ctx.author.display_name}** {verb}", description=cat_ascii)
        e.timestamp = datetime.datetime.now()
        e.color = ctx.author.color
        e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar)

        gifs = self.readJson(command)
        r = random.randint(0, 25 + len(gifs))
        if r < len(gifs):
            url = random.choice(gifs)
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://purrbot.site/api/img/sfw/{command}/{content_type}") as response:
                    rjson = await response.json()
                    if rjson["error"] == False:
                        url = rjson["link"]
                    else:
                        await ctx.send(embed=simple_embed(ctx.author, "Verbindungsfehler zur API", "(´; ω ;｀)", color=discord.Color.red()))
                        return
        e.set_image(url=url)
        await ctx.send(embed=e)
    
    @commands.command()       
    @is_bot_dev()
    async def add(self, ctx, *args):
        """fügt ein GIF für die wholesome-Kategorie hinzu.
        Syntaxbeispiel: `add hug hug_gif.gif`"""

        def is_gif(url):
            try:
                r = requests.head(url)
            except BaseException:
                return False
            if r.headers["content-type"] == "image/gif":
                return True
            return False
        if len(args) != 2:
            await ctx.send(embed=simple_embed(ctx.author, "Es müssen genau zwei Argumente übergeben werden", "Beispiel: `add hug hug_gif.gif`", color=discord.Color.red()))
            return
        category = args[0]
        if category not in self.cmds:
            await ctx.send(embed=simple_embed(ctx.author, "Die angegebene Kategorie ist nicht vorhanden", color=discord.Color.red()))
            return
        gif = args[1]
        if not is_gif(gif):
            await ctx.send(embed=simple_embed(ctx.author, "Die angegebene URL ist kein gültiges GIF.", color=discord.Color.red()))
            return
        self.addInJson(category, str(gif))
        await ctx.send(embed=simple_embed(ctx.author, "Das GIF wurde erfolgreich zur Kategorie hinzugefügt."))


    def readJson(self, name : str):
        try:
            with open(public_config.path + f'/json/{name}.json', 'r') as myfile:
                return json.loads(myfile.read())
        except FileNotFoundError:
            return []

    def addInJson(self, name : str, add):
        try:
            js = self.readJson(name)
            with open(public_config.path + f'/json/{name}.json', 'w') as myfile:
                js.append(add)
                json.dump(js, myfile)
        except FileNotFoundError:
            with open(public_config.path + f'/json/{name}.json', 'w') as file:
                file.write("[]")


    @hug.error
    @pat.error
    @feed.error
    @cuddle.error
    @kiss.error
    @poke.error
    @slap.error
    @bite.error
    async def on_command_error(self, ctx, error):
        embed = discord.Embed(title=type(error).__name__)
        embed.description = str(error)
        if isinstance(error, MemberNotFound):
            embed.description = f"{error.argument}\n\nist kein gültiger Benutzer."

        embed.color = discord.Color.red()
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Wholesome(bot))