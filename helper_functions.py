import datetime
import importlib

import discord
import requests

import config


def get_emoji(bot, emoji_name):
    return discord.utils.get(bot.emojis, name=emoji_name) or None

def update_config():
    importlib.reload(config)

def is_url_image(image_url):
    image_formats = ("image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp")
    try:
        r = requests.head(image_url)
        return r.headers["content-type"] in image_formats
    except Exception:
        return False

def simple_embed(author, title, description = "", image_url="", color=discord.Color.blurple()):
    e = discord.Embed(title=title, description=description)
    if image_url != "":
        e.set_image(url=image_url)
    e.color = color
    e.timestamp = datetime.datetime.now()
    e.set_footer(text=author.name, icon_url=author.avatar) 
    return e

