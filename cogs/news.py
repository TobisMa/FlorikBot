import asyncio
import contextlib
import datetime
import json

import aiohttp
import discord
from discord import embeds
from discord.ext import commands, tasks

import config
from bot import on_command_error
from helper_functions import simple_embed


class Nachrichten(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.old_news_ids = self.get_data()
        self.news_loop.start()

    @tasks.loop(seconds=300)
    async def news_loop(self):
        news = await self.get_news()
        for e in news:
            channel = self.bot.get_channel(config.NEWS_CHANNEL_ID)
            await channel.send(embed=e)

    async def get_news(self):
        url = "https://www.tagesschau.de/api2/news/?ressort=inland&regions=11"
        embed_list = []
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status == 200 and len(await r.text()) > 0:
                    data = json.loads(await r.text())
                    data["news"].reverse()
                    for news in data["news"]:
                        date = datetime.datetime.fromisoformat(news["date"])
                        # date_formatted = date.strftime("%d.%m.%Y %H:%M")
                        if news["externalId"] not in self.old_news_ids:
                            self.old_news_ids.append(news["externalId"])

                            e = discord.Embed()
                            e.color = discord.Color.dark_teal()
                            e.timestamp = date
                            e.title = news["title"]
                            e.url = news["shareURL"]
                            e.description = news["firstSentence"]
                            with contextlib.suppress(BaseException):   # still no idea what contexlib.suppress is
                                e.set_image(
                                    url=news["teaserImage"]["videowebl"]["imageurl"])
                            embed_list.append(e)
                    self.save_data()
        return embed_list

    def get_data(self):
        try:
            with open(config.path + '/json/news.json', 'r') as myfile:
                return json.loads(myfile.read())
        except FileNotFoundError:
            return []

    def save_data(self):
        with open(config.path + '/json/news.json', 'w') as myfile:
            json.dump(self.old_news_ids, myfile)

    @news_loop.before_loop
    async def before_news_loop(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simple_embed(self.bot.user, "Nachrichten loop start", color=discord.Color.green()))

    @news_loop.after_loop
    async def after_news_loop(self):
        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simple_embed(self.bot.user, "Nachrichten loop stopped.", color=discord.Color.orange()))
        await asyncio.sleep(60)
        self.news_loop.restart()

    @news_loop.error
    async def news_loop_error(self, error):
        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simple_embed(self.bot.user, "Nachrichten error", color=discord.Color.orange()))
        await on_command_error(self.bot.get_channel(config.LOG_CHANNEL_ID), error)


async def setup(bot):
    await bot.add_cog(Nachrichten(bot))
