import discord
import config
import importlib
import requests
import datetime


def getEmoji(bot, emojiName):
    emoji = discord.utils.get(bot.emojis, name=emojiName)
    if emoji:
        return emoji
    return None

def update_config():
    importlib.reload(config)

def is_url_image(image_url):
    image_formats = ("image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp")
    try:
        r = requests.head(image_url)
        if r.headers["content-type"] in image_formats:
            return True
        return False
    except:
        return False

def simple_embed(author, title, description = "", image_url="", color=discord.Color.blurple()):
    e = discord.Embed(title=title, description=description)
    if image_url != "":
        e.set_image(url=image_url)
    e.color = color
    e.timestamp = datetime.datetime.now()
    e.set_footer(text=author.name, icon_url=author.avatar) 
    return e

