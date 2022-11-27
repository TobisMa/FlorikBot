from asyncio import futures
import discord
from discord.ext import commands

import asyncio
import datetime
import operator
import validators
import json
from collections import defaultdict

import config
from helper_functions import *
from bot import is_bot_dev, on_command_error

def is_private_server():
    async def predicate(ctx):
        return ctx.guild and ctx.guild.id == config.SERVER_ID
    return commands.check(predicate)

class Memes(commands.Cog):
    """Commands zum Votingsystem im Shitpostkanal"""

    def __init__(self, bot):
        self.bot = bot

    # @commands.command()
    # async def entries(self, ctx):
    #     """Zeigt alle Memes, deren Scores für die Bestenliste gespeichert werden"""
    #     deleteOldMessages()
    #     voteList = getVoteList()
    #     e = discord.Embed()
    #     e.color = discord.Color.purple()
    #     e.timestamp = datetime.datetime.utcnow()
    #     e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar)
    #     e.set_author(name=self.bot.user, icon_url=self.bot.user.avatar)
    #     if not len(voteList) > 0:
    #         e.title = "Gerade eben sind keine Memes vorhanden."
    #         await ctx.send(embed=e)
    #         return
    #     e.title = "Entries"
    #     e.description = "All current entry messages in the votelist.\n\n```[ MessageID:\n Upvotes \u2606, created_at ]```"
    #     for k in list(voteList.keys()):
    #         e.add_field(
    #             name=f"{str(k)}:", value=f"```{str(voteList[k][0])} \u2606, {str(voteList[k][1])}```", inline=False)

    #     await ctx.send(embed=e)

    @is_private_server()
    @commands.command()
    async def top(self, ctx):
        """Zeigt den Top-shitpost"""
        async with ctx.message.channel.typing():
            deleteOldMessages()
        voteList = getVoteList()
        if(len(voteList) > 0):
            vList = {}
            for i in voteList.keys():
                vList[i] = voteList[i][0]
            sortedDict = sorted(
                vList.items(), key=operator.itemgetter(1), reverse=True)
            winnerMessage = await self.bot.get_channel(config.MEME_CHANNEL_ID).fetch_message(sortedDict[0][0])
            score = voteList[sortedDict[0][0]][0]
            e = discord.Embed()
            e.title = f"Der aktuell beliebteste Beitrag mit {str(score)} {getEmoji(self.bot, config.UPVOTE)}"

            e.description = f"[Nachricht:]({winnerMessage.jump_url})"
            if(len(winnerMessage.attachments) > 0):
                e.set_image(url=winnerMessage.attachments[0].url)
            e.set_author(name=winnerMessage.author,
                         icon_url=winnerMessage.author.avatar)
            e.color = winnerMessage.guild.get_member(
                winnerMessage.author.id).colour
            date = winnerMessage.created_at
            e.description += "\n" + winnerMessage.content
            e.timestamp = datetime.datetime.utcnow()
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar)
            await ctx.message.channel.send(embed=e)
            if(len(winnerMessage.attachments) > 0):
                if(not is_url_image(e.image.url)):
                    await ctx.message.channel.send(winnerMessage.attachments[0].url)
        else:
            await ctx.message.channel.send("Zurzeit sind keine Memes vorhanden.")

    @is_private_server()
    @commands.command()
    async def stats(self, ctx, *args):
        """Wertet die Bewertungen der Shitposts der einzelnen Nutzer aus
            Dies wird aufgrund von discord rate limits lange dauern.
            Für jeden Nutzer werden Anzahl Memes, Anzahl upvotes/downvotes, upvote/downvote-Verhältnis sowie durchschnittliche upvotes/downvotes aufgelistet.
            \nAls optionale Parameter können zuerst Limit des Durchsuchens, dann auszuwertende Nutzer angegeben werden.
            \n`stats 200 @Florik3ks @Zuruniik` gibt die Daten für @Florik3ks und @Zuruniik während der letzten 200 Nachrichten (nicht Beiträge!) aus.
            \nOhne angegebene Personen werden die Daten von allen Personen, die Beiträge gepostet haben, aufgeführt.
            \nOhne ein angegebenes Nachrichtenlimit werden alle Beiträge ausgewertet."""
        if len(args) > 0:
            if not args[0].isnumeric() and len(ctx.message.mentions) == 0:
                return
        progressEmbed = discord.Embed(title="Nachrichten werden gelesen...")
        progressEmbed.description = "Dies könnte (wird) eine recht lange Zeit in Anspruch nehmen."
        progressEmbed.set_image(
            url=getEmoji(self.bot, "KannaSip").url)
        await ctx.send(embed=progressEmbed)
        progress = 0
        progressMsg = await ctx.send("`  0% fertig.`")
        last_edited = []
        start_time = datetime.datetime.utcnow()
        async with ctx.channel.typing():
            channel = self.bot.get_channel(config.MEME_CHANNEL_ID)
            upvote = getEmoji(self.bot, config.UPVOTE)
            downvote = getEmoji(self.bot, config.DOWNVOTE)
            members = defaultdict(lambda: defaultdict(int))
            limit = None
            if len(args) > 0 and args[0].isnumeric():
                limit = int(args[0])
            messageCount = limit if limit != None else len(await channel.history(limit=None).flatten())
            counter = 0
            async for m in channel.history(limit=limit):
                counter += 1

                oldProg = progress
                progress = round(counter / messageCount * 100)
                if progress != oldProg:
                    time_now = datetime.datetime.utcnow()
                    if len(last_edited) >= 5:
                        if (time_now - last_edited[0]).seconds >= 5:
                            await progressMsg.edit(content=f"`{str(progress).rjust(3)}% fertig.`")
                            last_edited.pop(0)
                            last_edited.append(time_now)
                    else:
                        await progressMsg.edit(content=f"`{str(progress).rjust(3)}% fertig.`")
                        last_edited.append(time_now)

                if len(m.reactions) > 0:
                    meme = False
                    for r in m.reactions:
                        voters = await r.users().flatten()
                        count = r.count - 1 if self.bot.user in voters else r.count
                        if r.emoji == upvote:
                            members[m.author.id]["up"] += count
                            meme = True
                        elif r.emoji == downvote:
                            members[m.author.id]["down"] += count
                            meme = True
                    if meme:
                        members[m.author.id]["memes"] += 1
            
            end_time = str(datetime.datetime.utcnow() - start_time)
            # round milliseconds
            end_time = end_time.split(".")[0] + "." + str(round(int(end_time.split(".")[1]), 2)) 
            await progressMsg.edit(content=f"`Bearbeitung in {end_time} abgeschlossen.`")

            e = discord.Embed(title="Stats", color=ctx.author.color,
                              timestamp=datetime.datetime.utcnow())
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar)

            for member_id in members.keys():
                if len(ctx.message.mentions) > 0:
                    if member_id not in [u.id for u in ctx.message.mentions]:
                        continue
                if members[member_id] == {}:
                    continue
                if members[member_id]["memes"] == 0:
                    continue
                member = self.bot.get_guild(config.SERVER_ID).get_member(member_id)
                up = members[member_id]['up']
                down = members[member_id]['down']
                total = members[member_id]['memes']
                ratio = round(
                    up / down, 2) if down > 0 else up if up > 0 else 1
                dvratio = "1"  # if down > 0 else "0"
                members[member_id]["ratio"] = ratio
                e.add_field(name=member.display_name, value=f"Anzahl der Beiträge: `{members[member_id]['memes']}`\n" +
                            f"`Gesamtanzahl` {str(upvote)} `{str(up).rjust(6)} : {str(down).ljust(6)}` {str(downvote)}\n" +
                            f"`Verhältnis  ` {str(upvote)} `{str(ratio).rjust(6)} : {dvratio.ljust(6)}` {str(downvote)}\n" +
                            f"`Durchschnitt` {str(upvote)} `{str(round(up / total, 2)).rjust(6)} : {str(round(down / total, 2)).ljust(6)}` {str(downvote)}",
                            inline=False
                            )

            for m in ctx.message.mentions:
                if m.id not in members.keys():
                    e.add_field(name=m.display_name, value="Anzahl der Beiträge: `0`\n" +
                                f"`Gesamtanzahl` {str(upvote)} `     0 : 0     ` {str(downvote)}\n" +
                                f"`Verhältnis  ` {str(upvote)} `     1 : 1     ` {str(downvote)}\n" +
                                f"`Durchschnitt` {str(upvote)} `     0 : 0     ` {str(downvote)}", inline=False
                                )
        await ctx.send(embed=e)

        ## Leaderboard ##
        l = discord.Embed(title="Leaderboard (Up-/Downvote Verhältnis)",
                          color=discord.Color.gold(), timestamp=datetime.datetime.utcnow())

        ratioLeaderboard = []

        for k in members.keys():
            ratioLeaderboard.append([members[k]["ratio"], k])

        ratioLeaderboard.sort(reverse=True)

        for r in ratioLeaderboard:
            member = self.bot.get_guild(config.SERVER_ID).get_member(r[1])
            l.add_field(name=member.display_name, value=str(r[0]))

        await ctx.send(embed=l)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if message.channel.id == config.MEME_CHANNEL_ID and (len(message.attachments) > 0 or validators.url(message.content)):
            await self.addVotes(message)

    async def addVotes(self, message):
        up = getEmoji(self.bot, config.UPVOTE)
        down = getEmoji(self.bot, config.DOWNVOTE)
        await message.add_reaction(up)
        await message.add_reaction(down)
        cross = "\N{CROSS MARK}"
        await message.add_reaction(cross)
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=lambda _reaction, _user: _user == message.author and _reaction.emoji == cross and _reaction.message == message)
            await message.clear_reaction(up)
            await message.clear_reaction(down)
        except asyncio.exceptions.TimeoutError:
            pass
        try:
            await message.clear_reaction(cross)
        except discord.errors.NotFound:
            pass
        
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # check if the channel of the reaction is the specified channel
        if payload.channel_id != config.MEME_CHANNEL_ID:
            return
        # get user, message and reaction
        user = self.bot.get_user(payload.user_id)
        msg = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        reaction = None
        for reac in msg.reactions:
            if reac.emoji == payload.emoji.name or reac.emoji == payload.emoji:
                reaction = reac
        if reaction == None:
            return

        # get up-/downvote emojis
        upvote = getEmoji(self.bot, config.UPVOTE)
        downvote = getEmoji(self.bot, config.DOWNVOTE)
        if user != self.bot.user:
            # in case the message author tries to up-/downvote their own post
            if reaction.message.author == user and (reaction.emoji == upvote or reaction.emoji == downvote):
                await reaction.remove(user)
                errormsg = await reaction.message.channel.send(f"{user.mention} Du darfst für deinen eigenen Beitrag nicht abstimmen.")
                deleteEmoji = getEmoji(
                    self.bot, config.UNDERSTOOD_EMOJI)
                await errormsg.add_reaction(deleteEmoji)
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=lambda _reaction, _user: _user == user and _reaction.emoji == deleteEmoji)
                except asyncio.exceptions.TimeoutError:
                    pass
                await errormsg.delete()
                return

            # change voting counter
            if reaction.emoji == upvote:
                changeVotingCounter(reaction.message, 1)
                # pin message when it has the specified amount of upvotes
                if reaction.count - 1 >= config.REQUIRED_UPVOTES_FOR_GOOD_MEME:
                    # await reaction.message.pin(reason="good meme")
                    await self.send_good_meme(reaction.message)
            elif reaction.emoji == downvote:
                changeVotingCounter(reaction.message, -1)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        # check if the channel of the reaction is the specified channel
        if payload.channel_id != config.MEME_CHANNEL_ID:
            return
        # get user, message and reaction
        user = self.bot.get_user(payload.user_id)
        msg = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        reaction = None
        for reac in msg.reactions:
            if reac.emoji == payload.emoji.name or reac.emoji == payload.emoji:
                reaction = reac
        if reaction == None:
            return
        # change voting counter
        if user != self.bot.user and user != reaction.message.author:
            if reaction.emoji == getEmoji(self.bot, config.UPVOTE):
                changeVotingCounter(reaction.message, -1)
            elif reaction.emoji == getEmoji(self.bot, config.DOWNVOTE):
                changeVotingCounter(reaction.message, 1)

    async def send_good_meme(self, msg, force=False):
        if not force:
            with open(config.path + '/json/goodMemes.json', 'r') as myfile:
                memes = json.loads(myfile.read())

            if msg.id in memes:
                return

            memes.append(msg.id)
            with open(config.path + '/json/goodMemes.json', 'w') as myfile:
                json.dump(memes, myfile)

        channel = self.bot.get_channel(config.GOOD_MEMES_CHANNEL_ID)
        e = discord.Embed()
        e.description = f"[Link zur Nachricht]({msg.jump_url})\n"
        if msg.reference != None: 
            # TODO vereinfachbar in v1.7
            c = self.bot.get_channel(msg.reference.channel_id)
            m = await c.fetch_message(msg.reference.message_id)
            e.description += f"[Bezieht sich auf ...]({m.jump_url})\n"
        e.set_author(name=msg.author,
                     icon_url=msg.author.avatar)
        e.color = msg.guild.get_member(
            msg.author.id).colour
        e.description += "\n" + msg.content
        e.timestamp = msg.created_at
        e.set_footer(text=msg.author.name, icon_url=msg.author.avatar)

        if(len(msg.attachments) > 0):
            if(is_url_image(msg.attachments[0].url)):
                e.set_image(url=msg.attachments[0].url)

                counter = 0
                while isinstance(e.image, None) or e.image.width == 0 and counter < 100:
                    counter += 1
                    e.set_image(url=msg.attachments[0].url)
                if counter == 100:
                    await on_command_error(self.bot.get_channel(config.LOG_CHANNEL_ID), Exception(f"{str(msg.id)}: good meme was not sent correctly."))
                elif counter > 0:
                    await on_command_error(self.bot.get_channel(config.LOG_CHANNEL_ID), Exception(f"{str(msg.id)}: good meme was not sent correctly, took {counter} attempts."))
                await channel.send(embed=e)

            else:
                try:
                    await channel.send(embed=e, file=await msg.attachments[0].to_file())
                except Exception as e:
                    await channel.send(embed=e, file=await msg.attachments[0].url)
                    await on_command_error(self.bot.get_channel(config.LOG_CHANNEL_ID), e)
                    
        else:
            if(is_url_image(msg.content)):
                e.description = e.description.splitlines()[0]
                e.set_image(url=msg.content)
            await channel.send(embed=e)

    @is_bot_dev()
    @commands.command()
    async def resend_good_meme(self, ctx, msgid):
        msg = await self.bot.get_channel(config.MEME_CHANNEL_ID).fetch_message(msgid)
        await self.send_good_meme(msg, True)

def updateVoteListFile(voteList):
    with open(config.path + '/json/voteList.json', 'w') as myfile:
        json.dump(voteList, myfile)


def getVoteList():
    with open(config.path + '/json/voteList.json', 'r') as myfile:
        return json.loads(myfile.read())


def changeVotingCounter(message, amountToChange):
    voteList = getVoteList()
    if not str(message.id) in list(voteList.keys()):
        voteList[str(message.id)] = (amountToChange, str(message.created_at))
        updateVoteListFile(voteList)
        return
    voteList[str(message.id)] = (voteList[str(message.id)][0] +
                                 amountToChange, voteList[str(message.id)][1])
    updateVoteListFile(voteList)


def deleteOldMessages():
    voteList = getVoteList()
    keys = list(voteList.keys())
    timeNow = datetime.datetime.today()
    for messageID in keys:
        try:
            days = (timeNow - datetime.datetime.strptime(voteList[messageID][1], '%Y-%m-%d %H:%M:%S.%f')).days
        except ValueError:
            days = (timeNow - datetime.datetime.strptime(voteList[messageID][1], '%Y-%m-%d %H:%M:%S')).days
        if days > config.DELETE_AFTER_DAYS:
            if messageID in keys:
                voteList.pop(messageID)

    updateVoteListFile(voteList)


async def setup(bot):
    await bot.add_cog(Memes(bot))