import asyncio
import contextlib
import datetime
import json
import operator
from collections import defaultdict

import discord
import validators
from discord.ext import commands

import public_config
from bot import is_bot_dev, on_command_error
from helper_functions import get_emoji, is_url_image


def is_private_server():
    async def predicate(ctx):
        return ctx.guild and ctx.guild.id == public_config.SERVER_ID
    return commands.check(predicate)

class Memes(commands.Cog):
    """Commands zum Votingsystem im Shitpostkanal"""

    def __init__(self, bot):
        self.bot = bot

    @is_private_server()
    @commands.command()
    async def top(self, ctx):
        """Zeigt den Top-shitpost"""
        async with ctx.message.channel.typing():
            delete_old_messages()
        vote_list = get_vote_list()
        if (len(vote_list) > 0):
            v_list = {i: vote_list[i][0] for i in vote_list.keys()}
            sorted_dict = sorted(
                v_list.items(), key=operator.itemgetter(1), reverse=True)
            winner_message = await self.bot.get_channel(public_config.MEME_CHANNEL_ID).fetch_message(sorted_dict[0][0])
            score = vote_list[sorted_dict[0][0]][0]
            e = discord.Embed()
            e.title = f"Der aktuell beliebteste Beitrag mit {str(score)} {get_emoji(self.bot, public_config.UPVOTE)}"

            e.description = f"[Nachricht:]({winner_message.jump_url})"
            if(len(winner_message.attachments) > 0):
                e.set_image(url=winner_message.attachments[0].url)
            e.set_author(name=winner_message.author,
                         icon_url=winner_message.author.avatar)
            e.color = winner_message.guild.get_member(
                winner_message.author.id).colour
            date = winner_message.created_at
            e.description += "\n" + winner_message.content
            e.timestamp = datetime.datetime.now()
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar)
            await ctx.message.channel.send(embed=e)
            if len(winner_message.attachments) > 0 and not is_url_image(e.image.url):
                await ctx.message.channel.send(winner_message.attachments[0].url)
        else:
            await ctx.message.channel.send("Zurzeit sind keine Memes vorhanden.")

    @is_private_server()
    @commands.command()
    async def stats(self, ctx, *args):
        """Wertet die Bewertungen der Shitposts der einzelnen Nutzer aus.
            Dies wird aufgrund von discord rate limits lange dauern.
            Für jeden Nutzer werden Anzahl Memes, Anzahl upvotes/downvotes, upvote/downvote-Verhältnis sowie durchschnittliche upvotes/downvotes aufgelistet.
            \nAls optionale Parameter können zuerst Limit des Durchsuchens, dann auszuwertende Nutzer angegeben werden.
            \n`stats 200 @Florik3ks @Zuruniik` gibt die Daten für @Florik3ks und @Zuruniik während der letzten 200 Nachrichten (nicht Beiträge!) aus.
            \nOhne angegebene Personen werden die Daten von allen Personen, die Beiträge gepostet haben, aufgeführt.
            \nOhne ein angegebenes Nachrichtenlimit werden alle Beiträge ausgewertet."""
        if args and not args[0].isnumeric() and len(ctx.message.mentions) == 0:
            return
        progress_embed = discord.Embed(title="Nachrichten werden gelesen...")
        progress_embed.description = "Dies könnte (wird) eine recht lange Zeit in Anspruch nehmen."
        progress_embed.set_image(url=get_emoji(self.bot, "KannaSip").url)
        await ctx.send(embed=progress_embed)
        progress = 0
        progress_msg = await ctx.send("`  0% fertig.`")
        last_edited = []
        start_time = datetime.datetime.now()
        async with ctx.channel.typing():
            channel = self.bot.get_channel(public_config.MEME_CHANNEL_ID)
            upvote = get_emoji(self.bot, public_config.UPVOTE)
            downvote = get_emoji(self.bot, public_config.DOWNVOTE)
            members = defaultdict(lambda: defaultdict(int))
            limit = int(args[0]) if args and args[0].isnumeric() else None
            message_count = limit if limit != None else len([a async for a in await channel.history(limit=None)])

            counter = 0
            async for m in channel.history(limit=limit):
                counter += 1

                old_prog = progress
                progress = round(counter / message_count * 100)
                if progress != old_prog:
                    time_now = datetime.datetime.now()
                    if len(last_edited) >= 5:
                        if (time_now - last_edited[0]).seconds >= 5:
                            await progress_msg.edit(content=f"`{str(progress).rjust(3)}% fertig.`")
                            last_edited.pop(0)
                            last_edited.append(time_now)
                    else:
                        await progress_msg.edit(content=f"`{str(progress).rjust(3)}% fertig.`")
                        last_edited.append(time_now)

                if len(m.reactions) > 0:
                    meme = False
                    for r in m.reactions:
                        voters = [a async for a in r.users()]
                        count = r.count - 1 if self.bot.user in voters else r.count
                        if r.emoji == upvote:
                            members[m.author.id]["up"] += count
                            meme = True
                        elif r.emoji == downvote:
                            members[m.author.id]["down"] += count
                            meme = True
                    if meme:
                        members[m.author.id]["memes"] += 1

            end_time = str(datetime.datetime.now() - start_time)
            # round milliseconds
            end_time = end_time.split(".")[0] + "." + str(round(int(end_time.split(".")[1]), 2))
            await progress_msg.edit(content=f"`Bearbeitung in {end_time} abgeschlossen.`")

            e = discord.Embed(title="Stats", color=ctx.author.color,
                              timestamp=datetime.datetime.now())
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar)

            for member_id, value_ in members.items():
                if len(ctx.message.mentions) > 0 and member_id not in [u.id for u in ctx.message.mentions]:
                    continue
                if value_ == {}:
                    continue
                if members[member_id]["memes"] == 0:
                    continue
                member = self.bot.get_guild(public_config.SERVER_ID).get_member(member_id)
                up = members[member_id]['up']
                down = members[member_id]['down']
                total = members[member_id]['memes']
                ratio = round(up / down, 2) if down > 0 else max(up, 1)
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
        l = discord.Embed(
            title="Leaderboard (Up-/Downvote Verhältnis)",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now()
        )

        ratio_leaderboard = [[v["ratio"], k] for k, v in members.items()]

        ratio_leaderboard.sort(reverse=True)

        for r in ratio_leaderboard:
            member = self.bot.get_guild(public_config.SERVER_ID).get_member(r[1])
            l.add_field(name=member.display_name, value=str(r[0]))

        await ctx.send(embed=l)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if message.channel.id == public_config.MEME_CHANNEL_ID and (len(message.attachments) > 0 or validators.url(message.content)):
            await self.addVotes(message)

    async def addVotes(self, message):
        up = get_emoji(self.bot, public_config.UPVOTE)
        down = get_emoji(self.bot, public_config.DOWNVOTE)
        await message.add_reaction(up)
        await message.add_reaction(down)
        cross = "\N{CROSS MARK}"
        await message.add_reaction(cross)
        
        with contextlib.suppress(asyncio.exceptions.TimeoutError):  # don't even know if it does work. Was a extension's suggestion
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=lambda _reaction, _user: _user == message.author and _reaction.emoji == cross and _reaction.message == message)
            await message.clear_reaction(up)
            await message.clear_reaction(down)
        with contextlib.suppress(discord.errors.NotFound): # don't even know if it does work. Was a extension's suggestion
            await message.clear_reaction(cross)
        
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # check if the channel of the reaction is the specified channel
        if payload.channel_id != public_config.MEME_CHANNEL_ID:
            return
        # get user, message and reaction
        user = self.bot.get_user(payload.user_id)
        msg = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        reaction = None
        for reac in msg.reactions:
            if reac.emoji in [payload.emoji.name, payload.emoji]:
                reaction = reac
        if reaction is None:
            return

        # get up-/downvote emojis
        upvote = get_emoji(self.bot, public_config.UPVOTE)
        downvote = get_emoji(self.bot, public_config.DOWNVOTE)
        if user != self.bot.user:
            # in case the message author tries to up-/downvote their own post
            if reaction.message.author == user and reaction.emoji in [upvote, downvote]:
                await reaction.remove(user)
                errormsg = await reaction.message.channel.send(f"{user.mention} Du darfst für deinen eigenen Beitrag nicht abstimmen.")
                delete_emoji = get_emoji(
                    self.bot, public_config.UNDERSTOOD_EMOJI)
                await errormsg.add_reaction(delete_emoji)
                with contextlib.suppress(asyncio.exceptions.TimeoutError):
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=lambda _reaction, _user: _user == user and _reaction.emoji == delete_emoji)
                await errormsg.delete()
                return

            # change voting counter
            if reaction.emoji == upvote:
                change_voting_counter(reaction.message, 1)
                # pin message when it has the specified amount of upvotes
                if reaction.count - 1 >= public_config.REQUIRED_UPVOTES_FOR_GOOD_MEME:
                    # await reaction.message.pin(reason="good meme")
                    await self.send_good_meme(reaction.message)
            elif reaction.emoji == downvote:
                change_voting_counter(reaction.message, -1)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        # check if the channel of the reaction is the specified channel
        if payload.channel_id != public_config.MEME_CHANNEL_ID:
            return
        # get user, message and reaction
        user = self.bot.get_user(payload.user_id)
        msg = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        reaction = None
        for reac in msg.reactions:
            if reac.emoji in [payload.emoji.name, payload.emoji]:
                reaction = reac
        if reaction is None:
            return
        # change voting counter
        if user not in [self.bot.user, reaction.message.author]:
            if reaction.emoji == get_emoji(self.bot, public_config.UPVOTE):
                change_voting_counter(reaction.message, -1)
            elif reaction.emoji == get_emoji(self.bot, public_config.DOWNVOTE):
                change_voting_counter(reaction.message, 1)

    async def send_good_meme(self, msg, force=False):
        if not force:
            with open(public_config.path + '/json/goodMemes.json', 'r') as myfile:
                memes = json.loads(myfile.read())

            if msg.id in memes:
                return

            memes.append(msg.id)
            with open(public_config.path + '/json/goodMemes.json', 'w') as myfile:
                json.dump(memes, myfile)

        channel = self.bot.get_channel(public_config.GOOD_MEMES_CHANNEL_ID)
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

        if len(msg.attachments) > 0:
            if is_url_image(msg.attachments[0].url):
                e.set_image(url=msg.attachments[0].url)
                counter = 0
                while e.image is None or e.image.width == 0 and counter < 100:
                    counter += 1
                    e.set_image(url=msg.attachments[0].url)
                if counter == 100:
                    await on_command_error(self.bot.get_channel(public_config.LOG_CHANNEL_ID), Exception(f"{str(msg.id)}: good meme was not sent correctly."))
                elif counter > 0:
                    await on_command_error(self.bot.get_channel(public_config.LOG_CHANNEL_ID), Exception(f"{str(msg.id)}: good meme was not sent correctly, took {counter} attempts."))
                await channel.send(embed=e)

            else:
                try:
                    await channel.send(embed=e, file=await msg.attachments[0].to_file())
                except Exception as e:
                    await channel.send(embed=e, file=await msg.attachments[0].url)
                    await on_command_error(self.bot.get_channel(public_config.LOG_CHANNEL_ID), e)
                    
        else:
            if(is_url_image(msg.content)):
                e.description = e.description.splitlines()[0]
                e.set_image(url=msg.content)
            await channel.send(embed=e)

    @is_bot_dev()
    @commands.command()
    async def resend_good_meme(self, ctx, msgid):
        msg = await self.bot.get_channel(public_config.MEME_CHANNEL_ID).fetch_message(msgid)
        await self.send_good_meme(msg, True)

def update_vote_list_file(vote_list):
    with open(public_config.path + '/json/voteList.json', 'w') as myfile:
        json.dump(vote_list, myfile)


def get_vote_list():
    with open(public_config.path + '/json/voteList.json', 'r') as myfile:
        return json.loads(myfile.read())


def change_voting_counter(message, amountToChange):
    vote_list = get_vote_list()
    if str(message.id) not in list(vote_list.keys()):
        vote_list[str(message.id)] = (amountToChange, str(message.created_at))
        update_vote_list_file(vote_list)
        return
    vote_list[str(message.id)] = (vote_list[str(message.id)][0] +
                                 amountToChange, vote_list[str(message.id)][1])
    update_vote_list_file(vote_list)


def delete_old_messages():
    vote_list = get_vote_list()
    keys = list(vote_list.keys())
    time_now = datetime.datetime.today()   # FIXME find a solution
    for message_id in keys:
        try:
            days = (time_now - datetime.datetime.strptime(vote_list[message_id][1], '%Y-%m-%d %H:%M:%S.%f')).days
        except ValueError:
            days = (time_now - datetime.datetime.strptime(vote_list[message_id][1], '%Y-%m-%d %H:%M:%S')).days
            
        if days > public_config.DELETE_AFTER_DAYS and message_id in keys:
            vote_list.pop(message_id)

    update_vote_list_file(vote_list)


async def setup(bot):
    await bot.add_cog(Memes(bot))