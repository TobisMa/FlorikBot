import asyncio
import contextlib
import datetime
import json
import re
from typing import Optional

import discord
from discord import app_commands
from discord.errors import Forbidden
from discord.ext import commands, tasks

import config
from bot import on_command_error
from helper_functions import simple_embed


class Reminder():
    def __init__(self, author = None, date = "", message = "", users = None, roles = None, reminder_again = 0, reminder_again_in = "", is_private=False, r = None, channel=None):
        if users is None:
            users = []
        if roles is None:
            roles = []
            
        if channel != None:
            self.channel = channel
        
        if not r:
            self.author = author
            self.date = date
            self.message = message
            self.users = users
            self.roles = roles
            if len(users) == len(roles) == 0:
                self.users = [author]
            self.reminder_again = reminder_again
            self.reminder_again_in = reminder_again_in    
            self.private = is_private 
        else:
            self.__dict__ = json.loads(r)


class Erinnerungen(commands.Cog):
    """Commands zum Bedienen der Erinnerungs-funktion"""

    def __init__(self, bot):
        self.bot = bot
        self.checkReminder.start()

    @app_commands.command(name="reminder", description="Erschafft einen Reminder")
    @app_commands.describe(
        zeit="Zeitangabe für die Erinnerung",
        typ="Zeitformat",
        zugriff="Sichtbarkeit der Erinnerung",
        nachricht="Erinnerungsnachricht",
        user="Nutzer, der anstatt dir erwähnt werden soll"
    )
    @app_commands.choices(typ=[
            app_commands.Choice(name="relative Zeitangabe (5min)", value="relative"),
            app_commands.Choice(name="absolute Zeitangabe (dd.MM.yyyy hh:mm)", value="absolute"),
        ],
        zugriff=[
            app_commands.Choice(name="privat", value="private"),
            app_commands.Choice(name="öffentlich", value="public"), 
        ]
    )
    async def newnewreminder(self, interaction: discord.Interaction, typ: app_commands.Choice[str], zeit: str, zugriff: app_commands.Choice[str], nachricht: str, user: Optional[discord.User] = None):
        is_private = zugriff.value == "private"
        if is_private and user:
            e = simple_embed(interaction.user, "Du darfst private Reminder nur für dich selbst erstellen", color=discord.Color.red())
            await interaction.response.send_message(embed=e, ephemeral=True)
            return
        if typ.value == "relative":
            if not self.parse_to_timedelta(zeit):
                e = simple_embed(interaction.user, "Das eingegebene Zeitformat entspricht nicht dem Muster `5min` / `1h5min` / `6d22h`", color=discord.Color.red())
                await interaction.response.send_message(embed=e, ephemeral=True)
                return
            time = self.parse_to_timedelta(zeit)
            time += datetime.datetime.now()
        elif typ.value == "absolute":
            try:
                time = datetime.datetime.strptime(zeit, '%d.%m.%Y %H:%M')
            except ValueError:
                e = simple_embed(interaction.user, "Das eingegebene Zeitformat entspricht nicht dem Muster `dd.MM.yyyy hh:mm`", color=discord.Color.red())
                await interaction.response.send_message(embed=e, ephemeral=True)
                return

        time = time.strftime('%d.%m.%Y %H:%M')
        user = user.id if user else interaction.user.id
        r = Reminder(interaction.user.id, time, nachricht, [user], [], is_private=is_private, channel=interaction.channel_id)
        e = simple_embed(interaction.user, f"Glückwunsch, deine Erinnerung für {time} wurde erfolgreich gespeichert.")
        add_new_reminder(r)
        await interaction.response.send_message(embed=e, ephemeral=is_private)
        

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
        except asyncio.exceptions.TimeoutError:
            await ctx.send(embed=simple_embed(ctx.author, "Die Zeit ist abgelaufen.", "Bitte versuche es erneut, falls du eine Erinnerung erstellen möchtest.", color=discord.Color.red()))
            return
        except Exception:
            await ctx.send(embed=simple_embed(ctx.author, "Ein Fehler ist aufgetreten", "Deine Erinnerung konnte nicht gespeichert werden.", color=discord.Color.red()))
        else:
            if len(ctx.message.mentions) > 0:
                for recipient in ctx.message.mentions:
                    add_reminder(
                        ctx.author.id, recipient.id, time_str, m.content + f"\n_[Hier]({ctx.message.jump_url}) erstellt_")
                    await ctx.send(embed=simple_embed(ctx.author, "Eine neue Erinnerung für " + recipient.name + ", " + time_str + " wurde erstellt.", m.content))
            if len(ctx.message.role_mentions) > 0:
                for role in ctx.message.role_mentions:
                    add_reminder(
                        ctx.author.id, role.id, time_str, m.content + f"\n_[Hier]({ctx.message.jump_url}) erstellt_")
                    await ctx.send(embed=simple_embed(ctx.author, "Eine neue Erinnerung für @" + role.name + ", " + time_str + " wurde erstellt.", m.content))
            if len(ctx.message.mentions) == len(ctx.message.role_mentions) == 0:
                add_reminder(
                    ctx.author.id, ctx.author.id, time_str, m.content + f"\n_[Hier]({ctx.message.jump_url}) erstellt_")
                await ctx.send(embed=simple_embed(ctx.author, "Eine neue Erinnerung für dich, " + time_str + " wurde erstellt.", m.content))
            return

    @commands.command(aliases=["mr"])
    async def myreminders(self, ctx):
        """Listet alle Erinnerungen eines Nutzers auf"""
        reminder = get_reminder()
        if str(ctx.author.id) in list(reminder.keys()) and len(reminder[str(ctx.author.id)]) > 0:
            e = discord.Embed(
                title="Deine Erinnerungen",
                color=ctx.author.color,
                timestamp=datetime.datetime.now()
            )
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar)
            for single_reminder in reminder[str(ctx.author.id)]:
                # new
                if single_reminder[0] == "{":
                    rem = Reminder(r=single_reminder)
                    guild = self.bot.get_guild(config.SERVER_ID)
                    with contextlib.suppress(BaseException):
                        if rem.channel:
                            channel = self.bot.get_channel(rem.channel)
                            guild = channel.guild
                    if guild:
                        mentions = ' '.join([guild.get_role(role).mention for role in rem.roles])
                        mentions += " " + ' '.join([guild.get_member(user).mention for user in rem.users])
                    else:
                        mentions = " " + ' '.join([self.bot.get_user(user).mention for user in rem.users])
                    e.add_field(name=rem.date, value=mentions + "\n" + rem.message, inline=False)
                #old
                else:
                    e.add_field(name=single_reminder[0], value=single_reminder[1], inline=False)
            await ctx.send(embed=e)
        else:
            await ctx.send(embed=simple_embed(ctx.author, "Du hast keine Erinnerungen.",
                                                               f"Gebe {self.bot.command_prefix}reminder [Datum], um eine neue Erinnerung zu erstellen oder " +
                                                               f"{self.bot.command_prefix}help reminder ein, um dir die korrekte Syntax des Commandes anzeigen zu lassen."))

    @commands.command(aliases=["rmr"])
    async def removereminder(self, ctx):
        """Erinnerung entfernen
            rufe `,removereminder` auf, und wähle dann den Index der zu entfernenden Erinnerung"""
        new_reminder = False
        guild = self.bot.get_guild(config.SERVER_ID)
        reminder = get_reminder()
        if str(ctx.author.id) in list(reminder.keys()) and len(reminder[str(ctx.author.id)]) > 0:
            e = discord.Embed(
                title="Deine Erinnerungen",
                color=ctx.author.color,
                timestamp=datetime.datetime.now()
            )
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar)
            reminder_count = len(reminder[str(ctx.author.id)])
            for i in range(reminder_count):
                single_reminder = reminder[str(ctx.author.id)][i]
                # new
                if single_reminder[0] == "{":
                    new_reminder = True
                    rem = Reminder(r=single_reminder)
                    mentions = ' '.join([guild.get_role(role).mention for role in rem.roles])
                    mentions += " " + ' '.join([guild.get_member(user).mention for user in rem.users])
                    e.add_field(name=f"[{i}] {rem.date}",
                                value=mentions + "\n" + rem.message, inline=False)
                #old
                else:
                    e.add_field(name=f"[{i}] {single_reminder[0]}",
                                value=single_reminder[1], inline=False)

            await ctx.send(embed=e)
            await ctx.send(embed=simple_embed(ctx.author, "Gebe bitte den Index der Erinnerung ein, die du löschen möchtest.",
                                                               "Dies ist nur in den nächsten 60s möglich.", color=discord.Color.gold()))
            try:
                m = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
                index = int(m.content)
                if not 0 <= index < reminder_count:
                    raise ValueError
                # old
                if not new_reminder:
                    remove_reminder(ctx.author.id, *reminder[str(ctx.author.id)][index])
                    await ctx.send(embed=simple_embed(ctx.author, "Die Erinnerung wurde erfolgreich gelöscht.",
                                f"Deine Erinnerung\n```{''.join(reminder[str(ctx.author.id)][index][1].splitlines()[:-1])}``` wurde gelöscht."))
                # new
                else:
                    remove_new_reminder(ctx.author.id, rem)
                    await ctx.send(embed=simple_embed(ctx.author, "Die Erinnerung wurde erfolgreich gelöscht.",

                                f"Deine Erinnerung\n```{rem.message}``` für {mentions} wurde gelöscht."))

            except asyncio.TimeoutError:
                await ctx.send(embed=simple_embed(ctx.author, "Die Zeit ist abgelaufen.",
                                                                   "Bitte versuche es erneut, falls du eine Erinnerung löschen möchtest.", color=discord.Color.red()))
            except ValueError:
                await ctx.send(embed=simple_embed(ctx.author, "Eingabefehler",
                                                                   "Deine Eingabe war keine der zulässigen aufgeführten Indices.", color=discord.Color.red()))
        else:
            await ctx.send(embed=simple_embed(ctx.author, "Du hast keine Erinnerungen.",
                                                               f"Gebe {self.bot.command_prefix}reminder [Datum], um eine neue Erinnerung zu erstellen oder " +
                                                               f"{self.bot.command_prefix}help reminder ein, um dir die korrekte Syntax des Commandes anzeigen zu lassen."))

    @tasks.loop(seconds=60)
    async def checkReminder(self):
        r = get_reminder()
        now = datetime.datetime.now()
        recipients = list(r.keys())
        for recipient_id in recipients:
            for reminder in r[recipient_id]:
                channel = self.bot.get_channel(config.BOT_CHANNEL_ID)
                # old reminder format
                try:
                    time = datetime.datetime.strptime(
                        reminder[0], '%d.%m.%Y %H:%M')
                    if time <= now:
                        author = self.bot.get_guild(
                            config.SERVER_ID).get_member(int(reminder[2]))
                        recipient = self.bot.get_guild(
                            config.SERVER_ID).get_member(int(recipient_id))
                        if recipient is None:
                            recipient = self.bot.get_guild(
                                config.SERVER_ID).get_role(int(recipient_id))
                        if recipient is None:
                            return
                        color = recipient.color
                        await channel.send(content=recipient.mention, embed=simple_embed(author, "Erinnerung", reminder[1], color=color))
                        remove_reminder(recipient_id, *reminder)

                except ValueError:
                    rem : Reminder = Reminder(r=reminder)
                    # not all reminders have this
                    with contextlib.suppress(BaseException):
                        if rem.private:
                            channel = self.bot.get_user(rem.users[0])
                        else:
                            with contextlib.suppress(BaseException):
                                if rem.channel:
                                    channel = self.bot.get_channel(rem.channel)
                    if channel is None:
                        channel = self.bot.get_user(rem.users[0])
                    time = datetime.datetime.strptime(rem.date, '%d.%m.%Y %H:%M')
                    if time <= now:
                        content = self.bot.get_user(rem.author).mention
                        color = discord.Color.blurple()
                        if not isinstance(channel, discord.User):
                            guild = channel.guild
                            # guild = self.bot.get_guild(config.SERVER_ID)
                            if guild:
                                content = "" + ' '.join([guild.get_role(role).mention for role in rem.roles])
                                content += " " + ' '.join([guild.get_member(user).mention for user in rem.users])
                                color = guild.get_member(rem.author).color
                        embed = simple_embed(self.bot.get_user(rem.author), "Erinnerung", rem.message, color=color)

                        remove_new_reminder(rem.author, rem)

                        # change reminder date if it is reocurring
                        if rem.reminder_again > 0:
                            embed.description += f"\n\nDiese Erinnerung wird noch {(str(rem.reminder_again) + ' weiteres Mal') if rem.reminder_again == 1 else (str(rem.reminder_again) + ' weitere Male')} eintreten."
                            rem.reminder_again -= 1
                            rem.date = (time + self.parse_to_timedelta(rem.reminder_again_in)).strftime('%d.%m.%Y %H:%M')
                            embed.description += f"\nDas nächste Mal ist {rem.date}."
                            add_new_reminder(rem)

                        elif rem.reminder_again == -1:
                            embed.description += f"\n\nDiese Erinnerung wird noch unendlich weitere Male eintreten."
                            rem.date = (time + self.parse_to_timedelta(rem.reminder_again_in)).strftime('%d.%m.%Y %H:%M')
                            embed.description += f"\nDas nächste Mal ist {rem.date}."
                            add_new_reminder(rem)

                        await channel.send(content=content, embed=embed)


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

    def parse_to_timedelta(self, time_str) -> Optional[datetime.timedelta]:
        regex = re.compile(r'((?P<days>\d+?)d)?\s*((?P<hours>\d+?)h)?\s*((?P<minutes>\d+?)min)?')
        parts = regex.match(time_str)
        if not parts:
            return None
        d = parts.groupdict()
        for key in dict(d):
            if not d[key]:
                del d[key]
            elif d[key].isdigit():
                d[key] = int(d[key])
            else:
                return None
        return datetime.timedelta(**d)

    @commands.command(aliases=["newrm"])
    async def setReminderNew(self, ctx, *args):
        """Ein neuer und besserer Weg, einen Reminder zu setzen."""

        # emojis needed
        clock_emoji = "\N{ALARM CLOCK}"
        calendar_emoji = "\N{CALENDAR}"
        repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"
        repeat_once_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS WITH CIRCLED ONE OVERLAY}"
        private_emoji = "\N{lock}"
        checkmark = "\N{White Heavy Check Mark}"

        e = simple_embed(ctx.author, "Neue Erinnerung", color=discord.Color.dark_magenta())
        description = ["(Eins von beidem)",
        f"{clock_emoji} relative Zeitangabe (5min)",
        f"{calendar_emoji} absolute Zeitangabe (1.1.2021 11:01)",
        "",
        "(optional, erfordert eine noch anzugebende Wiederholungszeit)",
        f"{repeat_once_emoji} Erinnerung, die sich eine angegebene Zahl oft wiederholt",
        f"{repeat_emoji} Erinnerung, die sich bis zum eventuellen Löschen wiederholt",
        "",
        f"{private_emoji} wird in die discord DM's und nicht in den Server geschickt",
        "",
        f"{checkmark} ist zum Bestätigen, wenn alles ausgewählt wurde"
        ]
        e.description = '\n'.join(description)

        msg = await ctx.send(embed=e)
        await msg.add_reaction(clock_emoji)
        await msg.add_reaction(calendar_emoji)
        await msg.add_reaction(repeat_once_emoji)
        await msg.add_reaction(repeat_emoji)
        await msg.add_reaction(private_emoji)
        await msg.add_reaction(checkmark)

        time_format = ""
        repeat = 0
        is_private = False
        # reminder configuration
        finished = False
        while not finished:
            try:
                r, u = await self.bot.wait_for('reaction_add', check=lambda _r, _u: _u == ctx.author and _r.message == msg, timeout=120)
                if r.emoji == clock_emoji:
                    description[1] = description[1].strip("_")
                    description[1] = f"__{description[1]}__"
                    description[2] = description[2].strip("_")
                    time_format = "relative"
                elif r.emoji == calendar_emoji:
                    description[2] = description[2].strip("_")
                    description[2] = f"__{description[2]}__"
                    description[1] = description[1].strip("_")
                    time_format = "absolute"

                elif r.emoji == repeat_once_emoji:
                    repeat = -2
                    description[5] = description[5].strip("_")
                    description[5] = f"__{description[5]}__"
                    description[6] = description[6].strip("_")
                elif r.emoji == repeat_emoji:
                    repeat = -1
                    description[6] = description[6].strip("_")
                    description[6] = f"__{description[6]}__"
                    description[5] = description[5].strip("_")

                elif r.emoji == private_emoji:
                    is_private = not is_private
                    description[8] = description[8].strip("_")
                    if is_private:
                        description[8] = f"__{description[8]}__"


                elif r.emoji == checkmark and time_format != "":
                        finished = True
                        e.color = discord.Color.green()
                        await msg.edit(embed=e)
                        
                e.description = '\n'.join(description)
                await msg.edit(embed=e)
                try:
                    await r.remove(u)
                except Forbidden:
                    pass
            except asyncio.exceptions.TimeoutError:
                e.color = discord.Color.red()
                await msg.edit(embed=e)
                return

        # time details
        e = simple_embed(ctx.author, "Bitte gebe nun deine Erinnerungszeit ein", color=discord.Color.dark_magenta())
        finished = False
        time = None
        if time_format == "relative":
            e.description = "Beispiel: 7d5h2min"
        elif time_format == "absolute":
            e.description = "Beispiel: 1.1.2021 11:01"
        msg = await ctx.send(embed=e)
        while not finished:
            try:
                m = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=120)

                if time_format == "relative":
                    if not self.parse_to_timedelta(m.content):
                        await m.delete()
                        continue
                    time = self.parse_to_timedelta(m.content)
                    time += datetime.datetime.now()
                elif time_format == "absolute":
                    try:
                        time = datetime.datetime.strptime(m.content, '%d.%m.%Y %H:%M')
                    except ValueError:
                        time = None
                if not time:
                    await m.delete()
                    continue

                time = time.strftime('%d.%m.%Y %H:%M')
                e.color = discord.Color.green()
                await msg.edit(embed=e)
                finished = True
            except asyncio.exceptions.TimeoutError:
                e.color = discord.Color.red()
                await msg.edit(embed=e)
                return

        # when to reminder again after
        if repeat != 0:
            e = simple_embed(ctx.author, "Bitte gebe nun die Zeit ein, nach der du erneut erinnert werden sollst", "Beispiel: 7d5h2min", color=discord.Color.dark_magenta())
            msg = await ctx.send(embed=e)
            finished = False
            reminder_again_after = None
            while not finished:
                try:
                    m = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=120)
                    reminder_again_after = m.content
                    if not self.parse_to_timedelta(reminder_again_after):
                        await m.delete()
                        continue
                    e.color = discord.Color.green()
                    await msg.edit(embed=e)
                    finished = True
                except asyncio.exceptions.TimeoutError:
                    e.color = discord.Color.red()
                    await msg.edit(embed=e)
                    return
        
        # how often to remind after
        if repeat == -2:
            e = simple_embed(ctx.author, "Bitte gebe nun an, wie oft die Erinnerung wiederholt werden soll", "Der Wert dieser Zahl muss über 0 liegen.", color=discord.Color.dark_magenta())
            msg = await ctx.send(embed=e)
            try:
                m = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit() and int(m.content) > 0, timeout=120)
                repeat = int(m.content)
                e.color = discord.Color.green()
                await msg.edit(embed=e)
            except asyncio.exceptions.TimeoutError:
                e.color = discord.Color.red()
                await msg.edit(embed=e)
                return

        # who to mention
        if not is_private:
            e = simple_embed(ctx.author,
                "Bitte @erwähne nun alle Personen / Rollen, für die die Erinnerung sein soll", 
                "Im Falle von nur dir selbst nur dich selbst oder irgendeine Nachricht ohne Erwähnungen.",
                color=discord.Color.dark_magenta()
                )
            msg = await ctx.send(embed=e)
            try:
                m = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=120)
                users = m.raw_mentions
                roles = m.raw_role_mentions
                e.color = discord.Color.green()
                e.description += "\n"
                if len(users) == len(roles) == 0:
                    users.append(ctx.author.id)
                e.description += "Erwähnte Benutzer: " + ''.join([f"<@{user_id}>" for user_id in users])
                e.description += "\nErwähnte Rollen: " + ''.join([role.mention for role in m.role_mentions])
                await msg.edit(embed=e)
            except asyncio.exceptions.TimeoutError:
                e.color = discord.Color.red()
                await msg.edit(embed=e)
                return
        else:
            users = [ctx.author.id]
            roles = []

        # what the reminder message is
        e = simple_embed(ctx.author,
            "Zum Abschluss sollte nun noch die Erinnerungsnachricht angegeben werden.", 
            color=discord.Color.dark_magenta()
            )
        msg = await ctx.send(embed=e)
        try:
            m = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=120)
            reminder_message = m.content
            e.color = discord.Color.green()
            await msg.edit(embed=e)
        except asyncio.exceptions.TimeoutError:
            e.color = discord.Color.red()
            await msg.edit(embed=e)
            return

        if repeat != 0:
            r = Reminder(ctx.author.id, time, reminder_message, users, roles, repeat, reminder_again_after, is_private)
        else:
            r = Reminder(ctx.author.id, time, reminder_message, users, roles, is_private=is_private)
        e = simple_embed(ctx.author, f"Glückwunsch, deine Erinnerung für {time} wurde erfolgreich gespeichert.")
        await ctx.send(embed=e)
        add_new_reminder(r)        

def add_new_reminder(r):
    json_string = json.dumps(r.__dict__)
    reminder = get_reminder()
    authors = list(reminder.keys())
    if str(r.author) not in authors:
        reminder[str(r.author)] = []
    reminder[str(r.author)].append(json_string)
    update_reminder(reminder)

def remove_new_reminder(author, r):
    r = json.dumps(r.__dict__)
    reminder = get_reminder()
    authors = list(reminder.keys())
    if str(author) in authors and r in reminder[str(author)]:
        reminder[str(author)].pop(reminder[str(author)].index(r))
    update_reminder(reminder)

def update_reminder(reminder):
    with open(config.path + '/json/reminder.json', 'w') as myfile:
        json.dump(reminder, myfile)


def get_reminder():
    with open(config.path + '/json/reminder.json', 'r') as myfile:
        return json.loads(myfile.read())


def add_reminder(author, recipient, time, message):
    reminder = get_reminder()
    recipients = list(reminder.keys())
    if str(recipient) not in recipients:
        reminder[str(recipient)] = []
    reminder[str(recipient)].append([time, message, author])
    update_reminder(reminder)


def remove_reminder(recipient_id, time, message, author):
    reminder = get_reminder()
    recipients = list(reminder.keys())
    if str(recipient_id) in recipients:
        if [time, message, author] in reminder[str(recipient_id)]:
            reminder[str(recipient_id)].pop(reminder[str(recipient_id)].index([time, message, author]))
    update_reminder(reminder)


async def setup(bot):
    if(config.GUILDS):
        await bot.add_cog(Erinnerungen(bot), guilds=config.GUILDS)
    else:
        await bot.add_cog(Erinnerungen(bot))
        