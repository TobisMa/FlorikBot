import discord
from discord.ext import commands, tasks
from bs4 import BeautifulSoup
import public_config as config
import aiohttp

class FrierenStat(commands.Cog):

    URL = "https://myanimelist.net/anime/52991/Sousou_no_Frieren"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel = bot.get_channel(config.get("frieren_stat_channel"))
        self.last_value = self.getStat()
        if self.last_value is not None:
            self.last_value = float(self.last_value)
            self.checkStats.start()
        else:
            ... # handle appropiate

    @tasks.loop(minutes=60)
    async def checkStats(self):
        new_stat = self.getStat()
        try:
            new_stat = float(new_stat)
        except ValueError:
            return  # TODO handle more appropiate
        
        diff = new_stat - self.last_value
        if diff < 0:
            embed = discord.Embed(
                color=discord.Color.from_rgb(0xff, 0xad, 0x73),
                title="Frieren stats changed",
                description=f"Frieren ist im Rating auf {new_stat} gefallen ({diff}).",
            )
            embed.set_footer(icon="https://cdn.myanimelist.net/images/anime/1675/127908.jpg", text="Frieren")
            self.channel.send(embed=embed)

        elif diff > 0:
            embed = discord.Embed(
                color=discord.Color.from_rgb(0xff, 0xad, 0x73),
                title="Frieren stats changed",
                description=f"Frieren ist im Rating auf {new_stat} gestiegen ({diff})."
            )
            embed.set_footer(icon="https://cdn.myanimelist.net/images/anime/1675/127908.jpg", text="Frieren")
            self.channel.send(embed=embed)
        
        self.last_value = new_stat
        


    async def getStat(self):
        async with aiohttp.ClientSession() as sess:
            async with sess.get(FrierenStat.URL) as resp:
                if resp.ok:
                    soup = BeautifulSoup(resp.content, "html.parser")
                    stat = soup.find("div", class_="score-label").text
                    return stat


