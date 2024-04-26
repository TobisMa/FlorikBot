import hashlib
import os
import discord
from discord.ext import commands, tasks
from time import time
import json
import public_config
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
   

    # async def update_subject_autocomplete(self,interaction: discord.Interaction,current: str,) -> List[app_commands.Choice[str]]:
    #     choices = [x for x in self.data["subjects"] if not self.data["subjects"][x]["inactive"]]
    #     return [
    #         app_commands.Choice(name=choice, value=choice) for choice in choices if current.lower() in choice.lower()
    #     ]

    async def send_to_channel(self, file, date, channel_id, ver=1):
        filename = file.split("/")[-1].split("\\")[-1]
        channel = self.bot.get_channel(channel_id)
        f = discord.File(file)
        if ver > 1:
            date_str = f", Abgabedatum {date}" if date else ""
            await channel.send(f"``{filename}`` wurde aktualisiert. Version: ``{ver}``{date_str}", file=f)
            return
        date_str = f", Abgabe am {date}" if date else ""
        await channel.send(f"Neues Übungsblatt: ``{filename}``{date_str}", file=f)


    @tasks.loop(hours=2)
    async def update_assignments(self):
        # load files (https://github.com/Garmelon/PFERD)
        os.chdir(public_config.path)
        os.popen("sh ../assignment-data/loadAssignments.sh").read()
        change = False
        with open(public_config.path + "/json/assignments.json", "r", encoding='utf-8') as f:
            data = json.load(f)["assignments"]

        for subject in data["subjects"].keys():
            path = data["subjects"][subject]["path"] + os.sep
            
            locale = "de_DE.UTF-8"
            if "locale" in data["subjects"][subject]:
                locale = data["subjects"][subject]["locale"]
            # iterate over pdf files in assignment folder
            for root, dirs, files in os.walk(path):
                root += os.sep
                for file in files:
                    
                    if not file.endswith(".pdf"):
                        continue
                    
                    # check whether file is already in data
                    if file not in data["subjects"][subject]["assignments"].keys():
                        date = self.get_due_date(
                            root + file, 
                            data["subjects"][subject]["pattern"],
                            data["subjects"][subject]["datetime_pattern"],
                            locale
                        )
                        
                        with open(root + file, "rb") as f:
                            filehash = hashlib.sha1(f.read()).hexdigest()

                        data["subjects"][subject]["assignments"][file] = {
                            "version": 1, 
                            "last_change": datetime.now().timestamp(), 
                            "hash": filehash
                        }
                        await self.send_to_channel(root + file, date, data["subjects"][subject]["channel_id"])
                        change = True

                    else:
                        # # check if file hash has changed
                        with open(root + file, "rb") as f:
                            filehash = hashlib.sha1(f.read()).hexdigest()

                        if filehash != data["subjects"][subject]["assignments"][file]["hash"]:
                            date = self.get_due_date(
                                root + file, 
                                data["subjects"][subject]["pattern"],
                                data["subjects"][subject]["datetime_pattern"],
                                locale
                            )
                            data["subjects"][subject]["assignments"][file]["version"] += 1
                            data["subjects"][subject]["assignments"][file]["last_change"] = datetime.now().timestamp()
                            data["subjects"][subject]["assignments"][file]["hash"] = filehash

                            await self.send_to_channel(
                                root + file,
                                date,
                                data["subjects"][subject]["channel_id"],
                                data["subjects"][subject]["assignments"][file]["version"] 
                            )
                            change = True

        # update data file
        if change:
            with open(public_config.path + "/json/assignments.json", "w", encoding='utf-8') as f:
                new_data = {"assignments": data}
                json.dump(new_data, f, indent=4)
            
    @update_assignments.before_loop
    async def before_assignment_loop(self):
        await self.bot.wait_until_ready()
        
        
    def get_due_date(self, path, time_pattern, datetime_pattern, locale_="de_DE.UTF-8"):
        try:
            locale.setlocale(locale.LC_TIME, locale_)
            pdf_reader = PdfReader(path)
            for page in pdf_reader.pages:
                lines = page.extract_text().splitlines()
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
        except ValueError as e:
            return None
        
def update_data(data):
    public_config.dump("assignments.json", data)


def get_data():
    return public_config.load("assignments.json")


async def setup(bot):
    if get_data() == {}:
        update_data({
            "assignments": {
                "subjects": {}
            }
        })

        await bot.add_cog(Uni(bot))
        print("Cog loaded: Uni")

      
# structure is:  
"""
    "subject_name" : {
        "path" : "",
        "pattern": "",              # pattern to find the time line
        "datetime_pattern": "",     
        "locale": "",
        "channel_id": 0
        "assignments" : {
            "B1": {
                "hash": "",
                "version": 0,
                "last_change": 0
            }
        }
    }
"""