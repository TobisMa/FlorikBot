from typing import Any, Dict, List
import discord
from discord.ext import commands
from discord.ext import tasks

import asyncio
import contextlib
import datetime
import json
from bs4 import BeautifulSoup
import aiohttp
import base64
import gzip

import config
from helper_functions import simple_embed, update_config
from bot import on_command_error

class Schule(commands.Cog):
    """Commands zum Nutzen des personalisierten Stundenplans"""

    def __init__(self, bot):
        self.bot = bot
        # self.update_substitution_plan.start()

    async def cog_check(self, ctx):
        if ctx.guild.id == config.SERVER_ID:
            return True
        return False
        
    @commands.command()
    async def kurse(self, ctx):
        """Listet alle Kurse eines Nutzers auf"""
        # give the ctx.author the course seperator role if he does not have it already
        if config.ROLE_SEPERATOR_ID not in [c . id for c in ctx . author . roles]:
            await ctx.author.add_roles(ctx.guild.get_role(config.ROLE_SEPERATOR_ID))
        # if the ctx.author has at least one course role, send it
        kurse = get_my_course_role_names(ctx.author)
        if len(kurse) > 0:
            await ctx.send(embed=simple_embed(ctx.author, "Deine Kurse: ", f"```{', '.join(kurse)}```"))
        # otherwise, inform the ctx.author that he does not have any course roles
        else:
            await ctx.send(embed=simple_embed(ctx.author, "Du hast keine Kurse ausgewählt. ",
                                                               "Verwende den command addKurse [kurs1 kurs2 ...] um mehr hinzuzufügen.\nBeispiel: ```addKurse EN4 PH1```\ngibt dir die Kursrollen EN4 und PH1."))

    @commands.command(aliases=["ak"])
    async def addKurse(self, ctx, *, args):
        """Gibt dem Nutzer die gewünschten Kurse
            beispiel: `,addkurse MA1 IN2 de2 mu1`"""
        args = args.split(" ")
        # give the ctx.author the course seperator role if he does not have it already
        if config.ROLE_SEPERATOR_ID not in [c.id for c in ctx.author.roles]:
            await ctx.author.add_roles(ctx.guild.get_role(config.ROLE_SEPERATOR_ID))
        # for all roles listed to add
        for arg in args:
            # if the role does not exist, create it
            if arg not in get_my_course_role_names(ctx.guild):
                await create_course_role(ctx, arg)
            # if the ctx.author does not already have the role, add it
            if arg not in get_my_course_role_names(ctx.author):
                role_id = [r.id for r in get_my_course_roles(
                    ctx.guild) if r.name == arg][0]
                await ctx.author.add_roles(ctx.guild.get_role(role_id))

        kurse = get_my_course_role_names(ctx.author)
        await ctx.send(embed=simple_embed(ctx.author, "Deine Kurse: ", f"```{', '.join(kurse)}```"))

    @commands.command(aliases=["rk"])
    async def removeKurse(self, ctx, *, args):
        """Entfernt die gewünschten Kurse des Nutzers
            beispiel: `,removeKurse MA1 IN2 de2 mu1`"""
        args = args.split(" ")
        # give the ctx.author the course seperator role if he does not have it already
        if config.ROLE_SEPERATOR_ID not in [c.id for c in ctx.author.roles]:
            await ctx.author.add_roles(ctx.guild.get_role(config.ROLE_SEPERATOR_ID))
        for arg in args:
            # check if the ctx.author has the role that he wants to remove
            if arg not in get_my_course_role_names(ctx.author):
                await ctx.send(embed=simple_embed(ctx.author, "Du besitzt diese Kursrolle nicht.", color=discord.Color.red()))
                return
            # get the role id by name
            role_id = [r.id for r in get_my_course_roles(
                ctx.guild) if r.name == arg][0]
            # get the role by the id
            role = ctx.guild.get_role(role_id)
            await ctx.author.remove_roles(role)
            # delete the role if no members have it now
            if len(role.members) == 0:
                await role.delete(reason="Diese Kursrolle wird nicht mehr benutzt ist daher irrelevant.")
        await ctx.send(embed=simple_embed(ctx.author, f"Die Rolle(n) {', '.join(args)} wurde erfolgreich entfernt."))

    @commands.command(aliases=["mp"])
    async def myplan(self, ctx):
        """Zeigt den personalisierten Vertretungsplan des Nutzers an"""
        # give the ctx.author the course seperator role if he does not have it already
        if config.ROLE_SEPERATOR_ID not in [c.id for c in ctx.author.roles]:
            await ctx.author.add_roles(ctx.guild.get_role(config.ROLE_SEPERATOR_ID))
        # if the ctx.author has at least no course role, tell him and return
        kurse = get_my_course_role_names(ctx.author)
        if len(kurse) == 0:
            await ctx.send(embed=simple_embed(ctx.author, "Du hast keine Kurse ausgewählt. ",
                                                               "Verwende den command addKurse [kurs1 kurs2 ...] um mehr hinzuzufügen.\nBeispiel: ```addKurse EN4 PH1```\ngibt dir die Kursrollen EN4 und PH1."))
            return
        plan = get_substitution_plan()
        embed = discord.Embed(
            title="Dein persönlicher Vertretungsplan: ", color=ctx.author.color)
        embed.description = "`Stunde Art Kurs Lehrer Raum Bemerkungen`"
        embed.timestamp = datetime.datetime.now()
        embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar)
        courses = get_my_course_role_names(ctx.author)

        e = format_plan(plan, ctx.guild, embed, courses)
        await ctx.send(embed=e)



    @tasks.loop(seconds=300)
    async def update_substitution_plan(self):
        current_plan, new_plan = await get_current_substitution_plan()
        try:
            additions = {}
            removals = {}
            for date in new_plan.keys():
                additions[date] = []
                removals[date] = []
                if date not in current_plan.keys():
                    additions[date] = new_plan[date]
                else:
                    for k in new_plan[date]:
                        if k not in current_plan[date]:
                            additions[date].append(k)
                    for k in current_plan[date]:
                        if k not in new_plan[date]:
                            removals[date].append(k)
            channel = self.bot.get_channel(config.PLAN_CHANNEL)

            rm_embed = discord.Embed(
                title="Entfernt", color=discord.Color.red())
            added_embed = discord.Embed(
                title="Neu hinzugefügt", color=discord.Color.green())
            rm_embed.description = "gelöschte Vertretungen"
            added_embed.description = "geänderte Vertretungen"
            server = channel.guild
            rm_embed.timestamp = datetime.datetime.now()
            added_embed.timestamp = datetime.datetime.now()
            rm_embed = format_plan(
                removals, server, rm_embed)
            added_embed = format_plan(
                additions, server, added_embed)

            if len(rm_embed.fields) > 0:
                await channel.send(embed=rm_embed)
            if len(added_embed.fields) > 0:
                await channel.send(embed=added_embed)
        except Exception as e:
            with contextlib.suppress(Exception):
                await on_command_error(self.bot.get_channel(config.LOG_CHANNEL_ID), e)

    @update_substitution_plan.before_loop
    async def before_substitution_plan(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simple_embed(self.bot.user, "Vertretungplan loop start", color=discord.Color.green()))

    @update_substitution_plan.after_loop
    async def after_substitution_plan(self):
        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simple_embed(self.bot.user, "Vertretungplan loop stopped.", color=discord.Color.orange()))
        await asyncio.sleep(60)
        self.update_substitution_plan.restart()

    @update_substitution_plan.error
    async def substitution_plan_error(self, error):
        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simple_embed(self.bot.user, "substitution plan error", color=discord.Color.orange()))
        await on_command_error(self.bot.get_channel(config.LOG_CHANNEL_ID), error)



class Schulneuigkeiten(commands.Cog):
    def __init__(self, bot):
        self.bot = bot    
        self.check_website.start()

    @tasks.loop(seconds=300)
    async def check_website(self):
        news = await get_news()
        if news != None:
            channel = self.bot.get_channel(config.NEWS_CHANNEL_ID)
            await channel.send(channel.guild.get_role(config.GMO_ROLE_ID).mention + " " + news)

    @check_website.before_loop
    async def before_news(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simple_embed(self.bot.user, "gmoNewsCheck loop start", color=discord.Color.green()))

    @check_website.after_loop
    async def after_news(self):
        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simple_embed(self.bot.user, "gmoNewsCheck loop stopped.", color=discord.Color.orange()))
        await asyncio.sleep(60)
        self.check_website.restart()

    @check_website.error
    async def news_error(self, error):
        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simple_embed(self.bot.user, "gmo news error", color=discord.Color.orange()))
        await on_command_error(self.bot.get_channel(config.LOG_CHANNEL_ID), error)



def get_my_course_roles(ctx_author) -> List:
    kurse = []
    # all course roles except the @everyone role
    for r in ctx_author.roles[1:]:
        if config.ROLE_SEPERATOR_ID != r.id:
            kurse.append(r)
        else:
            break
    return kurse


def get_my_course_role_names(ctx):
    return [c.name for c in get_my_course_roles(ctx)]


async def create_course_role(ctx, name):
    await ctx.guild.create_role(name=name)


def update_substitution_plan(substitution_plan):
    with open(config.path + '/json/substitutionPlan.json', 'w') as myfile:
        json.dump(substitution_plan, myfile)


def get_substitution_plan():
    with open(config.path + '/json/substitutionPlan.json', 'r') as myfile:
        return json.loads(myfile.read())

async def get_plan_urls(username, password):
    date_string = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S:%f0")

    data = json.dumps({
        "AppId": "2092d12c-8470-4ef8-8c70-584965f9ffe5",
        "UserId": username,
        "UserPw": password,
        "AppVersion": "2.5.9",  # latest in PlayStore since 2016/02/18
        "Device": "VirtualBox",
        "OsVersion": "27 8.1.0",
        "Language": "de",
        "Date": date_string,
        "LastUpdate": date_string,
        "BundleId": "de.heinekingmedia.dsbmobile"
    }, separators=(",", ":")).encode("utf-8")

    body = {
        "req": {
            # data is sent gzip compressed and base64 encoded
            "Data": base64.b64encode(gzip.compress(data)).decode("utf-8"),
            "DataType": 1
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post("https://app.dsbcontrol.de/JsonHandler.ashx/GetData", json=body) as response:
            rjson = await response.json()
            response_data = json.loads(gzip.decompress(
                base64.b64decode(rjson["d"])).decode("utf-8"))
            for result in response_data['ResultMenuItems']:
                if result['Title'] != 'Inhalte':
                    continue
                for child in result['Childs']:
                    if child['MethodName'] != 'timetable':
                        continue
                    for child2 in child['Root']['Childs']:
                        if child2['Title'] != 'Schüler mobil':
                            continue
                        return list(map(lambda plan: plan['Detail'], child2['Childs']))
            return []

async def get_current_substitution_plan():
    async def get_only_grade_n(iterable, n):
        list_of_items_to_remove = []
        # geht die Liste durch, und schaut, welche einträge nicht zur n. Klasse gehören und merkt sich diese
        for element in iterable[:-1][0]:
            if(element["Klasse"] != n):
                list_of_items_to_remove.append(element)
        # löscht die elemente, welche er sich gemerkt hat
        for element in list_of_items_to_remove:
            iterable[0].remove(element)
        return iterable


    async def extract_table_from_site(url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status == 200:
                    soup = BeautifulSoup(await r.text(), "html.parser")
                    table_odd = soup.find_all("tr", class_="list odd")
                    table_even = soup.find_all("tr", class_="list even")
                    rows = []
                    for line in table_odd:
                        kurs = zeile_to_dict(line.find_all("td", class_="list"))
                        rows.append(kurs)
                    for line in table_even:
                        kurs = zeile_to_dict(line.find_all("td", class_="list"))
                        rows.append(kurs)
                    date = soup.find("div", class_="mon_title")
                    if date is None:
                        date = "11.11.2011 kein Datum vorhanden [Fehler]"
                    else:
                        date = date.text
                    return (rows, date)



    def zeile_to_dict(zeile) -> Dict[str, Any]:
        kurs = {}
        kurs["Klasse"] = zeile[0].text
        kurs["Stunde"] = zeile[1].text
        kurs["Art"] = zeile[6].text
        kurs["altes_Fach"] = zeile[2].text
        kurs["neues_Fach"] = zeile[4].text
        kurs["Vertreter"] = zeile[3].text.replace("+", "-")
        kurs["Raum"] = zeile[5].text.replace("---","-")
        kurs["Bemerkungen"] = zeile[7].text
        return kurs

    current_plan = getSubstitutionPlan()  # FIXME `getSubstitutionPlan` is not existing
    try:
        url1,url2,url3 = (await get_plan_urls(config.PLAN_USERNAME, config.PLAN_PW))
    except ValueError:
        return (current_plan, current_plan)


    # remove everything and get the newest substitution plan data

    new_plan = {}
    table1, date1 = await get_only_grade_n(await extract_table_from_site(url1), "12")
    table2, date2 = await get_only_grade_n(await extract_table_from_site(url2), "12")
    table3, date3 = await get_only_grade_n(await extract_table_from_site(url3), "12")
    new_plan[date1] = table1
    new_plan[date2] = table2
    new_plan[date3] = table3

    update_substitution_plan(new_plan)
    return (current_plan, new_plan)

def format_plan(plan, guild, embed, courses=[]):
    if courses == []:
        courses = get_my_course_role_names(guild)
    for date in list(plan.keys()):
        substitutions = []
        for i in range(len(plan[date])):
            field = plan[date][i]
            if field["altes_Fach"] in courses:
                course = field["altes_Fach"]
            elif field["neues_Fach"] in courses:
                course = field["neues_Fach"]
            else:
                continue
            if course in courses:
                substitutions.append(field)

        # get the max field length for all substitutions
        length = [0, 0, 0, 0, 0, 0]
        for substitution in substitutions:
            # j is the length index
            j = 0
            for k in list(substitution.keys()):
                if k == "altes_Fach":
                    if substitution["altes_Fach"] in courses:
                        substitution[k] = substitution["altes_Fach"]
                    elif substitution["neues_Fach"] in courses:
                        substitution[k] = substitution["neues_Fach"]
                elif k in ["neues_Fach", "Klasse"]:
                    continue

                length[j] = max(length[j], len(substitution[k]))
                j += 1

        # sort substitutions by time of lesson
        substitutions = sorted(
            substitutions, key=lambda k: k['Stunde'].split()[0])

        # stretch strings and apply them to the result string
        result = ""
        for i in range(len(substitutions)):
            # j is the length index
            j = 0
            result += "`"
            for k in list(substitutions[i].keys()):
                if k in ["neues_Fach", "Klasse"]:
                    continue
                # stretch the strings if needed
                substitutions[i][k] = substitutions[i][k].ljust(length[j])
                j += 1
                result += substitutions[i][k] + ("" if k == (list(substitutions[i].keys())[
                                                len(substitutions[i].keys()) - 1]) else "  ")
            result += f"`\n`{'-'*(sum(length) + 10)}`\n"
            if(len(result) > 1000):
                # date += " [zu viele Vertretungen]"
                embed.add_field(name=date, value=result[:1000] + "`", inline=False)
                result = "`" + result[1000:]

        if result.strip().replace("`", "") != "":
            # if(len(result) > 1020):
            #     result = result[:1020] + "..."
            #     date += " [zu viele Vertretungen]"
            embed.add_field(name=date, value=result, inline=False)
    return embed


async def get_news():
    url = "https://www.gymnasium-oberstadt.de/"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status == 200:
                soup = BeautifulSoup(await r.text(), "html.parser")
                for link in soup.findAll('a'):
                    if str(link.get('href')).startswith('https://www.gymnasium-oberstadt.de/neuigkeiten/'):
                        number = int(str(link.get('href')).replace('https://www.gymnasium-oberstadt.de/neuigkeiten/', "").split(".")[0])
                        if number > config.latest_news_number:
                            config.config["latest_gmo_news_number"] = number
                            config.latest_news_number = number
                            with open(config.path + '/json/config.json', 'w') as myfile:
                                myfile.write(json.dumps(config.config)) 
                            update_config()
                            return str(link.get('href'))
    return None

def setup(bot):
    bot.add_cog(Schule(bot))
    bot.add_cog(Schulneuigkeiten(bot))