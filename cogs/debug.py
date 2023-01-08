import discord
from discord.ext import commands
import datetime

# Define a simple View that gives us a confirmation menu

        
class Dropdown(discord.ui.Select):
    def __init__(self):

        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(label='Red', description='Your favourite colour is red', emoji='🟥'),
            discord.SelectOption(label='Green', description='Your favourite colour is green', emoji='🟩'),
            discord.SelectOption(label='Blue', description='Your favourite colour is blue', emoji='🟦'),
        ]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder='Choose your favourite colour...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # Use the interaction object to send a response message containing
        # the user's favourite colour or choice. The self object refers to the
        # Select object, and the values attribute gets a list of the user's
        # selected options. We only want the first one.
        await interaction.response.send_message(f'Your favourite colour is {self.values[0]}')

class Debug(commands.Cog):
    """Commands zum debuggen"""

    def __init__(self, bot):
        self.bot = bot

    # @commands.command()
    # async def test(self, ctx):
    #     """Test-command zum debuggen."""

    #     await ctx.send("test1")

    @commands.command()
    async def emotes(self, ctx):
        """Zeigt alle für Norman verfügbaren Emotes an
            nutze
            `getEmoji(bot, "emojiName")`
            um einen Emoji anhand seines Namens zu erhalten (devs only)"""
        e = discord.Embed(title="Emotes:")
        emotes = [f"<:{e.name}:{e.id}>" for e in self.bot.emojis]
        e.description = ''.join(emotes)
        e.timestamp = datetime.datetime.now()
        e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar)
        m = await ctx.send(embed=e)
        # for i in range(min(20, len(emotes))):
        #    await m.add_reaction(emotes[i])



async def setup(bot):
    await bot.add_cog(Debug(bot))