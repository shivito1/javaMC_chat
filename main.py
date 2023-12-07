import time
import re
import subprocess
import threading
import os
import discord
from discord.ext import commands
import asyncio

# Define the intents
intents = discord.Intents.all()

# Create an instance of the bot with intents
bot = commands.Bot(command_prefix='!', intents=intents)

channel_log = ""
channel_log_lock = threading.Lock()  # To prevent race conditions when updating channel_log
# Define server_process globally
server_process = None
data_dict = {}  # Define data_dict globally
# Create a lock for thread safety
data_dict_lock = threading.Lock()


@bot.event
async def on_ready():
    global channel_log, data_dict
    print(f'We have logged in as {bot.user}')

    # Replace 'CHANNEL_ID' with the ID of the channel you want to fetch messages from
    channel = bot.get_channel(channel_id)

    if channel:
        # Fetch initial channel messages
        channel_log, data_dict = await get_channel_messages(channel)
        print(channel_log)
        parse_and_print_log(channel_log)

    else:
        print(f'Channel with ID {channel_id} not found.')


@bot.event
async def on_message(message):
    # Check if the message is in the desired channel
    if message.channel.id == channel_id:
        # Fetch initial channel messages and update data_dict
        global channel_log, data_dict
        channel_log, data_dict = await get_channel_messages(message.channel)
        print(channel_log)
        parse_and_print_log(channel_log)

    await bot.process_commands(message)  # Make sure to process commands


async def get_channel_messages(channel):
    global data_dict
    channel_log = ""
    async for message in channel.history(limit=None):
        channel_log += message.content
        # Assume the messages follow the pattern you're looking for
        with data_dict_lock:
            data_dict.update(parse_message(message.content))

    return channel_log, data_dict


def parse_message(message_content):
    # Define the regular expression pattern for parsing messages
    pattern = re.compile(r'(\w+):.*?```(.*?)```', re.DOTALL)

    # Find all matches in the text
    matches = pattern.findall(message_content)

    # If the title is not provided explicitly, use the first part of each line
    return {title.strip(): command.strip() for title, command in matches}


def parse_and_print_log(channel_log):
    # Print or process channel_log as needed
    print(channel_log)


# Read bot token and channel ID from configsettings.txt
with open("configsettings.txt", "r") as f:
    TOKEN = f.readline().strip()
    channel_id = int(f.readline().strip())


def extract_chat_info(line):
    match = re.search(r'<(\w+)> (.*)', line)
    return match.groups() if match else (None, None)


def send_command_to_server(command, server_process):
    server_process.stdin.write(bytes(command + '\r\n', 'ascii'))
    server_process.stdin.flush()


def monitor_chat_log(file_path, server_process, data_dict):
    def remove_commas(input_string):
        # Use a regular expression to find and replace commas in the string
        result = re.sub(r'(-?\d+\.\d+), (-?\d+\.\d+), (-?\d+\.\d+)', r'\1 \2 \3', input_string)
        return result

    time.sleep(50)
    t = open(file_path, 'r', encoding='utf-8')
    t.seek(0, os.SEEK_END)
    last_position = t.tell()
    t.close

    while True:
        with open(file_path, 'r', encoding='utf-8') as file:
            file.seek(last_position)
            new_messages = file.readlines()

            if not new_messages:
                # No new messages, wait a bit before checking again
                time.sleep(0.1)
                continue

            last_position = file.tell()

        for message in new_messages:
            name, chat_message = extract_chat_info(message)
            if name and chat_message:
                formatted_message = f"{name}: {chat_message}"
                print(formatted_message)
                chat_message = remove_commas(chat_message)
                print(chat_message)

                chat_messagetrim = chat_message[5:]
                print(chat_messagetrim + "here")

                # Use the lock to ensure data_dict is accessed safely
                with data_dict_lock:
                    if chat_messagetrim in data_dict:
                        command = data_dict[chat_messagetrim]
                        command = remove_commas(command)
                        print(f"Using command from data_dict: {command}")
                        print(command + "command here")
                        if chat_messagetrim.startswith("nether"):
                            send_command_to_server(f"execute in minecraft:the_nether run tp {name}" + command[4:],
                                                   server_process)
                        elif chat_messagetrim.startswith("the_end"):
                            send_command_to_server(f"execute in minecraft:the_end run tp {name}" + command[4:],
                                                   server_process)
                        else:
                            send_command_to_server(f"tp {name}" + command[4:], server_process)
                    elif chat_message[:4] == '!=tp':
                        print(remove_commas(chat_message))
                        send_command_to_server(f"tp {name}" + chat_message[4:], server_process)
                    elif chat_message[:5] == '!=new':
                        print(remove_commas(chat_message))
                        with open("ourlocations.txt", "a") as f:
                            f.write(chat_message[5:] + "\r")


def discord_bot_thread():
    # Run the bot with the provided token
    bot.run(TOKEN)


def monitor_chat_log_threaded(log_file_path, server_process, data_dict):
    monitor_chat_log(log_file_path, server_process, data_dict)


def user_input_thread(server_process):
    while True:
        user_input = input("Enter command for the server (or 'exit' to stop): ")
        if user_input.lower() == 'exit':
            break
        server_process.stdin.write(bytes(user_input + '\r\n', 'ascii'))
        server_process.stdin.flush()


if __name__ == "__main__":
    log_file_path = r"C:\Users\johns\Minecraft Server\server java\logs\latest.log"
    server_start_command = r'java -jar "C:\Users\johns\Minecraft Server\server java\fabric-server-mc.1.20.1-loader.0.14.24-launcher.0.11.2.jar" nogui'

    # Start the server process
    server_process = subprocess.Popen(server_start_command, stdin=subprocess.PIPE, shell=True)

    # Start the monitoring thread
    monitor_thread = threading.Thread(target=monitor_chat_log_threaded, args=(log_file_path, server_process, data_dict))
    monitor_thread.start()

    # Start the Discord bot thread
    discord_thread = threading.Thread(target=discord_bot_thread)
    discord_thread.start()

    # Run the on_ready event in the asyncio event loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(on_ready())

    # Start the user input thread
    input_thread = threading.Thread(target=user_input_thread, args=(server_process,))
    input_thread.start()

    # Wait for the user input thread to finish
    input_thread.join()

    # Close the server process and wait for the user input thread to finish
    server_process.terminate()

    # Stop the Discord bot thread
    bot.close()
    discord_thread.join()
    monitor_thread.join()
