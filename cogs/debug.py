import discord
from discord.ext import commands
import datetime
from discord import app_commands
import config

class Debug(commands.Cog):
    """Commands zum debuggen"""

    def __init__(self, bot):
        self.bot = bot

    # @commands.command()
    # async def test(self, ctx):
    #     """Test-command zum debuggen."""
    #     a = await ctx.bot.tree.sync(guild=ctx.guild)
    #     await ctx.send(a)

    @app_commands.command(name="emotes", description="test debug command")
    async def emotes(self, interaction: discord.Interaction):
        """Zeigt alle für Norman verfügbaren Emotes an
            nutze
            `getEmoji(bot, "emojiName")`
            um einen Emoji anhand seines Namens zu erhalten (devs only)"""
        e = discord.Embed(title="Emotes:")
        emotes = [f"<:{e.name}:{e.id}>" for e in self.bot.emojis]
        e.description = ''.join(emotes)
        e.timestamp = datetime.datetime.now()
        e.set_footer(text=interaction.user.name, icon_url=interaction.user.avatar)
        await interaction.response.send_message(embed=e)
        # m = await ctx.send(embed=e)
        # for i in range(min(20, len(emotes))):
        #    await m.add_reaction(emotes[i])



async def setup(bot):
    if(config.GUILDS):
        await bot.add_cog(Debug(bot), guilds=config.GUILDS)
    else:
        await bot.add_cog(Debug(bot))