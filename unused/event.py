import discord
from discord.ext import commands
from asyncio import futures
import asyncio

import json
import random

import discord
from discord.ext import commands
from discord.ext.commands.errors import CommandError
from discord.ext.commands.errors import CheckFailure, CommandNotFound, NotOwner
from discord.ext.commands.errors import MissingRequiredArgument

import config
from helper_functions import *


class NoParticipant(commands.CheckFailure):
    pass


class EventNotRunning(commands.CheckFailure):
    pass


class EventError(commands.CheckFailure):
    pass


def is_participating():
    async def predicate(ctx):
        if ctx.author.id in get_data("event_config")["participants"]:
            return True
        raise NoParticipant("Du bist kein Teilnehmer.")
    return commands.check(predicate)


def event_started():
    async def predicate(ctx):
        if get_data("event_config")["is_running"]:
            return True
        raise EventNotRunning("Das Wortspiel läuft noch nicht.")
    return commands.check(predicate)


class Event(commands.Cog):
    """Event-Spezifische Commands"""

    def __init__(self, bot):
        self.bot = bot
        self.data = get_data("event")
        self.config = get_data("event_config")
        self.channel = 804652343428644874

    def update_data(self):
        self.data = get_data("event")
        self.config = get_data("event_config")

    @commands.Cog.listener()
    async def on_message(self, message):
        if not(message.channel.id == 693062821650497600 or message.channel.id == 707325921245266011):
            return
        if message.author == self.bot.user:
            return
        if get_data("event_config")["words_complete"]:
            changed = False
            if message.author.id in self.config["remaining"]:
                user = message.author.id
                if not self.data[str(user)]["word1_found"]:
                    w1 = self.data[str(user)]["word1"]
                    if w1.lower() in message.content.lower():
                        self.data[str(user)]["word1_found"] = True
                        await message.channel.send(embed=simple_embed(message.author, "Verbotenes Wort!", f"`{w1}` war eines deiner verbotenen Worte!", color=discord.Color.dark_purple()))
                        changed = True
                if not self.data[str(user)]["word2_found"]:
                    w2 = self.data[str(user)]["word2"]
                    if w2.lower() in message.content.lower():
                        self.data[str(user)]["word2_found"] = True
                        await message.channel.send(embed=simple_embed(message.author, "Verbotenes Wort!", f"`{w2}` war eines deiner verbotenen Worte!", color=discord.Color.dark_purple()))
                        changed = True
                if not self.data[str(user)]["phrase_found"]:
                    ph = self.data[str(user)]["phrase"]
                    if ph.lower() in message.content.lower():
                        self.data[str(user)]["phrase_found"] = True
                        await message.channel.send(embed=simple_embed(message.author, "Verbotenes Wort!", f"`{ph}` war deine verbotene Phrase!", color=discord.Color.dark_purple()))
                        changed = True

                if (self.data[str(user)]["word1_found"] and self.data[str(user)]["word2_found"] and self.data[str(user)]["phrase_found"]):
                    self.data[str(user)]["placement"] = len(self.config["remaining"])
                    self.config["remaining"].remove(user)
                    e = simple_embed(message.author, "Ausgeschieden!", f"Du bist ausgeschieden und belegst somit Platz `{self.data[str(user)]['placement']}`", color=discord.Color.dark_purple())
                    if self.data[str(user)]["placement"] == len(self.config["participants"]):
                        e.description += "\nDu bist ziemlich vorhersehbar :)"
                    await message.channel.send(embed=e)

                    for p in self.config["remaining"]:
                        self.data[str(p)]["placement"] = len(self.config["remaining"])
                    changed = True

            if changed:
                save_data("event", self.data)
                save_data("event_config", self.config)
                await self.update_event_message()
                if len(self.config["remaining"]) == 0:
                    self.config["is_running"] = False
                    self.config["words_complete"] = False
                save_data("event_config", self.config)
                self.update_data()
            


    @commands.is_owner()
    @commands.command()
    async def start(self, ctx, *args):

        if get_data("event_config")["is_running"]:
            raise EventError("Event läuft schon")
        self.update_data()
        self.data = {}
        self.config["is_running"] = True
        self.config["remaining"] = list(self.config["participants"])

        # create event message
        e = discord.Embed(title="Das Wortspiel hat begonnen.")
        e.description = "```fix\nAlle Teilnehmer haben eine Nachricht von Norman bekommen, in der erklärt wird, was nun zu tun ist."
        e.description += "\nWenn Wörter für jeden Teilnehmer gewählt wurden, beginnt das Spiel.```"
        e.description += "\nMomentan wird darauf gewartet, dass alle Teilnehmer ihre Wörter bekommen."
        e.timestamp = datetime.datetime.utcnow()
        e.set_footer(text=self.bot.user.name,
                     icon_url=self.bot.user.avatar)

        e.color = discord.Color.dark_purple()
        event_msg = await self.bot.get_channel(self.config["channel_id"]).send(embed=e)
        self.config["event_message"] = event_msg.id

        data = self.data
        # match participants
        participants = self.config["participants"]
        if len(participants) <= 1:
            raise EventError("Nicht genügend Teilnehmer")
        unmatched = list(self.config["participants"])  # copy
        # create empty dicts
        for p in participants:
            data[str(p)] = {}
            data[str(p)]["word1"] = ""
            data[str(p)]["word2"] = ""
            data[str(p)]["phrase"] = ""
            data[str(p)]["word1_found"] = False
            data[str(p)]["word2_found"] = False
            data[str(p)]["phrase_found"] = False
            data[str(p)]["placement"] = len(participants)

        for p in participants:
            author = random.choice(unmatched)
            while author == p:
                author = random.choice(unmatched)
            data[str(p)]["word_author"] = author
            data[str(author)]["is_author_for"] = p
            unmatched.remove(author)

        # send instruction messagess
        for p in participants:
            e = discord.Embed(title="Das Wortspiel",
                              color=discord.Color.dark_purple())
            e.description = """```md
KURZEINFÜHRUNG
---
Jede Person bekommt
1. < Eine Wortphrase > (quasi ein Satz, beispielsweise "Schiess dir doch ins Knie")
2. < ein einzelnes Wort > (Ein Wort, allerdings kein alltägliches wie "allerdings", "nicht" oder so)
3. < noch ein einzelnes Wort > (siehe 2.)
Die Wörter / Phrasen sollen nicht allzu schwer, aber auch nicht allzu leicht sein, es soll also am besten etwas sein, dass eine Person unbewusst oft sagt (beziehungsweise schreibt) :)

DURCHSUCHTE NACHRICHTEN
---
Sämtliche geschriebene Nachrichten in #textchat und #shitpost werden durchsucht, die anderen Channel nicht.
Groß- und Kleinschreibung ist egal, aber falls ein < Wort > oder eine < Phrase > in der Nachricht vorkommt, wird diese von Norman in #wortspiel aufgedeckt und ist nicht mehr gültig.

ZIEL DES SPIELS
---
Spaß haben oder so.
Eine Person "gewinnt", wenn sie die letzte Person ist, die noch mindestens ein < Wort > oder < eine Phrase > übrig, also noch nicht erwähnt hat.
```"""

            e.timestamp = datetime.datetime.utcnow()
            e.set_footer(text=self.bot.user.name,
                         icon_url=self.bot.user.avatar)
            await self.bot.get_user(p).send(embed=e)

            e.title = "Zuteilung der Wörter"
            e.description = "Es sollte, bis sämtliche Wörter einer Person aufgedeckt wurden, **geheim** bleiben, wer die Wörter ausgesucht hat, also bitte verrate niemandem, wen du hast, um den Spielspaß zu gewähren."
            e.description += f"\nDir wurde {self.bot.get_user(data[str(p)]['is_author_for']).mention} zugeteilt!"
            e.description += f"\nBenutze den Command **{config.PREFIX}words**, um deiner Person Wörter zuzuteilen"
            e.description += f"\n(Wenn du den Command aufrufst, wirst du durch die beiden Wörter und die Phrase geführt, starten musst du nur mit **{config.PREFIX}words**)"
            await self.bot.get_user(p).send(embed=e)

        save_data("event_config", self.config)
        save_data("event", data)
        self.update_data()

    @is_participating()
    @event_started()
    @commands.dm_only()
    @commands.command()
    async def words(self, ctx):
        self.update_data()
        author = self.data[str(ctx.author.id)]
        user = self.data[str(ctx.author.id)]["is_author_for"]
        if not(self.data[str(user)]["word1"] == "" or self.data[str(user)]["word2"] == "" or self.data[str(user)]["phrase"] == ""):
            raise EventError(
                f"Die Einrichtung für den Teilnehmer {self.bot.get_user(user).mention} ist bereits abgeschlossen.")

        async def choose_word(title, single_word):
            e = discord.Embed(title=title, color=discord.Color.purple())
            e.description = f"Gebe bitte (in den nächsten 180s) {title} ein.\n(Groß- und Kleinschreibung ist egal)"
            e.timestamp = datetime.datetime.utcnow()
            e.set_footer(text=self.bot.user.name,
                         icon_url=self.bot.user.avatar)

            await ctx.send(embed=e)
            try:
                m = await self.bot.wait_for('message', check=lambda m: m.channel == ctx.channel and m.author == ctx.author, timeout=180)
                if single_word:
                    if len(m.content.split()) != 1:
                        raise ValueError
                return m.content
            except asyncio.exceptions.TimeoutError:
                await ctx.send(embed=simple_embed(ctx.author, "Timeout", "Bitte versuche es erneut.", color=discord.Color.red()))
            except ValueError:
                await ctx.send(embed=simple_embed(ctx.author, "Kein Wort", "Du darfst nur ein Wort eingeben, bitte versuche es erneut.", color=discord.Color.red()))
            return ""
        w1 = await choose_word("Wort 1", True)
        if w1 == "":
            return
        w2 = await choose_word("Wort 2", True)
        if w2 == "":
            return
        phrase = await choose_word("die Phrase", False)
        if phrase == "":
            return

        e = discord.Embed(title="Kontrollübersicht",
                          color=discord.Color.purple())
        e.description = "Falls du mit einem Wort/der Phrase unzufrieden bist, hast du **jetzt** in den nächsten 60s die Möglichkeit, abzubrechen und den Command neu auszuführen."
        e.description += "\nFalls nicht, wird deine Auswahl in 60s automatisch **unwiderruflich** gespeichert."
        e.description += f"\n`Wort 1: {w1}`"
        e.description += f"\n`Wort 2: {w2}`"
        e.description += f"\n`Phrase: {phrase}`"
        e.timestamp = datetime.datetime.utcnow()
        e.set_footer(text=self.bot.user.name,
                     icon_url=self.bot.user.avatar)
        m = await ctx.send(embed=e)
        cross = "\N{CROSS MARK}"
        await m.add_reaction(cross)
        try:
            await self.bot.wait_for('reaction_add', timeout=60.0, check=lambda _reaction, _user: _user == ctx.message.author and _reaction.emoji == cross and _reaction.message == m)
            await ctx.send(embed=simple_embed(ctx.author, "Deine Auswahl wurde gelöscht",
                         "Bitte führe den Command erneut aus.", color=discord.Color.dark_red()))
        except asyncio.TimeoutError:
            self.data[str(user)]["word1"] = w1
            self.data[str(user)]["word2"] = w2
            self.data[str(user)]["phrase"] = phrase
            save_data("event", self.data)
            self.update_data()
            await ctx.send(embed=simple_embed(ctx.author, "Deine Auswahl wurde gespeichert.",
                         "Viel Erfolg und Spaß beim Wortspiel!", color=discord.Color.dark_purple()))
            await m.remove_reaction(cross, self.bot.user)
            await self.update_event_message()

        temp = True
        for p in self.config["participants"]:
            if (self.data[str(p)]["word1"] == "" or self.data[str(p)]["word2"] == "" or self.data[str(p)]["phrase"] == ""):
                temp = False
        
        if temp:
            self.config["words_complete"] = True
        save_data("event_config", self.config)
        self.update_data()


    async def update_event_message(self):
        self.update_data()
        msg = await self.bot.get_channel(self.config["channel_id"]).fetch_message(self.config["event_message"])
        e = msg.embeds[0]
        if self.config["words_complete"]:
            e.timestamp = datetime.datetime.utcnow()
            e.description = "Das Spiel beginnt!"

            participants = self.config["participants"]
            e.clear_fields()
            for p in participants:
                user = self.bot.get_user(p)
                author = self.bot.get_user(self.data[str(p)]["word_author"])
                author_visible = (self.data[str(p)]["word1_found"] and self.data[str(p)]["word2_found"] and self.data[str(p)]["phrase_found"])
                v =  f"`Author:` `{author.name if author_visible else ' '}`\n\n"
                v += f"`Wort 1:` `{self.data[str(p)]['word1'] if self.data[str(p)]['word1_found'] else ' '}`\n"
                v += f"`Wort 2:` `{self.data[str(p)]['word2'] if self.data[str(p)]['word2_found'] else ' '}`\n"
                v += f"`Phrase:` `{self.data[str(p)]['phrase'] if self.data[str(p)]['phrase_found'] else ' '}`\n"
                v += f"`Platzierung: {self.data[str(p)]['placement']}`"
                e.add_field(name=user.name, value=v)
            await msg.edit(embed=e)

    @start.error
    @words.error
    async def on_command_error(self, ctx, error):
        # error = getattr(error, 'original', error)
        embed = discord.Embed(title=type(error).__name__)
        if isinstance(error, CommandNotFound) or isinstance(error, MissingRequiredArgument):
            return
        embed.description = str(error)
        embed.color = discord.Color.red()
        await ctx.send(embed=embed)


def get_data(filename):
    try:
        with open(config.path + f'/json/{filename}.json', 'r') as myfile:
            return json.loads(myfile.read())
    except FileNotFoundError:
        return {}


def save_data(filename, data):
    try:
        with open(config.path + f'/json/{filename}.json', 'w') as myfile:
            json.dump(data, myfile)
    except FileNotFoundError:
        file = open(config.path + f'/json/{filename}.json', 'w')
        file.write("{}")
        json.dump(data, file)
        file.close()


async def setup(bot):
    bot.add_cog(Event(bot))
