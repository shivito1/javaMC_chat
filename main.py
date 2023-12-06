import discord
from discord.ext import commands
import re

# Replace 'YOUR_TOKEN_HERE' with your actual bot token
f = open("configsettings.txt","r")
#read token from file
TOKEN = f.readline()
channel_id = int(f.readline())

# Define the intents
intents = discord.Intents.all()

# Create an instance of the bot with intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize channel_log as an empty string
channel_log = ""

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

    # Replace 'CHANNEL_ID' with the ID of the channel you want to fetch messages from
    #channel_id = # Replace with your channel ID
    channel = bot.get_channel(channel_id)

    if channel:
        # Fetch initial channel messages
        global channel_log
        channel_log = await get_channel_messages(channel)
        print(channel_log)
        parse_and_print_log(channel_log)

    else:
        print(f'Channel with ID {channel_id} not found.')


async def get_channel_messages(channel):
    channel_log = ""
    async for message in channel.history(limit=None):
        channel_log += message.content
    return channel_log


def parse_and_print_log(channel_log):
    # Define the regular expression pattern
    pattern = re.compile(r'(\w+):.*?```(.*?)```', re.DOTALL)

    # Find all matches in the text
    matches = pattern.findall(channel_log)

    # If the title is not provided explicitly, use the first part of each line
    data_dict = {title.strip(): command.strip() for title, command in matches}

    # Print the resulting dictionary
    print(data_dict)


@bot.event
async def on_message(message):
    # Check if the message is in the desired channel
    if message.channel.id == 1180972548184354939:
        # Update the channel_log when a new message is added
        global channel_log
        channel_log += message.content
        parse_and_print_log(channel_log)
        # You might want to call parse_and_print_log here if you want to print the updated log on each new message
        # parse_and_print_log(channel_log)

    await bot.process_commands(message)  # Make sure to process commands

# Run the bot with the provided token
bot.run(TOKEN)
