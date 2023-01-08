import discord
from discord.ext import commands
from discord.ext.commands.errors import CommandNotFound
from discord.ext.commands.errors import MissingRequiredArgument
from asyncio import futures

import json
import requests
import datetime
from bs4 import BeautifulSoup

import config
from helper_functions import *
from bot import is_bot_dev

class AuthenticationError(commands.CheckFailure):
    pass

class NoAssignmentsError(commands.CheckFailure):
    pass

class MoodleApi:
    baseUrl:str
    data_format = "json"
    token:str
    header = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    def __init__(self,baseUrl,service="moodle_mobile_app"):
        if baseUrl[-1]=="/":
            baseUrl=baseUrl[:-1]
        self.baseUrl=baseUrl
        self.service=service

    def authenticate(self,username,password):
        url=f"{self.baseUrl}/login/token.php?username={username}&password={password}&service={self.service}"
        data=json.loads(requests.get(url).text)
        self.token=data.get("token")

    def getAssignments(self):
        func="mod_assign_get_assignments"
        url=f"{self.baseUrl}/webservice/rest/server.php?wstoken={self.token}&moodlewsrestformat={self.data_format}&wsfunction={func}"
        data:dict=json.loads(requests.get(url).text)
        assignments=[]
        for course in data.get("courses"):
            for assignment in course.get("assignments"):
                assignment.update({"course":course})
                a = Assignment(assignment,self)
                assignments.append(a)
        return assignments


class Assignment:
    def __init__(self, assignmentData,moodleApi:MoodleApi): 
        for key in assignmentData: 
            if "date" in key:
                if assignmentData[key] != 0:
                    assignmentData[key] = datetime.datetime.fromtimestamp(assignmentData[key])
            setattr(self, key, assignmentData[key]) 

        #Add url
        self.url=f"{moodleApi.baseUrl}/mod/assign/view.php?id={self.cmid}"

        #Add submission_status
        params=f"assignid={self.id}"
        url=f"{moodleApi.baseUrl}/webservice/rest/server.php?wstoken={moodleApi.token}&moodlewsrestformat={moodleApi.data_format}&wsfunction=mod_assign_get_submission_status&{params}"
        self.submission_status=json.loads(requests.get(url, headers=moodleApi.header).text)
            
def read_json(name : str):
    try:
        with open(config.path + f'/json/{name}.json', 'r') as myfile:
            return json.loads(myfile.read())
    except FileNotFoundError:
        return {}

class Paginator():
    def __init__(self, bot):
        self.page_count = 0
        self.pages = []
        self.bot = bot

    def add_page_embed(self, embed):
        self.page_count += 1
        self.pages.append(embed)

    def add_page(self, title, description, author, url, *fields):
        self.page_count += 1
        e = simple_embed(author=author, title=title, description=description)
        for f in fields:
            e.add_field(name=f[0], value=f[1], inline=False)
        self.pages.append(e)
        e.url = url

    def get_page(self, page):
        e = self.pages[page]
        e.set_footer(icon_url=e.footer.icon_url, text=f"{page + 1} / {self.page_count}")
        return e

    async def send(self, ctx, msg=None):
        if self.page_count == 0:
            raise NoAssignmentsError("Du hast keine offenen Aufgaben.")
        e = self.get_page(0)
        if msg == None:
            msg = await ctx.send(embed=e)
        else:
            await msg.edit(embed=e, content="")
        page = 0
        active = True
        right = "\u25B6"
        left = "\u25C0"
        await msg.add_reaction(left)
        await msg.add_reaction(right)
        while active:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=lambda _reaction, _user: _user == ctx.author and (_reaction.emoji == right or _reaction.emoji == left) and _reaction.message == msg)
                await reaction.remove(user)
                if reaction.emoji == left and page > 0:
                    page -= 1
                elif reaction.emoji == right and page < self.page_count - 1:
                    page += 1
                else:
                    continue
                e = self.get_page(page)
                await msg.edit(embed=e)
            except asyncio.exceptions.TimeoutError:
                active = False
        e.color = discord.Color.orange()
        await msg.edit(embed=e)

class Moodle(commands.Cog):
    """Commands für ein besseres Moodle"""
    def __init__(self, bot):
        self.config = read_json("user_config")
        self.bot = bot

    @commands.command()
    async def aufgaben(self, ctx):
        """Moodle-Aufgaben"""
        try:
            un = self.config[str(ctx.author.id)]["username"]
            pw = self.config[str(ctx.author.id)]["password"]
        except KeyError:
            raise AuthenticationError("Dein Benutzername und Passwort sind nicht gespeichert.")
        message = await ctx.send("`Benutzerdaten werden ausgelesen...`")
        api = MoodleApi(self.config["moodle_link"])
        await message.edit(content="`Benutzer wird authentifiziert..`")
        api.authenticate(un, pw)
        await message.edit(content="`Daten werden von Moodle abgefragt..`")
        a = api.getAssignments()
        await message.edit(content="`Daten werden verarbeitet..`")
        a.sort(key=lambda x: float('inf') if type(x.duedate) == int else datetime.datetime.timestamp(x.duedate))
        pages = Paginator(self.bot)
        for assignment in a:
            if (datetime.datetime.now() - datetime.datetime.fromtimestamp(assignment.timemodified)).days > 7:
                if type(assignment.duedate) == int or assignment.duedate < datetime.datetime.now():
                    continue
            description = BeautifulSoup(assignment.intro, "html5lib").get_text(separator="\n")
            if assignment.nosubmissions == 1:
                description = "**Diese Aufgabe benötigt keine Abgabe**\n" + description

            fields = []
            fields.append(["Kurs", assignment.course["shortname"]])
            date = "-" if assignment.duedate == 0 else assignment.duedate.strftime("%d.%m.%Y %H:%MUhr").replace(" 0", " ")
            fields.append(["Fälligkeitsdatum", date])
            fields.append(["Zuletzt bearbeitet am", datetime.datetime.fromtimestamp(assignment.timemodified).strftime("%d.%m.%Y %H:%MUhr").replace(" 0", " ")])
            files = []
            for i in assignment.introfiles:
                files.append(f'[{i["filename"]}]({i["fileurl"].replace("/webservice", "")})')
            if len(files) > 0:
                fields.append(["Dateien", '\n'.join(files)])
            
            attachments = []
            for i in assignment.introattachments:
                attachments.append(f'[{i["filename"]}]({i["fileurl"].replace("/webservice", "")})')
            if len(attachments) > 0:
                fields.append(["Anhänge", '\n'.join(attachments)])

            
            if assignment.duedate == 0 or assignment.duedate > datetime.datetime.now():
                pages.add_page(assignment.name, description, ctx.author, assignment.url, *fields)
        await pages.send(ctx, message)


    @aufgaben.error
    async def on_command_error(self, ctx, error):
        embed = discord.Embed(title=type(error).__name__)
        if isinstance(error, CommandNotFound) or isinstance(error, MissingRequiredArgument):
            return
        embed.description = str(error)
        embed.color = discord.Color.red()
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Moodle(bot))