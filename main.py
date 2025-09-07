import os
import discord
from discord.ext import commands
import datetime
import traceback
from keep_alive import keep_alive

keep_alive()

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
SENIOR_MODS = [996087982798950410, 219920365227474944, 267151979849973764, 264538443130994689, 1404975249874751549]  # replace with your user IDs

# Mod roles (who can use the bot at all)
MOD_ROLES = [1391897542576443452]  # Replace with your mod role IDs

def is_mod(member) -> bool:
    """Check if user has any mod role"""
    if not member:
        return False
    user_role_ids = [role.id for role in member.roles]
    return any(role_id in user_role_ids for role_id in MOD_ROLES)

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

# --- READY EVENT ---
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    for guild in bot.guilds:
        print(f'- {guild.name} (ID: {guild.id})')

# --- ERROR HANDLER ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"❌ You don't have permission to use this command. Missing: {', '.join(error.missing_permissions)}")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"❌ I don't have the required permissions. Missing: {', '.join(error.missing_permissions)}")
    elif isinstance(error, commands.UserNotFound):
        await ctx.send("❌ User not found. Make sure you're using the correct user ID or mention.")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")
        print(f"Command error: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

# --- GLOBAL BAN ---
@bot.command()
async def gban(ctx, user: discord.User, *, reason="No reason provided"):
    print(f"GBAN command called by {ctx.author} for {user}")
    
    # Check if user has mod role
    if not is_mod(ctx.author):
        return await ctx.send("⛔ You don't have permission to use this command.")
    
    if ctx.author.id not in SENIOR_MODS and not can_use_mod_action(ctx.author.id):
        return await ctx.send("⛔ You've hit the 3 actions/hour limit. Please wait.")

    banned_from, failed, not_in_guild = [], [], []
    
    # Send initial message
    status_msg = await ctx.send(f"🔄 Processing global ban for {user.mention}...")
    
    for guild in bot.guilds:
        member = guild.get_member(user.id)
        if not member:
            not_in_guild.append(guild.name)
            continue
            
        try:
            # Check if bot can ban in this guild
            if not guild.me.guild_permissions.ban_members:
                failed.append(f"{guild.name} (No ban permission)")
                continue
                
            # Check role hierarchy
            if member.top_role >= guild.me.top_role:
                failed.append(f"{guild.name} (Role hierarchy)")
                continue
                
            await member.ban(reason=f"[Global Ban by {ctx.author}] {reason}")
            banned_from.append(guild.name)
            print(f"Successfully banned {user} from {guild.name}")
            
        except discord.Forbidden:
            failed.append(f"{guild.name} (Forbidden)")
        except discord.HTTPException as e:
            failed.append(f"{guild.name} (HTTP Error: {e})")
        except Exception as e:
            failed.append(f"{guild.name} (Error: {e})")
            print(f"Error banning in {guild.name}: {e}")

    # Update the status message with results
    result_msg = f"✅ Global ban completed for {user.mention}\n"
    if banned_from:
        result_msg += f"**Banned from ({len(banned_from)}):** {', '.join(banned_from)}\n"
    if failed:
        result_msg += f"**Failed ({len(failed)}):** {', '.join(failed)}\n"
    if not_in_guild:
        result_msg += f"**Not in guild ({len(not_in_guild)}):** {', '.join(not_in_guild[:5])}{'...' if len(not_in_guild) > 5 else ''}"
    
    await status_msg.edit(content=result_msg[:2000])  # Discord message limit

# --- GLOBAL UNBAN ---
@bot.command()
async def gunban(ctx, user: discord.User, *, reason="No reason provided"):
    print(f"GUNBAN command called by {ctx.author} for {user}")
    
    # Check if user has mod role
    if not is_mod(ctx.author):
        return await ctx.send("⛔ You don't have permission to use this command.")
    
    if ctx.author.id not in SENIOR_MODS and not can_use_mod_action(ctx.author.id):
        return await ctx.send("⛔ You've hit the 3 actions/hour limit. Please wait.")

    unbanned_from, failed, not_banned = [], [], []
    status_msg = await ctx.send(f"🔄 Processing global unban for {user.mention}...")

    for guild in bot.guilds:
        try:
            if not guild.me.guild_permissions.ban_members:
                failed.append(f"{guild.name} (No ban permission)")
                continue
                
            # Check if user is actually banned
            try:
                ban_entry = await guild.fetch_ban(user)
            except discord.NotFound:
                not_banned.append(guild.name)
                continue
                
            await guild.unban(user, reason=f"[Global Unban by {ctx.author}] {reason}")
            unbanned_from.append(guild.name)
            print(f"Successfully unbanned {user} from {guild.name}")
            
        except discord.Forbidden:
            failed.append(f"{guild.name} (Forbidden)")
        except discord.HTTPException as e:
            failed.append(f"{guild.name} (HTTP Error: {e})")
        except Exception as e:
            failed.append(f"{guild.name} (Error: {e})")
            print(f"Error unbanning in {guild.name}: {e}")

    result_msg = f"✅ Global unban completed for {user.mention}\n"
    if unbanned_from:
        result_msg += f"**Unbanned from ({len(unbanned_from)}):** {', '.join(unbanned_from)}\n"
    if failed:
        result_msg += f"**Failed ({len(failed)}):** {', '.join(failed)}\n"
    if not_banned:
        result_msg += f"**Not banned ({len(not_banned)}):** {', '.join(not_banned[:5])}{'...' if len(not_banned) > 5 else ''}"
    
    await status_msg.edit(content=result_msg[:2000])

# --- GLOBAL KICK ---
@bot.command()
async def gkick(ctx, user: discord.User, *, reason="No reason provided"):
    print(f"GKICK command called by {ctx.author} for {user}")
    
    # Check if user has mod role
    if not is_mod(ctx.author):
        return await ctx.send("⛔ You don't have permission to use this command.")
    
    if ctx.author.id not in SENIOR_MODS and not can_use_mod_action(ctx.author.id):
        return await ctx.send("⛔ You've hit the 3 actions/hour limit. Please wait.")

    kicked_from, failed, not_in_guild = [], [], []
    status_msg = await ctx.send(f"🔄 Processing global kick for {user.mention}...")

    for guild in bot.guilds:
        member = guild.get_member(user.id)
        if not member:
            not_in_guild.append(guild.name)
            continue
            
        try:
            if not guild.me.guild_permissions.kick_members:
                failed.append(f"{guild.name} (No kick permission)")
                continue
                
            if member.top_role >= guild.me.top_role:
                failed.append(f"{guild.name} (Role hierarchy)")
                continue
                
            await member.kick(reason=f"[Global Kick by {ctx.author}] {reason}")
            kicked_from.append(guild.name)
            print(f"Successfully kicked {user} from {guild.name}")
            
        except discord.Forbidden:
            failed.append(f"{guild.name} (Forbidden)")
        except discord.HTTPException as e:
            failed.append(f"{guild.name} (HTTP Error: {e})")
        except Exception as e:
            failed.append(f"{guild.name} (Error: {e})")
            print(f"Error kicking in {guild.name}: {e}")

    result_msg = f"✅ Global kick completed for {user.mention}\n"
    if kicked_from:
        result_msg += f"**Kicked from ({len(kicked_from)}):** {', '.join(kicked_from)}\n"
    if failed:
        result_msg += f"**Failed ({len(failed)}):** {', '.join(failed)}\n"
    if not_in_guild:
        result_msg += f"**Not in guild ({len(not_in_guild)}):** {', '.join(not_in_guild[:5])}{'...' if len(not_in_guild) > 5 else ''}"
    
    await status_msg.edit(content=result_msg[:2000])

# --- GLOBAL TIMEOUT ---
@bot.command()
async def gtimeout(ctx, user: discord.User, minutes: int, *, reason="No reason provided"):
    print(f"GTIMEOUT command called by {ctx.author} for {user} ({minutes} minutes)")
    
    # Check if user has mod role
    if not is_mod(ctx.author):
        return await ctx.send("⛔ You don't have permission to use this command.")
    
    if ctx.author.id not in SENIOR_MODS and not can_use_mod_action(ctx.author.id):
        return await ctx.send("⛔ You've hit the 3 actions/hour limit. Please wait.")

    if minutes <= 0 or minutes > 40320:  # Max 28 days
        return await ctx.send("❌ Timeout duration must be between 1 and 40320 minutes (28 days).")

    until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
    timedout_in, failed, not_in_guild = [], [], []
    status_msg = await ctx.send(f"🔄 Processing global timeout for {user.mention}...")

    for guild in bot.guilds:
        member = guild.get_member(user.id)
        if not member:
            not_in_guild.append(guild.name)
            continue
            
        try:
            if not guild.me.guild_permissions.moderate_members:
                failed.append(f"{guild.name} (No timeout permission)")
                continue
                
            if member.top_role >= guild.me.top_role:
                failed.append(f"{guild.name} (Role hierarchy)")
                continue
                
            await member.edit(timeout=until, reason=f"[Global Timeout by {ctx.author}] {reason}")
            timedout_in.append(guild.name)
            print(f"Successfully timed out {user} in {guild.name}")
            
        except discord.Forbidden:
            failed.append(f"{guild.name} (Forbidden)")
        except discord.HTTPException as e:
            failed.append(f"{guild.name} (HTTP Error: {e})")
        except Exception as e:
            failed.append(f"{guild.name} (Error: {e})")
            print(f"Error timing out in {guild.name}: {e}")

    result_msg = f"✅ Global timeout completed for {user.mention} ({minutes} minutes)\n"
    if timedout_in:
        result_msg += f"**Timed out in ({len(timedout_in)}):** {', '.join(timedout_in)}\n"
    if failed:
        result_msg += f"**Failed ({len(failed)}):** {', '.join(failed)}\n"
    if not_in_guild:
        result_msg += f"**Not in guild ({len(not_in_guild)}):** {', '.join(not_in_guild[:5])}{'...' if len(not_in_guild) > 5 else ''}"
    
    await status_msg.edit(content=result_msg[:2000])

# --- RESET COOLDOWN (SENIOR MODS ONLY) ---
@bot.command()
async def resetcooldown(ctx, user: discord.User):
    if ctx.author.id not in SENIOR_MODS:
        return await ctx.send("⛔ Only senior mods can reset cooldowns.")

    mod_usage[user.id] = []
    await ctx.send(f"✅ Cleared cooldown for {user.mention}")

# --- DEBUG COMMAND ---
@bot.command()
async def debugperms(ctx, guild_id: int = None):
    """Check bot permissions in a specific guild or current guild"""
    if ctx.author.id not in SENIOR_MODS:
        return await ctx.send("⛔ Only senior mods can use debug commands.")
    
    target_guild = bot.get_guild(guild_id) if guild_id else ctx.guild
    if not target_guild:
        return await ctx.send("❌ Guild not found.")
    
    me = target_guild.me
    perms = me.guild_permissions
    
    relevant_perms = {
        'ban_members': perms.ban_members,
        'kick_members': perms.kick_members,
        'moderate_members': perms.moderate_members,
        'administrator': perms.administrator
    }
    
    perm_status = '\n'.join([f"{perm}: {'✅' if has_perm else '❌'}" 
                            for perm, has_perm in relevant_perms.items()])
    
    await ctx.send(f"**Bot permissions in {target_guild.name}:**\n```{perm_status}```\n"
                  f"**Bot's highest role:** {me.top_role.name} (pos: {me.top_role.position})")

# --- BOT TOKEN ---
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERROR: DISCORD_TOKEN environment variable not set!")
    exit(1)

bot.run(TOKEN)
