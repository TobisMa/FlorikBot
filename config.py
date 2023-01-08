import json
path = ""
try:
    import os
    path = os.path.abspath(".")
    with open(path + '/json/config.json', 'r') as myfile:
        data = myfile.read()
except:
    path = '/home/pi/lwBot/LWBot_Rewrite'
    with open(path + '/json/config.json', 'r') as myfile:
        data = myfile.read()


config = json.loads(data)
OWNER_IDS = config["owner_id"]
REQUIRED_UPVOTES_FOR_GOOD_MEME = config["upvotes_for_pin"]
DELETE_AFTER_DAYS = config["delete_after_days"]
TOKEN = config["discord_token"]
STATUS_MSG = config["status_message"]
MEME_CHANNEL_ID = config["meme_channel_id"]
UPVOTE = config["upvote_emoji"]
DOWNVOTE = config["downote_emoji"]
PREFIX = config["prefix"]
UNDERSTOOD_EMOJI = config["delete_emoji_name"]
latest_news_number = config["latest_gmo_news_number"]
NEWS_CHANNEL_ID = config["news_channel_id"]
GMO_ROLE_ID = config["gmo_role_id"]
SERVER_ID = config["server_id"]
LOG_CHANNEL_ID = config["log_channel_id"]
BOT_CHANNEL_ID = config["bot_channel_id"]
AWAKE_CHANNEL_IDS = config["awake_channel_IDs"]
ROLE_SEPERATOR_ID = config["course_role_sperator_role_id"]
PLAN_USERNAME = config["substitution_plan_username"]
PLAN_PW = config["substitution_plan_password"]
PLAN_CHANNEL = config["substitution_channel_id"]
GOOD_MEMES_CHANNEL_ID = config["good_memes_channel_id"]
BANISHED_ROLE_ID = config["banished_role_id"]
BANISHED_VC_ID = config["banished_channel_id"]
wortspielAllowedUserIds = [327461111173742592, 760125323580276757]

UNI_GUILD = config["uni"]["uni_server_id"]