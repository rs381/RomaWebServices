import os
import discord
from discord.ext import commands
import datetime

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- COOLDOWN SYSTEM ---
mod_usage = {}  # {user_id: [timestamps]}
COOLDOWN_LIMIT = 3
COOLDOWN_WINDOW = 3600  # 1 hour in seconds

# Senior mods (bypass + can reset cooldowns)
SENIOR_MODS = [123456789012345678, 987654321098765432]  # replace with your user IDs

def can_use_mod_action(user_id: int) -> bool:
    now = datetime.datetime.utcnow().timestamp()
    if user_id not in mod_usage:
        mod_usage[user_id] = []
    # Keep only actions within the last hour
    mod_usage[user_id] = [t for t in mod_usage[user_id] if now - t < COOLDOWN_WINDOW]
    if len(mod_usage[user_id]) >= COOLDOWN_LIMIT:
        return False
    mod_usage[user_id].append(now)
    return True

# --- GLOBAL BAN ---
@bot.command()
@commands.has_permissions(ban_members=True)
async def gban(ctx, user: discord.User, *, reason="No reason provided"):
    if ctx.author.id not in SENIOR_MODS and not can_use_mod_action(ctx.author.id):
        return await ctx.send("⛔ You’ve hit the 3 actions/hour limit. Please wait.")

    banned_from, failed = [], []
    for guild in bot.guilds:
        member = guild.get_member(user.id)
        if member:
            try:
                await member.ban(reason=f"[Global Ban by {ctx.author}] {reason}")
                banned_from.append(guild.name)
            except Exception:
                failed.append(guild.name)

    await ctx.send(
        f"✅ Globally banned {user.mention}.\n"
        f"Banned from: {', '.join(banned_from) or 'None'}\n"
        f"Failed: {', '.join(failed) or 'None'}"
    )

# --- GLOBAL UNBAN ---
@bot.command()
@commands.has_permissions(ban_members=True)
async def gunban(ctx, user: discord.User, *, reason="No reason provided"):
    if ctx.author.id not in SENIOR_MODS and not can_use_mod_action(ctx.author.id):
        return await ctx.send("⛔ You’ve hit the 3 actions/hour limit. Please wait.")

    unbanned_from, failed = [], []
    for guild in bot.guilds:
        try:
            await guild.unban(user, reason=f"[Global Unban by {ctx.author}] {reason}")
            unbanned_from.append(guild.name)
        except Exception:
            failed.append(guild.name)

    await ctx.send(
        f"✅ Globally unbanned {user.mention}.\n"
        f"Unbanned in: {', '.join(unbanned_from) or 'None'}\n"
        f"Failed: {', '.join(failed) or 'None'}"
    )

# --- GLOBAL KICK ---
@bot.command()
@commands.has_permissions(kick_members=True)
async def gkick(ctx, user: discord.User, *, reason="No reason provided"):
    if ctx.author.id not in SENIOR_MODS and not can_use_mod_action(ctx.author.id):
        return await ctx.send("⛔ You’ve hit the 3 actions/hour limit. Please wait.")

    kicked_from, failed = [], []
    for guild in bot.guilds:
        member = guild.get_member(user.id)
        if member:
            try:
                await member.kick(reason=f"[Global Kick by {ctx.author}] {reason}")
                kicked_from.append(guild.name)
            except Exception:
                failed.append(guild.name)

    await ctx.send(
        f"✅ Globally kicked {user.mention}.\n"
        f"Kicked from: {', '.join(kicked_from) or 'None'}\n"
        f"Failed: {', '.join(failed) or 'None'}"
    )

# --- GLOBAL TIMEOUT ---
@bot.command()
@commands.has_permissions(moderate_members=True)
async def gtimeout(ctx, user: discord.User, minutes: int, *, reason="No reason provided"):
    if ctx.author.id not in SENIOR_MODS and not can_use_mod_action(ctx.author.id):
        return await ctx.send("⛔ You’ve hit the 3 actions/hour limit. Please wait.")

    until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
    timedout_in, failed = [], []
    for guild in bot.guilds:
        member = guild.get_member(user.id)
        if member:
            try:
                await member.edit(timeout=until, reason=f"[Global Timeout by {ctx.author}] {reason}")
                timedout_in.append(guild.name)
            except Exception:
                failed.append(guild.name)

    await ctx.send(
        f"✅ Globally timed out {user.mention} for {minutes} minutes.\n"
        f"Applied in: {', '.join(timedout_in) or 'None'}\n"
        f"Failed: {', '.join(failed) or 'None'}"
    )

# --- RESET COOLDOWN (SENIOR MODS ONLY) ---
@bot.command()
async def resetcooldown(ctx, user: discord.User):
    if ctx.author.id not in SENIOR_MODS:
        return await ctx.send("⛔ Only senior mods can reset cooldowns.")

    mod_usage[user.id] = []
    await ctx.send(f"✅ Cleared cooldown for {user.mention}")

# --- BOT TOKEN ---
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
