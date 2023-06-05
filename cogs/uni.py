import hashlib
import os
import traceback
import discord
from discord.ext import commands, tasks
import datetime
from time import time
from helper_functions import simple_embed
import json
import config
from bot import is_bot_dev, on_command_error
from discord import app_commands
from typing import List, Optional

from PyPDF2 import PdfReader
import re
from datetime import datetime
import locale
discord_timestamp = "<t:{timestamp}:D> (<t:{timestamp}:R>)"

class Uni(commands.Cog):
    """Commands zum debuggen"""

    def __init__(self, bot):
        self.bot = bot
        self.data = get_data()
        self.update_assignments.start()
        
    def cog_unload(self):
        self.update_assignments.cancel()

    @staticmethod
    def is_in_uni_server():
        async def predicate(ctx):
            possible_member = ctx.author
            guild = ctx.bot.get_guild(config.UNI_GUILD)
            if possible_member in guild.members:
                return True
            return "students" in get_data().keys() and ctx.author.id in get_data()["students"]

        return commands.check(predicate)
    
    @staticmethod
    def is_in_uni_server_interaction_check():
        async def predicate(interaction: discord.Interaction) -> bool:
            guild = interaction.client.get_guild(config.UNI_GUILD)
            if interaction.user in guild.members:
                return True
            elif "students" in get_data().keys() and interaction.user.id in get_data()["students"]:
                return True
            else:
                e = simple_embed(interaction.user, "Du hast keine Berechtigung diesen Command auszuführen.", color=discord.Color.red())
                await interaction.response.send_message(embede=e, ephemeral=True)
                return False 
        
        return app_commands.check(predicate)

   
    
    @app_commands.command(name="vorlesungsstand", description="Zeigt den momentanen Vorlesungsstand an")
    async def get_vorlesungsstand_nosync(self, interaction: discord.Interaction):
        if "subjects" not in self.data.keys():
            e = simple_embed(interaction.user, "Es stehen keine Daten zur Verfügung", color=discord.Color.red())
            await interaction.response.send_message(embed=e, ephemeral=True)
            return

        e = discord.Embed(title="Vorlesungsstand", color=discord.Color.blurple())
        description = ""
        for subject in self.data["subjects"]:
            current = self.data['subjects'][subject]['current']
            timestring = datetime.datetime.fromtimestamp(current[1]).strftime('%d.%m.%Y') #  %H:%MUhr
            description += f"**{subject}**\n{current[0]}  -  (Stand {timestring})\n\n"
        e.description = description
        await interaction.response.send_message(embed=e, ephemeral=True)


    async def update_subject_autocomplete(self,interaction: discord.Interaction,current: str,) -> List[app_commands.Choice[str]]:
        choices = [x for x in self.data["subjects"] if not self.data["subjects"][x]["inactive"]]
        return [
            app_commands.Choice(name=choice, value=choice) for choice in choices if current.lower() in choice.lower()
        ]
    

    @is_in_uni_server_interaction_check()
    @app_commands.command(name="update_subject", description="Aktualisiert den Stand eines angegebenen Fachs")
    @app_commands.describe(
        subject="Fach, welches aktualisiert werden soll",
        new_state="Neuer Stand des Faches", 
        timestamp="Zeitpunkt der Aktualisierung im Format dd.mm.yyyy"
    )
    @app_commands.autocomplete(subject=update_subject_autocomplete)
    @app_commands.rename(new_state="neuer_stand", subject="fach", timestamp="zeitpunkt")
    async def update_subject(self, interaction: discord.Interaction, subject: str, new_state: str, timestamp: Optional[str]):
        if "subjects" not in self.data.keys():
            e = simple_embed(interaction.user, "Es stehen keine Fächer zur Verfügung, die aktualisiert werden können", color=discord.Color.red())
            await interaction.response.send_message(embed=e, ephemeral=True)
            return
        if subject not in self.data["subjects"]:
            e = simple_embed(interaction.user, f"Das Fach `{subject}` existiert nicht", color=discord.Color.red())
            await interaction.response.send_message(embed=e, ephemeral=True)
            return
        if self.data["subjects"][subject]["inactive"]:
            e = simple_embed(interaction.user, f"Das Fach `{subject}` ist nicht aktiv", color=discord.Color.red())
            await interaction.response.send_message(embed=e, ephemeral=True)
            return
        if(timestamp):
            try:
                timestamp = datetime.datetime.strptime(timestamp, '%d.%m.%Y').timestamp()
            except ValueError as ex:
                e = simple_embed(interaction.user, ex.args[0], color=discord.Color.red())
                await interaction.response.send_message(embed=e, ephemeral=True)
                return
        else:
            timestamp = time()
             
        start = self.findLastEnd(subject)
        
        self.data["subjects"][subject]["current"] = (new_state, timestamp)
        self.data["subjects"][subject]["history"].append(
            {
                "time": timestamp,
                "start": start,
                "end": new_state
            }
        )
        await self.update_message()
        update_data(self.data)
        
        e = simple_embed(interaction.user, f"Das Fach {subject} wurde erfolgreich aktualisiert", color=discord.Color.green())
        await interaction.response.send_message(embed=e, ephemeral=True)
        

    @is_in_uni_server()
    @commands.command(aliases=["vls"])
    async def vorlesungsstand(self, ctx, *args):
        """Aktualisiert den Vorlesungsstand eines angegebenen Faches.
        Beispiel: `vls LA1 3.2.2 3.3` setzt den aktuellen Stand auf 3.3 und speichert, dass heute 3.2.2 bis 3.3 behandelt wurden.
        Möglichkeiten, den Befehl anzuwenden: \n``vls LA1 3.3``\n``vls LA1 3.2.2 3.3``\n``vls LA1 3.2.2 3.3 28.11.2022`
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
        await self.update_message()
        update_data(self.data)
        await ctx.message.add_reaction("\N{White Heavy Check Mark}")
        

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
    
      
    async def update_message(self):
        if "channel_id" not in self.data.keys() or "message_id" not in self.data.keys():
            return
        msg = await self.bot.get_channel(self.data["channel_id"]).fetch_message(self.data["message_id"])

        if "subjects" not in self.data.keys():
            return

        e = discord.Embed(title="Vorlesungsstand", color=discord.Color.blurple())
        description = ""
        for subject in self.data["subjects"]:
            if self.data['subjects'][subject]['inactive']:
                continue
            current = self.data['subjects'][subject]['current']
            timestring = datetime.datetime.fromtimestamp(current[1]).strftime('%d.%m.%Y') #  %H:%MUhr
            description += f"**{subject}**\n{current[0]}  -  (Stand {timestring})\n\n"
        e.description = description
        await msg.edit(embed=e)

    @is_bot_dev()
    @commands.command(aliases=["vlsadd"])
    async def addSubject(self, ctx, subject):
        """Fügt ein Fach der Vorlesungsstandsliste hinzu."""

        if "subjects" not in self.data.keys():
            self.data["subjects"] = {}
        if subject in self.data["subjects"]:
            await ctx.send(embed=simple_embed(ctx.author, "Ein Fehler ist aufgetreten", f"Das Fach ``{subject}`` ist existiert bereits", color=discord.Color.red()))
            return

        self.data["subjects"][subject] = {
            "current": ("0.0", time()),
            "history": [],
            "inactive": False
        }
        update_data(self.data)
        await self.update_message()
        await ctx.send(embed=simple_embed(ctx.author, f"Das Fach ``{subject}`` wurde erfolgreich hinzugefügt.", color=discord.Color.green()))


    @is_bot_dev()
    @commands.command(aliases=["vlsdeactivate"])
    async def deactivateSubject(self, ctx, subject):
        """Deaktiviert ein Fach."""

        if "subjects" not in self.data.keys():
            self.data["subjects"] = {}
        if subject not in self.data["subjects"]:
            await ctx.send(embed=simple_embed(ctx.author, "Ein Fehler ist aufgetreten", f"Das Fach ``{subject}`` ist existiert nicht", color=discord.Color.red()))
            return

        self.data['subjects'][subject]['inactive'] = True;
        update_data(self.data)
        await self.update_message()
        await ctx.send(embed=simple_embed(ctx.author, f"Das Fach ``{subject}`` wurde erfolgreich deaktiviert.", color=discord.Color.green()))



    @is_bot_dev()
    @commands.command(aliases=["addstudent"])
    async def addStudent(self, ctx, student: discord.User):
        """Gibt einem Nutzer Berechtigungen, Unicommands zu nutzen"""
        if "students" not in self.data.keys():
            self.data["students"] = []

        if student in self.data["students"]:
            await ctx.send(embed=simple_embed(ctx.author, "Ein Fehler ist aufgetreten", f"Der Nutzer ``{student.name}`` hat bereits Berechtigungen", color=discord.Color.red()))
            return

        self.data["students"].append(student.id)
        update_data(self.data)
        await self.update_message()
        await ctx.send(embed=simple_embed(ctx.author, f"Der Nutzer ``{student.name}`` wurde erfolgreich hinzugefügt.", color=discord.Color.green()))


    @is_in_uni_server()
    @commands.command(aliases=["vlsmsg"])
    async def vlsInformation(self, ctx):
        """Setzt den aktuellen Kanal als Vorlesungsstand-Informations-Kanal."""
        self.data["channel_id"] = ctx.channel.id
        msg = await ctx.send(embed=simple_embed(ctx.author, "Vorlesungsstand", color=discord.Color.green()))
        self.data["message_id"] = msg.id
        update_data(self.data)
        await self.update_message()


    async def send_to_channel(self, file, date, channel_id, ver=1):
        filename = file.split("/")[-1].split("\\")[-1]
        channel = self.bot.get_channel(channel_id)
        f = discord.File(file)
        if ver > 1:
            await channel.send(f"``{filename}`` wurde aktualisiert. Version: ``{ver}``, Abgabedatum {date}", file=f)
        await channel.send(f"Neues Übungsblatt: ``{filename}``, Abgabe am {date}", file=f)


    @tasks.loop(hours=2)
    async def update_assignments(self):
        print("checking")
        # load files (https://github.com/Garmelon/PFERD)
        os.chdir(config.path)
        os.popen("loadAssignments.sh").read()
        change = False
        with open(config.path + "/json/assignments.json", "r", encoding='utf-8') as f:
            data = json.load(f)["assignments"]

        for subject in data["subjects"].keys():
            path = data["subjects"][subject]["path"] + os.sep
            # iterate over pdf files in assignment folder
            for _, _, files in os.walk(path):
                for file in files:
                    
                    if not file.endswith(".pdf"):
                        continue
                    
                    # check whether file is already in data
                    if file not in data["subjects"][subject]["assignments"].keys():
                        date = self.get_due_date(
                            path + file, 
                            data["subjects"][subject]["pattern"],
                            data["subjects"][subject]["datetime_pattern"]
                        )
                        
                        with open(path + file, "rb") as f:
                            filehash = hashlib.sha1(f.read()).hexdigest()

                        data["subjects"][subject]["assignments"][file] = {
                            "version": 1, 
                            "last_change": datetime.now().timestamp(), 
                            "hash": filehash
                        }
                        await self.send_to_channel(path + file, date, data["subjects"][subject]["channel_id"])
                        change = True

                    else:
                        # # check if file hash has changed
                        with open(path + file, "rb") as f:
                            filehash = hashlib.sha1(f.read()).hexdigest()

                        if filehash != data["assignments"][file]["hash"]:
                            date = self.get_due_date(
                                path + file, 
                                data["subjects"][subject]["pattern"],
                                data["subjects"][subject]["datetime_pattern"]
                            )
                            data["subjects"][subject]["assignments"][file]["version"] += 1
                            data["subjects"][subject]["assignments"][file]["last_change"] = datetime.now().timestamp()
                            data["subjects"][subject]["assignments"][file]["hash"] = filehash

                            await self.send_to_channel(
                                path + file,
                                date,
                                data["subjects"][subject]["assignments"][file]["version"], 
                                data["subjects"][subject]["channel_id"]
                            )
                            change = True

        # update data file
        if change:
            with open(config.path + "/json/assignments.json", "w", encoding='utf-8') as f:
                json.dump(data, f, indent=4)

    @update_assignments.before_loop
    async def before_printer(self):
        await self.bot.wait_until_ready()
        
        
    def get_due_date(self, path, time_pattern, datetime_pattern):
        locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')
        pdf_reader = PdfReader(path)
        
        page_1 = pdf_reader.pages[0]
        lines = page_1.extract_text().splitlines()
        for line in lines:
            if re.match(time_pattern, line):
                date = re.match(time_pattern, line).group(1)
                time = re.match(time_pattern, line).group(2)
                actual_date = datetime.strptime(date + " " + time, datetime_pattern)
                # set year if none is specified
                if actual_date.year < datetime.now().year:
                    actual_date = actual_date.replace(year=datetime.now().year)
                # fix year if date is in the next year (e.g. 1.1.20xx)
                if actual_date.timestamp() < datetime.now().timestamp():
                    actual_date = actual_date.replace(year=datetime.now().year + 1)
                return discord_timestamp.format(timestamp=int(actual_date.timestamp()))
        
def update_data(data):
    with open(config.path + '/json/uniVL.json', 'w') as myfile:
        json.dump(data, myfile, indent=4)


def get_data():
    try:
        with open(config.path + '/json/uniVL.json', 'r') as myfile:
            return json.loads(myfile.read())
    except FileNotFoundError:
        return {}


async def setup(bot):
    if not os.path.exists(config.path + "/json/assignments.json"):
        with open(config.path + "/json/assignments.json", "w") as f:
            assignment_base = {
                "assignments":{
                    "subjects" : {
                        # "dummy" : {
                        #     "path" : "",
                        #     "pattern": "",
                        #     "datetime_pattern": "",
                        #     "channel_id": 0
                        #     "assignments" : {
                        #         "B1": {
                        #             "hash": "",
                        #             "version": 0,
                        #             "last_change": 0
                        #         }
                        #     }
                        # }
                    }
                }
            }
            f.write(json.dumps(assignment_base, indent=4))
            
    if(config.GUILDS):
        await bot.add_cog(Uni(bot), guilds=config.GUILDS)
    else:
        await bot.add_cog(Uni(bot))
