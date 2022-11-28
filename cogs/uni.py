import discord
from discord.ext import commands
import datetime
from time import time
from helper_functions import *
import json
import config
from bot import is_bot_dev, on_command_error


class Uni(commands.Cog):
    """Commands zum debuggen"""

    def __init__(self, bot):
        self.bot = bot
        self.data = getData()

    def is_in_uni_server():
        async def predicate(ctx):
            possibleMember = ctx.author
            guild = ctx.bot.get_guild(config.UNI_GUILD)
            return possibleMember in guild.members

        return commands.check(predicate)

    @is_in_uni_server()
    @commands.command(aliases=["vls"])
    async def vorlesungsstand(self, ctx, *args):
        """Aktualisiert den Vorlesungsstand eines angegebenen Faches.
        Beispiel: `vls LA1 3.2.2 3.3` setzt den aktuellen Stand auf 3.3 und speichert, dass heute 3.2.2 bis 3.3 behandelt wurden.
        Möglichkeiten, den Befehl anzuwenden: \n``vls LA1 3.3``\n``vls LA1 3.2.2 3.3``\n``vls LA1 3.2.2 3.3 28.11.2022`v
        """
 
        if not 2 <= len(args) <= 4:
            await ctx.send(embed=simple_embed(
                ctx.author,
                "Es müssen genau 2-4 Argumente angegeben werden",
                "Beispiel:\n`vls LA1 3.3`\n`vls LA1 3.2.2 3.3`\n`vls LA1 3.2.2 3.3 28.11.2022`",
                color=discord.Color.red()
            ))
            return
        
        timestamp = time()
        
        if len(args) == 2:
            (subject, end) = args
            start = self.findLastEnd(subject)
        elif len(args) == 3:
            (subject, start, end) = args
        elif len(args) == 4:
            (subject, start, end, timestr) = args
            timestamp = datetime.datetime.strptime(timestr, '%d.%m.%Y').timestamp()
            
        if "subjects" not in self.data.keys() or subject not in self.data["subjects"]:
            await ctx.send(embed=simple_embed(ctx.author, "Ein Fehler ist aufgetreten", f"Das Fach ``{subject}`` ist nicht vorhanden", color=discord.Color.red()))
            return

        self.data["subjects"][subject]["current"] = (end, timestamp)
        self.data["subjects"][subject]["history"].append(
            {
                "time": timestamp,
                "start": start,
                "end": end
            }
        )
        await self.updateMessage()
        updateData(self.data)

    def findLastEnd(self, subject):
        if "subjects" not in self.data.keys() or subject not in self.data["subjects"]:
            return "0.0"
        
        if len(self.data["subjects"][subject]["history"]) == 0:
            return "0.0"
        
        current = self.data["subjects"][subject]["history"][0]
        for h in self.data["subjects"][subject]["history"]:
            if h["time"] > current["time"]:
                current = h
        
        return current["end"]  
    
      
    async def updateMessage(self):
        if "channel_id" in self.data.keys() and "message_id" in self.data.keys():
            msg = await self.bot.get_channel(self.data["channel_id"]).fetch_message(self.data["message_id"])

            if "subjects" not in self.data.keys():
                return

            e = discord.Embed(title="Vorlesungsstand", color=discord.Color.blurple())
            description = ""
            for subject in self.data["subjects"]:
                current = self.data['subjects'][subject]['current']
                timestring = datetime.datetime.fromtimestamp(current[1]).strftime('%d.%m.%Y') #  %H:%MUhr
                description += f"**{subject}**\n{current[0]}  -  (Stand {timestring})\n"
            e.description = description
            await msg.edit(embed=e)
        pass

    @is_bot_dev()
    @commands.command(aliases=["vlsadd"])
    async def addSubject(self, ctx, subject):
        """Fügt ein Fach der Vorlesungsstandsliste hinzu."""

        if subject in self.data:
            await ctx.send(embed=simple_embed(ctx.author, "Ein Fehler ist aufgetreten", f"Das Fach ``{subject}`` ist existiert bereits", color=discord.Color.red()))
            return
        if "subjects" not in self.data.keys():
            self.data["subjects"] = {}

        self.data["subjects"][subject] = {
            "current": ("0.0", time()),
            "history": [],
            "inactive": False
        }
        updateData(self.data)
        await self.updateMessage()
        await ctx.send(embed=simple_embed(ctx.author, f"Das Fach ``{subject}`` wurde erfolgreich hinzugefügt.", color=discord.Color.green()))

    @is_bot_dev()
    @commands.command(aliases=["vlsmsg"])
    async def vlsInformation(self, ctx):
        """Setzt den aktuellen Kanal als Vorlesungsstand-Informations-Kanal."""
        self.data["channel_id"] = ctx.channel.id
        msg = await ctx.send(embed=simple_embed(ctx.author, "Vorlesungsstand", color=discord.Color.green()))
        self.data["message_id"] = msg.id
        updateData(self.data)
        await self.updateMessage()


def updateData(data):
    with open(config.path + '/json/uniVL.json', 'w') as myfile:
        json.dump(data, myfile)


def getData():
    try:
        with open(config.path + '/json/uniVL.json', 'r') as myfile:
            return json.loads(myfile.read())
    except FileNotFoundError:
        return {}


async def setup(bot):
    await bot.add_cog(Uni(bot))
