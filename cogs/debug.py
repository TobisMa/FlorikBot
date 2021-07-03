import discord
from discord.ext import commands
import datetime
from helper_functions import *


class Debug(commands.Cog):
    """Commands zum debuggen"""

    def __init__(self, bot):
        self.bot = bot

    # @commands.command()
    # async def test(self, ctx, *, arg : discord.Member):
    #     """Test-command zum debuggen."""
    #     await ctx.send(arg.name)

    @commands.command()
    async def emotes(self, ctx):
        """Zeigt alle für Norman verfügbaren Emotes an
            nutze
            `getEmoji(bot, "emojiName")`
            um einen Emoji anhand seines Namens zu erhalten (devs only)"""
        e = discord.Embed(title="Emotes:")
        emotes = [f"<:{e.name}:{e.id}>" for e in self.bot.emojis]
        e.description = ''.join(emotes)
        e.timestamp = datetime.datetime.utcnow()
        e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
        m = await ctx.send(embed=e)
        # for i in range(min(20, len(emotes))):
        #    await m.add_reaction(emotes[i])



def setup(bot):
    bot.add_cog(Debug(bot))