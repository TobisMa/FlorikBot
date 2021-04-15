from asyncio import futures
import discord
from discord.ext import commands
from discord.ext import tasks

import asyncio
import datetime
import json

import config
from helper_functions import *
from bot import on_command_error

class Erinnerungen(commands.Cog):
    """Commands zum Bedienen der Erinnerungs-funktion"""

    def __init__(self, bot):
        self.bot = bot
        self.checkReminder.start()

    @commands.command(aliases=["remindme", "remind", "reminder", "rmd", "rmnd", "rmndr"])
    async def setreminder(self, ctx, *, arg):
        """Erstellt eine neue Erinnerung
            nutze das Schema
            `reminder (d)d.(m)m.yyyy (h)h:(m)m`
            Beispiel: `reminder 1.10.2020 6:34`"""
        try:
            length = min(len(arg.split()), 2)
            time_str = ' '.join(arg.split()[:length])
            time = datetime.datetime.strptime(time_str, '%d.%m.%Y %H:%M')
            if time < datetime.datetime.now():
                await ctx.send(embed=simple_embed(ctx.author, "Erinnerungen in der Vergangenheit sind nicht erlaubt.", color=discord.Color.orange()))
                return
            await ctx.send(embed=simple_embed(ctx.author, "Bitte gib deine Erinnerungsnachricht ein.", "Dies ist nur in den nächsten 60s möglich.", color=discord.Color.gold()))
            m = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
        except ValueError:
            await ctx.send(embed=simple_embed(ctx.author, "Dein Datum ist so nicht zulässig.", "Das Format sollte so aussehen:\n```reminder (d)d.(m)m.yyyy (h)h:(m)m\nBeispiel: reminder 1.10.2020 6:34```", color=discord.Color.red()))
            return
        except futures.TimeoutError:
            await ctx.send(embed=simple_embed(ctx.author, "Die Zeit ist abgelaufen.", "Bitte versuche es erneut, falls du eine Erinnerung erstellen möchtest.", color=discord.Color.red()))
            return
        except Exception:
            await ctx.send(embed=simple_embed(ctx.author, "Ein Fehler ist aufgetreten", "Deine Erinnerung konnte nicht gespeichert werden.", color=discord.Color.red()))
        else:
            if len(ctx.message.mentions) > 0:
                for recipient in ctx.message.mentions:
                    addReminder(
                        ctx.author.id, recipient.id, time_str, m.content + f"\n_[Hier]({ctx.message.jump_url}) erstellt_")
                    await ctx.send(embed=simple_embed(ctx.author, "Eine neue Erinnerung für " + recipient.name + ", " + time_str + " wurde erstellt.", m.content))
            if len(ctx.message.role_mentions) > 0:
                for role in ctx.message.role_mentions:
                    addReminder(
                        ctx.author.id, role.id, time_str, m.content + f"\n_[Hier]({ctx.message.jump_url}) erstellt_")
                    await ctx.send(embed=simple_embed(ctx.author, "Eine neue Erinnerung für @" + role.name + ", " + time_str + " wurde erstellt.", m.content))
            if len(ctx.message.mentions) == len(ctx.message.role_mentions) == 0:
                addReminder(
                    ctx.author.id, ctx.author.id, time_str, m.content + f"\n_[Hier]({ctx.message.jump_url}) erstellt_")
                await ctx.send(embed=simple_embed(ctx.author, "Eine neue Erinnerung für dich, " + time_str + " wurde erstellt.", m.content))
            return

    @commands.command(aliases=["mr"])
    async def myreminders(self, ctx):
        """Listet alle Erinnerungen eines Nutzers auf"""
        reminder = getReminder()
        if str(ctx.author.id) in list(reminder.keys()) and len(reminder[str(ctx.author.id)]) > 0:
            e = discord.Embed(title="Deine Erinnerungen", color=ctx.author.color,
                              timestamp=datetime.datetime.utcnow())
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
            for singleReminder in reminder[str(ctx.author.id)]:
                e.add_field(name=singleReminder[0],
                            value=singleReminder[1], inline=False)
            await ctx.send(embed=e)
        else:
            await ctx.send(embed=simple_embed(ctx.author, "Du hast keine Erinnerungen.",
                                                               f"Gebe {self.bot.command_prefix}reminder [Datum], um eine neue Erinnerung zu erstellen oder " +
                                                               f"{self.bot.command_prefix}help reminder ein, um dir die korrekte Syntax des Commandes anzeigen zu lassen."))

    @commands.command(aliases=["rmr"])
    async def removereminder(self, ctx):
        """Erinnerung entfernen
            rufe `,removereminder` auf, und wähle dann den Index der zu entfernenden Erinnerung"""
        reminder = getReminder()
        if str(ctx.author.id) in list(reminder.keys()) and len(reminder[str(ctx.author.id)]) > 0:
            e = discord.Embed(title="Deine Erinnerungen", color=ctx.author.color,
                              timestamp=datetime.datetime.utcnow())
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
            reminderCount = len(reminder[str(ctx.author.id)])
            for i in range(reminderCount):
                singleReminder = reminder[str(ctx.author.id)][i]
                e.add_field(name=f"[{i}] {singleReminder[0]}",
                            value=singleReminder[1], inline=False)

            await ctx.send(embed=e)
            await ctx.send(embed=simple_embed(ctx.author, "Gebe bitte den Index der Erinnerung ein, die du löschen möchtest.",
                                                               "Dies ist nur in den nächsten 60s möglich.", color=discord.Color.gold()))
            try:
                m = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
                index = int(m.content)
                if 0 <= index < reminderCount:
                    removeReminder(
                        ctx.author.id, *reminder[str(ctx.author.id)][index])
                    await ctx.send(embed=simple_embed(ctx.author, "Die Erinnerung wurde erfolgreich gelöscht.",
                                                                       f"Deine Erinnerung\n```{''.join(reminder[str(ctx.author.id)][index][1].splitlines()[:-1])}``` wurde gelöscht."))
                else:
                    raise ValueError
            except futures.TimeoutError:
                await ctx.send(embed=simple_embed(ctx.author, "Die Zeit ist abgelaufen.",
                                                                   "Bitte versuche es erneut, falls du eine Erinnerung löschen möchtest.", color=discord.Color.red()))
            except ValueError:
                await ctx.send(embed=simple_embed(ctx.author, "Eingabefehler",
                                                                   "Deine Eingabe war keine der zulässigen aufgeführten Indices.", color=discord.Color.red()))
        else:
            await ctx.send(embed=simple_embed(ctx.author, "Du hast keine Erinnerungen.",
                                                               f"Gebe {self.bot.command_prefix}reminder [Datum], um eine neue Erinnerung zu erstellen oder " +
                                                               f"{self.bot.command_prefix}help reminder ein, um dir die korrekte Syntax des Commandes anzeigen zu lassen."))

    @tasks.loop(seconds=30)
    async def checkReminder(self):
        r = getReminder()
        now = datetime.datetime.now()
        recipients = list(r.keys())
        for recipientID in recipients:
            for reminder in r[recipientID]:
                time = datetime.datetime.strptime(
                    reminder[0], '%d.%m.%Y %H:%M')
                if time <= now:
                    channel = self.bot.get_channel(config.BOT_CHANNEL_ID)
                    author = self.bot.get_guild(
                        config.SERVER_ID).get_member(int(reminder[2]))
                    recipient = self.bot.get_guild(
                        config.SERVER_ID).get_member(int(recipientID))
                    if recipient == None:
                        recipient = self.bot.get_guild(
                            config.SERVER_ID).get_role(int(recipientID))
                    if recipient == None:
                        return
                    color = recipient.color
                    await channel.send(content=recipient.mention, embed=simple_embed(author, "Erinnerung", reminder[1], color=color))
                    removeReminder(recipientID, *reminder)

    @checkReminder.before_loop
    async def beforeReminderCheck(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simple_embed(self.bot.user, "reminder loop start", color=discord.Color.green()))

    @checkReminder.after_loop
    async def afterReminderCheck(self):
        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simple_embed(self.bot.user, "reminder loop stopped.", color=discord.Color.orange()))
        await asyncio.sleep(60)
        self.checkReminder.restart()

    @checkReminder.error
    async def ReminderCheckError(self, error):
        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simple_embed(self.bot.user, "reminder error", color=discord.Color.orange()))
        await on_command_error(self.bot.get_channel(config.LOG_CHANNEL_ID), error)




def updateReminder(reminder):
    with open(config.path + '/json/reminder.json', 'w') as myfile:
        json.dump(reminder, myfile)


def getReminder():
    with open(config.path + '/json/reminder.json', 'r') as myfile:
        return json.loads(myfile.read())


def addReminder(author, recipient, time, message):
    reminder = getReminder()
    recipients = list(reminder.keys())
    if not str(recipient) in recipients:
        reminder[str(recipient)] = []
    reminder[str(recipient)].append([time, message, author])
    updateReminder(reminder)


def removeReminder(recipientID, time, message, author):
    reminder = getReminder()
    recipients = list(reminder.keys())
    if str(recipientID) in recipients:
        if [time, message, author] in reminder[str(recipientID)]:
            reminder[str(recipientID)].pop(reminder[str(recipientID)].index([time, message, author]))
    updateReminder(reminder)


def setup(bot):
    bot.add_cog(Erinnerungen(bot))