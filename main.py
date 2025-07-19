#test save

import discord
from discord import app_commands
from discord.ext import commands
import json, os
from flask import Flask
import threading

# Read token from environment (Railway or Render)
TOKEN = os.getenv("DISCORD_TOKEN")

BAN_FILE = "bans.json"

if os.path.exists(BAN_FILE):
    if os.path.getsize(BAN_FILE) > 0:
        with open(BAN_FILE, "r") as f:
            banned_users = json.load(f)
    else:
        banned_users = []
else:
    banned_users = []

intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # Make sure this is enabled if you rely on message content
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

def save_bans():
    with open(BAN_FILE, "w") as f:
        json.dump(banned_users, f)

def is_moderator(interaction):
    return any(role.name == "Moderator" for role in interaction.user.roles)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot is ready. Logged in as {bot.user}")

@tree.command(name="globalban", description="Globally ban a user.")
@app_commands.describe(user="User to ban", reason="Why?")
async def globalban(interaction, user: discord.User, reason: str = "No reason"):
    if not is_moderator(interaction):
        await interaction.response.send_message("You need the 'Moderator' role.", ephemeral=True)
        return

    if str(user.id) in banned_users:
        await interaction.response.send_message("Already banned.", ephemeral=True)
        return

    banned_users.append(str(user.id))
    save_bans()

    count = 0
    for guild in bot.guilds:
        try:
            await guild.ban(user, reason=reason)
            count += 1
        except:
            pass

    await interaction.response.send_message(f"{user} banned in {count} servers.")

@tree.command(name="globalunban", description="Globally unban a user.")
@app_commands.describe(user="User to unban")
async def globalunban(interaction, user: discord.User):
    if not is_moderator(interaction):
        await interaction.response.send_message("You need the 'Moderator' role.", ephemeral=True)
        return

    if str(user.id) not in banned_users:
        await interaction.response.send_message("User not globally banned.", ephemeral=True)
        return

    banned_users.remove(str(user.id))
    save_bans()

    count = 0
    for guild in bot.guilds:
        try:
            await guild.unban(user)
            count += 1
        except:
            pass

    await interaction.response.send_message(f"{user} unbanned in {count} servers.")

# --- Flask server to keep Render happy ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Run Flask server in background thread
threading.Thread(target=run_web).start()

# Run the bot
bot.run(TOKEN)
