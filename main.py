#test save

import discord
from discord import app_commands
from discord.ext import commands
import json, os
from flask import Flask
import threading
import datetime
import asyncio
from collections import defaultdict
from discord import Embed



bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.command()
async def lastdelete(ctx):
    async for entry in ctx.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        await ctx.send(f"Last channel deleted by: {entry.user}")

# Abuse tracking system
abuse_events = defaultdict(list)
ABUSE_THRESHOLD = 5
TIME_WINDOW = 60  # seconds
SENIOR_MOD_IDS = [219920365227474944, 996087982798950410, 345626453844313099468989012]  # Replace with actual IDs

def log_abuse_event(user_id: int, event_type: str):
    now = asyncio.get_event_loop().time()
    abuse_events[user_id] = [t for t in abuse_events[user_id] if now - t < TIME_WINDOW]
    abuse_events[user_id].append(now)
    return len(abuse_events[user_id]) >= ABUSE_THRESHOLD

async def handle_abuse(member: discord.Member):
    # Remove roles
    roles = [role for role in member.roles if role.name != "@everyone"]
    try:
        await member.edit(roles=[])
    except Exception as e:
        print(f"Failed to remove roles: {e}")

    # Notify senior mods
    embed_mod = Embed(
        title="⚠️ Possible Admin Abuse Detected",
        description=f"{member.mention} has triggered 5 or more major actions in under 60 seconds.",
        color=0xFF5555
    )
    for mod_id in SENIOR_MOD_IDS:
        mod = member.guild.get_member(mod_id)
        if mod:
            try:
                await mod.send(embed=embed_mod)
            except:
                pass

    # DM the accused
    embed_accused = Embed(
        title="🚨 You May Have Been Flagged",
        description="You triggered multiple high-level actions in a short time and had your roles removed.\n\n"
                    "Please contact `bonesdominion`, `WinterTale`, or `LordRitos` to review the situation and potentially restore your roles.",
        color=0x990000
    )
    try:
        await member.send(embed=embed_accused)
    except:
        pass

# Watch major actions
@bot.event
async def on_member_ban(guild, user):
    member = guild.get_member(user.id)
    if member and log_abuse_event(member.id, "ban"):
        await handle_abuse(member)

@bot.event
async def on_member_remove(member):  # kick detection
    if log_abuse_event(member.id, "kick"):
        await handle_abuse(member)

@bot.event
async def on_guild_channel_delete(channel):
    print(f"Channel deleted: {channel.name} in guild {channel.guild.name}")
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        print(f"Audit log entry found: {entry.user} deleted a channel")
        if log_abuse_event(entry.user.id, "channel_delete"):
            print(f"Abuse detected for user {entry.user}")
            member = channel.guild.get_member(entry.user.id)
            if member:
                await handle_abuse(member)


@bot.event
async def on_guild_channel_update(before, after):
    if before.name != after.name:
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
            if log_abuse_event(entry.user.id, "rename_channel"):
                member = after.guild.get_member(entry.user.id)
                if member:
                    await handle_abuse(member)

@bot.event
async def on_guild_role_update(before, after):
    if not before.hoist and after.hoist:
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update):
            if log_abuse_event(entry.user.id, "hoist_role"):
                member = after.guild.get_member(entry.user.id)
                if member:
                    await handle_abuse(member)


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
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True
intents.members = True
intents.message_content = True
intents.guilds = True
intents.bans = True
intents.guild_messages = True
intents.guild_scheduled_events = True
intents.guild_message_reactions = True
intents.guild_presences = True
intents.guild_typing = True
intents.integrations = True
intents.webhooks = True

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

@bot.event
async def on_member_unban(guild, user):
    if str(user.id) in banned_users:
        try:
            await guild.ban(user, reason="Re-banned: Global ban still in effect.")
            print(f"Re-banned {user} in {guild.name} after manual unban.")
        except Exception as e:
            print(f"Failed to re-ban {user} in {guild.name}: {e}")


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

@tree.command(name="globalunban", description="Globally unban a user by ID.")
@app_commands.describe(user_id="User ID to unban")
async def globalunban(interaction: discord.Interaction, user_id: str):
    if not is_moderator(interaction):
        await interaction.response.send_message("You need the 'Moderator' role.", ephemeral=True)
        return

    if user_id not in banned_users:
        await interaction.response.send_message("User is not globally banned.", ephemeral=True)
        return

    banned_users.remove(user_id)
    save_bans()

    count = 0
    for guild in bot.guilds:
        try:
            await guild.unban(discord.Object(id=int(user_id)))
            count += 1
        except:
            pass

    await interaction.response.send_message(f"User ID {user_id} unbanned in {count} servers.")


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
