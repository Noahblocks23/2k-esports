import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import os
import random
from dotenv import load_dotenv
 

TOKEN = os.getenv("MTUyMTg0MzY1NjQxNDQ2MjA0NA.GdkdU3.5Hg4mm-C50d8itia-3kRgWNkiurcCZCms5JuRs")

AUTO_ROLE_NAME     = "Community"
ROSTER_ROLE_NAME   = "Roster"
RAID_ALERT_USERS   = ["noahblocks23","Oztix"]
NEW_ACCOUNT_DAYS   = 7          # accounts younger than this get kicked during an active raid
MILESTONE_STEP     = 50         # celebrate every 50 members
TICKET_SUPPORT_ROLE_ID = 1521520766141595689

TICKET_CATEGORY_MAP = {
    "roster": 1442706134434844682,
    "staff": 1522361957414469894,
    "content_creator": 1442706134640099423,
    "gfx_vfx": 1442706134640099426,
    "investment": 1442706134828978256,
    "business": 1442706134040449143,
    "report": 1442706134040449142,
    "general_support": 1522365882360266883,
}
ADMIN_ROLES = [
    "2K bot admin",
    "",
    "",
    "",
    "",
    "",
]

STAFF_ROLES = ADMIN_ROLES + [
    "",
    "",
    "",
    "",
    "",
    "",
]

INVITE_STRINGS   = ["discord.gg/", "discord.com/invite/"]
TICKET_SUPPORT_ROLE_NAMES = ["Ticket Support", "Support"] + ADMIN_ROLES

raid_active      = {}
locked_channels  = {}
join_timestamps  = {}
warn_db          = {}
modmail_map      = {}
xp_db            = {}
last_xp_time     = {}
spam_tracker     = {}
ticket_claims    = {}   # channel_id -> staff user_id who claimed it
staff_stats      = {}   # staff user_id (str) -> {"tickets_claimed": int, "messages_sent": int}


def bump_stat(uid, field, amount=1):
    uid = str(uid)
    if uid not in staff_stats:
        staff_stats[uid] = {"tickets_claimed": 0, "messages_sent": 0}
    staff_stats[uid][field] += amount

TICKET_OPTIONS = {
    "roster": {
        "emoji": "🏀", "label": "Roster Application", "description": "Apply to join the 2K roster",
        "color": discord.Color.orange(), "age_required": True, "resume_required": False,
    },
    "staff": {
        "emoji": "🛡️", "label": "Staff Application", "description": "Apply to become staff (resume required)",
        "color": discord.Color.blue(), "age_required": True, "resume_required": True,
    },
    "content_creator": {
        "emoji": "🎥", "label": "Content Creator / Streamer", "description": "Apply to join as a content creator/streamer for 2K eSports",
        "color": discord.Color.purple(), "age_required": True, "resume_required": False,
    },
    "investment": {
        "emoji": "💰", "label": "Investment", "description": "Invest for 2K eSports",
        "color": discord.Color.gold(), "age_required": False, "resume_required": False,
    },
    "business": {
        "emoji": "🤝", "label": "Business Inquiry", "description": "Partnerships and business enquiries",
        "color": discord.Color.blurple(), "age_required": False, "resume_required": False,
    },
}

TICKET_QUESTIONS = {
    "roster": [
        "What is your name?",
        "How old are you?",
        "What is your PSN / XBOX / GAMERTAG",
        "What game are you applying for?",
        "Please send your fortnite tracker.",
         "How many hours per week can you dedicate to scrimmages and games?",
        "Why do you want to join the 2K Esports roster?",
    ],
    "staff": [
        "What is your name?",
        "How old are you?",
        "What staff position do you desire? (Human Resources, manegment, chat moderator, etc)",
        "Please send your resume / previous experience.",
        "How many hours per week can you actively moderate / work for us?",
        "Why do you want to be staff at 2K Esports?",
    ],
    "content_creator": [
        "What is your name?",
        "What type of content / streams do you create? YouTube, TikTok, Twitch, etc.",
        "How many followers or subscribers do you have?",
        "Share links to your content or social media.",
        "Please send a screenshot of you being able to edit your social media accounts to verify.",
        "Why do you want to join 2K as a Content Creator / Streamer?"
    ],
    "investment": [
        "What is your name and contact information?",
        "What is the nature of your investment interest?",
        "What budget or resources are you looking to invest?",
        "Have you previously invested in esports or gaming organisations?",
        "What are you hoping to gain from this partnership?",
    ],
    "business": [
        "What is your name and organisation?",
        "What is the nature of your business inquiry?",
        "What are you looking to achieve through this partnership?",
        "How can 2K Esports benefit from working with you?",
        "What is the best way for our team to contact you?",
    ],
}

WELCOME_MESSAGES = [
    "Welcome to **2K Esports**, {mention}! Glad to have you here!",
    "Hey {mention}! Welcome to **2K Esports**! You are our **#{count}** member. Let's hoop!",
    "{mention} just joined **2K Esports**! You are member **#{count}**. Welcome to the squad!",
    "A new baller has arrived! Welcome {mention} to **2K Esports**! You are member **#{count}**.",
    "Everyone welcome {mention} to **2K Esports**! You are member **#{count}**. GG!",
]

GOODBYE_MESSAGES = [
    "{name} has left 2K Esports. We hope to see you again!",
    "{name} just left the server. Take care and good luck!",
    "It looks like {name} has left us. Farewell!",
    "{name} has left 2K Esports. Thanks for being part of the squad!",
]


def find_ch(guild, name):
    c = discord.utils.get(guild.text_channels, name=name)
    if c:
        return c
    for ch in guild.text_channels:
        if name.lower() in ch.name.lower():
            return ch
    return None


async def find_users_by_name(guild, usernames):
    return [m for m in guild.members if m.name.lower() in [u.lower() for u in usernames]]


def is_staff(member):
    return any(role.name in STAFF_ROLES for role in member.roles) or member.guild_permissions.administrator


def is_admin(member):
    return any(role.name in ADMIN_ROLES for role in member.roles) or member.guild_permissions.administrator


def is_founder(member):
    return any(role.name in ["Founder", "Co-Founder", "Co Founder", "Owner"] for role in member.roles) \
        or member.guild_permissions.administrator

def is_ticket_support(member):
    return any(r.id == TICKET_SUPPORT_ROLE_ID for r in member.roles) or member.guild_permissions.administrator

def xp_for_level(level):
    return 100 * level * level


def get_level(xp):
    level = 0
    while xp >= xp_for_level(level + 1):
        level += 1
    return level


# ══════════════════════════════════════════════
#  RAID STOP BUTTON
# ══════════════════════════════════════════════

class StopRaidView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=300)
        self.guild = guild

    @discord.ui.button(label="YES — Stop Raid and Unlock", style=discord.ButtonStyle.success, emoji="✅")
    async def stop_raid(self, interaction, button):
        guild_id = self.guild.id
        raid_active[guild_id] = False
        restored = 0
        if guild_id in locked_channels:
            for channel_id, old_perms in locked_channels[guild_id].items():
                ch = self.guild.get_channel(channel_id)
                if ch:
                    try:
                        await ch.set_permissions(self.guild.default_role, send_messages=old_perms)
                        restored += 1
                    except Exception:
                        pass
            locked_channels.pop(guild_id, None)
        e = discord.Embed(title="Raid Stopped", description="Raid stopped. " + str(restored) + " channels unlocked.", color=discord.Color.green())
        e.set_footer(text="2K Esports | Anti-Raid")
        e.timestamp = datetime.utcnow()
        await interaction.response.edit_message(embed=e, view=None)
        lc = find_ch(self.guild, "defense-logs")
        if lc:
            le = discord.Embed(title="Raid Ended", description="Stopped by " + str(interaction.user) + ". " + str(restored) + " channels unlocked.", color=discord.Color.green())
            le.timestamp = datetime.utcnow()
            await lc.send(embed=le)

    @discord.ui.button(label="NO — Keep Lockdown", style=discord.ButtonStyle.danger, emoji="🔒")
    async def keep_lockdown(self, interaction, button):
        e = discord.Embed(title="Lockdown Continues", description="Server remains locked. Use the button again when ready.", color=discord.Color.red())
        e.set_footer(text="2K Esports | Anti-Raid")
        await interaction.response.edit_message(embed=e, view=None)


async def lockdown_server(guild, reason="Raid detected", kick_new_accounts=False):
    guild_id = guild.id
    raid_active[guild_id] = True
    locked_channels[guild_id] = {}
    for channel in guild.text_channels:
        try:
            current = channel.overwrites_for(guild.default_role)
            locked_channels[guild_id][channel.id] = current.send_messages
            await channel.set_permissions(guild.default_role, send_messages=False)
        except Exception:
            pass

    kicked = 0
    if kick_new_accounts:
        cutoff = datetime.utcnow() - timedelta(days=NEW_ACCOUNT_DAYS)
        for member in guild.members:
            if member.bot or is_staff(member):
                continue
            if member.created_at.replace(tzinfo=None) > cutoff:
                try:
                    await member.kick(reason="Anti-raid: new account during active raid")
                    kicked += 1
                except Exception:
                    pass

    alert = discord.Embed(
        title="RAID ALERT — SERVER LOCKED DOWN",
        description="Raid detected!\n\nAll channels locked.\nReason: " + reason + ("\nKicked **" + str(kicked) + "** new accounts (under " + str(NEW_ACCOUNT_DAYS) + " days old)." if kick_new_accounts else "") + "\n\nStaff have been notified.",
        color=discord.Color.dark_red(),
    )
    alert.set_footer(text="2K Esports | Anti-Raid")
    alert.timestamp = datetime.utcnow()
    lc = find_ch(guild, "defense-logs")
    if lc:
        await lc.send(embed=alert)

    for user in await find_users_by_name(guild, RAID_ALERT_USERS):
        dm = discord.Embed(
            title="RAID ALERT",
            description="A raid has been detected on **" + guild.name + "**!\n\nReason: " + reason + "\n\nAll channels are locked.\n\nWould you like to stop the raid and unlock all channels?",
            color=discord.Color.dark_red(),
        )
        dm.set_footer(text="2K Esports | Anti-Raid")
        dm.timestamp = datetime.utcnow()
        try:
            await user.send(embed=dm, view=StopRaidView(guild))
        except discord.Forbidden:
            pass


# ══════════════════════════════════════════════
#  TICKET VIEWS
# ══════════════════════════════════════════════

class TicketTypeButton(discord.ui.Button):
    def __init__(self, ttype, cfg):
        super().__init__(
            label=cfg["label"],
            emoji=cfg["emoji"],
            style=discord.ButtonStyle.primary,
            custom_id="2k_ticket_" + ttype,
        )
        self.ttype = ttype

    async def callback(self, interaction):
        await interaction.response.defer(ephemeral=True)
        await open_ticket(interaction, self.ttype)


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # Explicit button per scenario — Roster, Staff Application, Content Creator, Investment, Business Inquiry
        for ttype, cfg in TICKET_OPTIONS.items():
            self.add_item(TicketTypeButton(ttype, cfg))


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="2k_close")
    async def close(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Only admins can close tickets!", ephemeral=True)
            return
        ticket_claims.pop(interaction.channel.id, None)
        await interaction.response.send_message("Saving transcript and closing in 5 seconds...")
        await save_transcript(interaction.channel)
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.success, emoji="✅", custom_id="2k_claim")
    async def claim(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Only admins can claim tickets!", ephemeral=True)
            return

        existing_claim = ticket_claims.get(interaction.channel.id)
        if existing_claim:
            claimer = interaction.guild.get_member(existing_claim)
            claimer_name = claimer.mention if claimer else "another staff member"
            await interaction.response.send_message("This ticket is already claimed by " + claimer_name + ".", ephemeral=True)
            return

        ticket_claims[interaction.channel.id] = interaction.user.id
        bump_stat(interaction.user.id, "tickets_claimed")

        e = discord.Embed(
            title="Ticket Claimed",
            description=(
                interaction.user.mention + " has claimed this ticket and will assist you shortly!\n\n"
                "Other staff can still view this channel, but " + interaction.user.mention + " is now handling it."
            ),
            color=discord.Color.green()
        )
        e.set_footer(text="2K Esports | Ticket System")
        await interaction.response.send_message(embed=e)


async def save_transcript(channel):
    guild = channel.guild
    lc = find_ch(guild, "mod-logs")
    if not lc:
        return
    lines = []
    async for msg in channel.history(limit=200, oldest_first=True):
        if msg.author.bot and not msg.embeds:
            continue
        content = msg.content
        if msg.embeds:
            content += " [embed] " + (msg.embeds[0].description or "")
        lines.append(str(msg.author) + ": " + content)
    transcript = "\n".join(lines)[-3800:] if lines else "No messages recorded."
    e = discord.Embed(title="Ticket Transcript — " + channel.name, description="```" + transcript + "```", color=discord.Color.dark_grey())
    e.set_footer(text="2K Esports | Ticket Transcript")
    e.timestamp = datetime.utcnow()
    try:
        await lc.send(embed=e)
    except Exception:
        pass


async def open_ticket(interaction, ttype):
    guild  = interaction.guild
    member = interaction.user
    cfg    = TICKET_OPTIONS[ttype]

    cat_id = TICKET_CATEGORY_MAP.get(ttype)

    cat = None
    if cat_id:
        cat = guild.get_channel(cat_id)

    if not isinstance(cat, discord.CategoryChannel):
        cat = discord.utils.get(guild.categories, name="Tickets")
        if cat is None:
            cat = await guild.create_category("Tickets")

    cname = ttype.replace("_", "-") + "-" + member.name.lower()

    if discord.utils.get(cat.text_channels, name=cname):
        await interaction.followup.send(
            "You already have an open ticket for this category!",
            ephemeral=True
        )
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
    }

    for rname in STAFF_ROLES:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            overwrites[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    ch = await cat.create_text_channel(name=cname, overwrites=overwrites)

    age_note = "\n⚠️ 13+ only." if cfg["age_required"] else ""
    resume_note = "\n📄 Resume required." if cfg["resume_required"] else ""

    embed = discord.Embed(
        title=cfg["emoji"] + " " + cfg["label"],
        description=member.mention + " — please wait for staff." + age_note + resume_note,
        color=cfg["color"],
    )
    embed.set_footer(text="2K Esports | Ticket System")

    await ch.send(embed=embed, view=TicketControlView())

    await interaction.followup.send("Ticket created: " + ch.mention, ephemeral=True)


# ══════════════════════════════════════════════
#  MODMAIL
# ══════════════════════════════════════════════

async def create_modmail_channel(guild, member, message_content):
    cat = discord.utils.get(guild.categories, name="ModMail")
    if cat is None:
        cat = await guild.create_category("ModMail")

    cname    = "modmail-" + member.name.lower()
    existing = find_ch(guild, cname)
    if existing:
        e = discord.Embed(description=message_content, color=discord.Color.from_rgb(255, 140, 0))
        e.set_author(name=str(member), icon_url=member.display_avatar.url)
        e.set_footer(text="ModMail | User replied")
        e.timestamp = datetime.utcnow()
        await existing.send(embed=e)
        return existing

    ow = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me:           discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
    }
    for rname in ["Founder", "Co-Founder", "Co Founder", "Owner", "Admin"]:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            ow[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    ch = await cat.create_text_channel(name=cname, overwrites=ow)
    modmail_map[ch.id] = member.id

    e = discord.Embed(
        title="New ModMail",
        description="**From:** " + str(member) + " (" + str(member.id) + ")\n\n**Message:**\n" + message_content,
        color=discord.Color.from_rgb(255, 140, 0),
    )
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text="2K Esports | ModMail")
    e.timestamp = datetime.utcnow()
    await ch.send(embed=e)

    for rname in ["Founder", "Co-Founder", "Co Founder", "Owner"]:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            await ch.send(r.mention + " — New ModMail received!", delete_after=10)
            break
    return ch


# ══════════════════════════════════════════════
#  SUGGESTIONS & GIVEAWAYS
# ══════════════════════════════════════════════

class SuggestionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Upvote", style=discord.ButtonStyle.success, emoji="👍", custom_id="2k_upvote")
    async def upvote(self, interaction, button):
        await interaction.response.send_message("You upvoted this suggestion!", ephemeral=True)

    @discord.ui.button(label="Downvote", style=discord.ButtonStyle.danger, emoji="👎", custom_id="2k_downvote")
    async def downvote(self, interaction, button):
        await interaction.response.send_message("You downvoted this suggestion!", ephemeral=True)


# ══════════════════════════════════════════════
#  BOT SETUP
# ══════════════════════════════════════════════

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="k?", intents=intents, help_command=None)


# ══════════════════════════════════════════════
#  EVENTS
# ══════════════════════════════════════════════

@bot.event
async def on_member_join(member):
    guild    = member.guild
    guild_id = guild.id

    auto_role = discord.utils.get(guild.roles, name=AUTO_ROLE_NAME)
    if auto_role:
        try:
            await member.add_roles(auto_role)
        except discord.Forbidden:
            pass

    now = datetime.utcnow().timestamp()
    if guild_id not in join_timestamps:
        join_timestamps[guild_id] = []
    join_timestamps[guild_id].append(now)
    join_timestamps[guild_id] = [t for t in join_timestamps[guild_id] if now - t < 10]
    if len(join_timestamps[guild_id]) >= 5 and not raid_active.get(guild_id, False):
        await lockdown_server(guild, reason="Mass joins — " + str(len(join_timestamps[guild_id])) + " users joined in 10 seconds", kick_new_accounts=True)

    try:
        dm = discord.Embed(
            title="Welcome to 2K Esports!",
            description=(
                "Hey " + member.mention + "! We are glad you joined us.\n\n"
                "Head to **#tickets** to apply for roster, staff, or reach out to us!\n"
                "DM this bot at any time to open a private ModMail with our staff.\n"
                "Chat around the server to earn XP and level up — check `k?rank`!\n\n"
                "Let's hoop!"
            ),
            color=discord.Color.from_rgb(255, 140, 0),
        )
        if guild.icon:
            dm.set_thumbnail(url=guild.icon.url)
        dm.set_footer(text="2K Esports | Welcome")
        dm.timestamp = datetime.utcnow()
        await member.send(embed=dm)
    except discord.Forbidden:
        pass

    wc = find_ch(guild, "welcome")
    if wc:
        msg = random.choice(WELCOME_MESSAGES).format(mention=member.mention, count=guild.member_count)
        w = discord.Embed(description=msg, color=discord.Color.from_rgb(255, 140, 0))
        w.set_author(name=str(member), icon_url=member.display_avatar.url)
        w.set_thumbnail(url=member.display_avatar.url)
        w.add_field(name="Account Age",  value=discord.utils.format_dt(member.created_at, style="R"), inline=True)
        w.add_field(name="Member Count", value=str(guild.member_count), inline=True)
        w.add_field(name="User ID",      value=str(member.id), inline=True)
        w.set_footer(text="2K Esports | Welcome System")
        w.timestamp = datetime.utcnow()
        await wc.send(embed=w)

        if guild.member_count % MILESTONE_STEP == 0:
            milestone_e = discord.Embed(
                title="🎉 Milestone Reached!",
                description="**2K Esports** just hit **" + str(guild.member_count) + " members**! Thank you all for being part of the squad!",
                color=discord.Color.gold(),
            )
            milestone_e.set_footer(text="2K Esports | Milestone")
            await wc.send(embed=milestone_e)

    lc = find_ch(guild, "mod-logs")
    if lc:
        le = discord.Embed(title="Member Joined", description=str(member) + " joined.", color=discord.Color.green())
        le.set_thumbnail(url=member.display_avatar.url)
        le.add_field(name="User ID",      value=str(member.id), inline=True)
        le.add_field(name="Account Age",  value=discord.utils.format_dt(member.created_at, style="R"), inline=True)
        le.add_field(name="Member Count", value=str(guild.member_count), inline=True)
        le.set_footer(text="2K Esports | Mod Logs")
        le.timestamp = datetime.utcnow()
        await lc.send(embed=le)


@bot.event
async def on_member_remove(member):
    guild = member.guild
    gc    = find_ch(guild, "goodbye")
    if gc:
        msg   = random.choice(GOODBYE_MESSAGES).format(name=member.name)
        roles = sorted([r for r in member.roles if r.name != "@everyone"], key=lambda r: r.position, reverse=True)
        g = discord.Embed(description=msg, color=discord.Color.red())
        g.set_author(name=str(member), icon_url=member.display_avatar.url)
        g.set_thumbnail(url=member.display_avatar.url)
        g.add_field(name="User ID",  value=str(member.id), inline=True)
        g.add_field(name="Top Role", value=roles[0].name if roles else "None", inline=True)
        g.add_field(name="Joined",   value=discord.utils.format_dt(member.joined_at, style="R") if member.joined_at else "Unknown", inline=True)
        g.add_field(name="Members",  value=str(guild.member_count), inline=True)
        g.set_footer(text="2K Esports | Goodbye System")
        g.timestamp = datetime.utcnow()
        await gc.send(embed=g)

    lc = find_ch(guild, "mod-logs")
    if lc:
        le = discord.Embed(title="Member Left", description=str(member) + " left the server.", color=discord.Color.red())
        le.add_field(name="User ID", value=str(member.id), inline=True)
        le.add_field(name="Joined",  value=discord.utils.format_dt(member.joined_at, style="R") if member.joined_at else "Unknown", inline=True)
        le.set_footer(text="2K Esports | Mod Logs")
        le.timestamp = datetime.utcnow()
        await lc.send(embed=le)


@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    lc = find_ch(message.guild, "mod-logs")
    if lc:
        e = discord.Embed(title="Message Deleted", description="By " + str(message.author) + " in " + message.channel.mention, color=discord.Color.orange())
        e.add_field(name="Content", value=message.content or "No content", inline=False)
        e.set_footer(text="2K Esports | Mod Logs")
        e.timestamp = datetime.utcnow()
        await lc.send(embed=e)


@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return
    lc = find_ch(before.guild, "mod-logs")
    if lc:
        e = discord.Embed(title="Message Edited", description="By " + str(before.author) + " in " + before.channel.mention, color=discord.Color.yellow())
        e.add_field(name="Before", value=before.content or "Empty", inline=False)
        e.add_field(name="After",  value=after.content or "Empty", inline=False)
        e.set_footer(text="2K Esports | Mod Logs")
        e.timestamp = datetime.utcnow()
        await lc.send(embed=e)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # MODMAIL — DM handler
    if isinstance(message.channel, discord.DMChannel):
        for guild in bot.guilds:
            member = guild.get_member(message.author.id)
            if member:
                await create_modmail_channel(guild, message.author, message.content)
                try:
                    conf = discord.Embed(title="ModMail Sent", description="Your message has been received by **" + guild.name + "** staff.\n\nA staff member will respond shortly.", color=discord.Color.green())
                    conf.set_footer(text="2K Esports | ModMail")
                    conf.timestamp = datetime.utcnow()
                    await message.author.send(embed=conf)
                except discord.Forbidden:
                    pass
                return

    # MODMAIL — Staff reply
    if message.guild and message.channel.id in modmail_map:
        if not is_admin(message.author):
            await message.delete()
            try:
                await message.author.send("Only Admin and above can type in ModMail channels.")
            except discord.Forbidden:
                pass
            return
        user_id = modmail_map[message.channel.id]
        user    = message.guild.get_member(user_id)
        if user:
            try:
                reply = discord.Embed(title="Reply from 2K Esports Staff", description=message.content, color=discord.Color.from_rgb(255, 140, 0))
                reply.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
                reply.set_footer(text="2K Esports | ModMail")
                reply.timestamp = datetime.utcnow()
                await user.send(embed=reply)
                await message.add_reaction("✅")
            except discord.Forbidden:
                await message.channel.send("Could not DM that user — they may have DMs disabled.", delete_after=5)
        return

    if message.guild:
        # MASS MENTION check
        if len(message.mentions) >= 5:
            await message.delete()
            try:
                await message.author.send("Your message was removed for mass mentioning.")
            except discord.Forbidden:
                pass
            lc = find_ch(message.guild, "defense-logs")
            if lc:
                e = discord.Embed(title="Mass Mention Blocked", description=str(message.author) + " tried to mention " + str(len(message.mentions)) + " users.", color=discord.Color.dark_red())
                e.timestamp = datetime.utcnow()
                await lc.send(embed=e)
            return

        # INVITE LINK check
        has_invite = any(inv in message.content for inv in INVITE_STRINGS)
        if has_invite and not is_staff(message.author):
            await message.delete()
            try:
                await message.author.send("Posting Discord invite links is not allowed in this server.")
            except discord.Forbidden:
                pass
            lc = find_ch(message.guild, "defense-logs")
            if lc:
                e = discord.Embed(title="Invite Link Blocked", description=str(message.author) + " posted an invite link.", color=discord.Color.dark_red())
                e.timestamp = datetime.utcnow()
                await lc.send(embed=e)
            return

        # SPAM check — same message repeated 4+ times quickly
        key = str(message.author.id) + "-" + str(message.guild.id)
        now = datetime.utcnow().timestamp()
        history = spam_tracker.get(key, [])
        history = [h for h in history if now - h["time"] < 8]
        history.append({"content": message.content, "time": now})
        spam_tracker[key] = history
        repeats = [h for h in history if h["content"] == message.content]
        if len(repeats) >= 4 and not is_staff(message.author):
            await message.delete()
            try:
                await message.author.send("Your message was removed for spamming.")
            except discord.Forbidden:
                pass
            spam_tracker[key] = []
            return

        
        # STAFF ACTIVITY TRACKING
# Counts ALL staff messages since the last reset
if is_staff(message.author):
    bump_stat(message.author.id, "messages_sent")

        # XP SYSTEM
        uid = str(message.author.id)
        last = last_xp_time.get(uid, 0)
        if now - last > 60:
            last_xp_time[uid] = now
            old_xp    = xp_db.get(uid, 0)
            old_level = get_level(old_xp)
            new_xp    = old_xp + random.randint(10, 20)
            xp_db[uid] = new_xp
            new_level  = get_level(new_xp)
            if new_level > old_level:
                lvl_e = discord.Embed(
                    title="Level Up!",
                    description=message.author.mention + " just reached **Level " + str(new_level) + "**!",
                    color=discord.Color.from_rgb(255, 140, 0),
                )
                lvl_e.set_footer(text="2K Esports | XP System")
                try:
                    await message.channel.send(embed=lvl_e, delete_after=10)
                except Exception:
                    pass

    await bot.process_commands(message)


# ══════════════════════════════════════════════
#  PREFIX COMMANDS
# ══════════════════════════════════════════════

@bot.command(name="help")
async def help_cmd(ctx):
    e = discord.Embed(title="2K Esports Bot", description="Prefix: `k?`", color=discord.Color.from_rgb(255, 140, 0))
    e.add_field(name="k?userinfo @user",   value="View member info",         inline=False)
    e.add_field(name="k?serverinfo",       value="View server info",         inline=False)
    e.add_field(name="k?avatar @user",     value="View member avatar",       inline=False)
    e.add_field(name="k?rank @user",       value="View XP and level",       inline=False)
    e.add_field(name="k?leaderboard",      value="Top 10 XP leaderboard",    inline=False)
    e.add_field(name="k?roster",           value="View the current roster", inline=False)
    e.add_field(name="k?ping",             value="Bot latency",              inline=False)
    e.add_field(name="k?suggest <idea>",   value="Submit a suggestion",      inline=False)
    e.add_field(name="k?poll <question>",  value="Create a poll",            inline=False)
    e.add_field(name="k?giveaway <mins> <prize>", value="Start a giveaway (Staff)", inline=False)
    e.add_field(name="k?8ball <question>", value="Magic 8 ball",             inline=False)
    e.add_field(name="k?coinflip",         value="Flip a coin",              inline=False)
    e.add_field(name="k?roll",             value="Roll a dice",              inline=False)
    e.add_field(name="k?warn @user",       value="Warn a member (Staff)",    inline=False)
    e.add_field(name="k?warnings @user",   value="View warnings",            inline=False)
    e.add_field(name="k?clearwarns @user", value="Clear warnings (Staff)",   inline=False)
    e.add_field(name="k?kick @user",       value="Kick a member (Staff)",    inline=False)
    e.add_field(name="k?ban @user",        value="Ban a member (Staff)",     inline=False)
    e.add_field(name="k?mute @user",       value="Mute a member (Staff)",    inline=False)
    e.add_field(name="k?clear 10",         value="Delete messages (Staff)",  inline=False)
    e.add_field(name="k?closemodmail",     value="Close ModMail (Admin)",    inline=False)
    e.add_field(name="/setup",             value="First time setup (Admin)", inline=False)
    e.add_field(name="/panel",             value="Re-post ticket panel",     inline=False)
    e.add_field(name="/testraid",          value="Test anti-raid (Admin)",   inline=False)
    e.add_field(name="/lockdown",          value="Lock server (Admin)",      inline=False)
    e.add_field(name="/unlock",            value="Unlock server (Admin)",    inline=False)
    e.set_footer(text="2K Esports | DM the bot to open a ModMail")
    await ctx.send(embed=e)


@bot.command(name="ping")
async def ping(ctx):
    e = discord.Embed(title="Pong!", description="Latency: **" + str(round(bot.latency * 1000)) + "ms**", color=discord.Color.green())
    e.set_footer(text="2K Esports")
    await ctx.send(embed=e)


@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    t  = member or ctx.author
    rs = sorted([r for r in t.roles if r.name != "@everyone"], key=lambda r: r.position, reverse=True)
    tr = rs[0] if rs else None
    sm = {discord.Status.online: "Online", discord.Status.idle: "Idle", discord.Status.dnd: "Do Not Disturb", discord.Status.offline: "Offline"}
    e  = discord.Embed(title=t.display_name, color=tr.color if tr else discord.Color.from_rgb(255, 140, 0))
    e.set_thumbnail(url=t.display_avatar.url)
    e.add_field(name="Username",       value=str(t), inline=True)
    e.add_field(name="User ID",        value=str(t.id), inline=True)
    e.add_field(name="Status",         value=sm.get(t.status, "Offline"), inline=True)
    e.add_field(name="Top Role",       value=tr.mention if tr else "None", inline=True)
    e.add_field(name="Joined Server",  value=discord.utils.format_dt(t.joined_at, style="R") if t.joined_at else "Unknown", inline=True)
    e.add_field(name="Joined Discord", value=discord.utils.format_dt(t.created_at, style="R"), inline=True)
    e.add_field(name="Roles " + str(len(rs)), value=" ".join(r.mention for r in rs[:8]) or "None", inline=False)
    e.set_footer(text="2K Esports | Requested by " + ctx.author.display_name)
    e.timestamp = datetime.utcnow()
    await ctx.send(embed=e)


@bot.command(name="serverinfo")
async def serverinfo(ctx):
    g = ctx.guild
    e = discord.Embed(title=g.name, color=discord.Color.from_rgb(255, 140, 0))
    if g.icon:
        e.set_thumbnail(url=g.icon.url)
    e.add_field(name="Server ID",  value=str(g.id), inline=True)
    e.add_field(name="Owner",      value=str(g.owner), inline=True)
    e.add_field(name="Members",    value=str(g.member_count), inline=True)
    e.add_field(name="Channels",   value=str(len(g.text_channels)), inline=True)
    e.add_field(name="Roles",      value=str(len(g.roles)), inline=True)
    e.add_field(name="Boosts",     value="Level " + str(g.premium_tier) + " with " + str(g.premium_subscription_count) + " boosts", inline=True)
    e.add_field(name="Created",    value=discord.utils.format_dt(g.created_at, style="R"), inline=True)
    e.set_footer(text="2K Esports | Server Info")
    e.timestamp = datetime.utcnow()
    await ctx.send(embed=e)


@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    t = member or ctx.author
    e = discord.Embed(title=t.display_name + " Avatar", color=discord.Color.from_rgb(255, 140, 0))
    e.set_image(url=t.display_avatar.url)
    e.set_footer(text="2K Esports")
    await ctx.send(embed=e)


@bot.command(name="rank")
async def rank(ctx, member: discord.Member = None):
    t   = member or ctx.author
    uid = str(t.id)
    xp  = xp_db.get(uid, 0)
    lvl = get_level(xp)
    next_xp = xp_for_level(lvl + 1)
    e = discord.Embed(title=t.display_name + "'s Rank", color=discord.Color.from_rgb(255, 140, 0))
    e.set_thumbnail(url=t.display_avatar.url)
    e.add_field(name="Level", value=str(lvl), inline=True)
    e.add_field(name="XP", value=str(xp) + " / " + str(next_xp), inline=True)
    e.set_footer(text="2K Esports | XP System")
    await ctx.send(embed=e)


@bot.command(name="leaderboard")
async def leaderboard(ctx):
    top = sorted(xp_db.items(), key=lambda x: x[1], reverse=True)[:10]
    e = discord.Embed(title="2K Esports Leaderboard", color=discord.Color.from_rgb(255, 140, 0))
    if not top:
        e.description = "No XP recorded yet. Start chatting!"
    else:
        lines = []
        for i, (uid, xp) in enumerate(top, 1):
            member = ctx.guild.get_member(int(uid))
            name   = member.display_name if member else "Unknown User"
            lines.append(str(i) + ". **" + name + "** — Level " + str(get_level(xp)) + " (" + str(xp) + " XP)")
        e.description = "\n".join(lines)
    e.set_footer(text="2K Esports | Top 10")
    await ctx.send(embed=e)


@bot.command(name="roster")
async def roster(ctx):
    r = discord.utils.get(ctx.guild.roles, name=ROSTER_ROLE_NAME)
    e = discord.Embed(title="2K Esports Roster", color=discord.Color.from_rgb(255, 140, 0))
    if not r or not r.members:
        e.description = "No roster members set yet. Give players the **" + ROSTER_ROLE_NAME + "** role to list them here."
    else:
        e.description = "\n".join("🏀 " + m.mention for m in r.members)
    e.set_footer(text="2K Esports | Official Roster")
    await ctx.send(embed=e)


@bot.command(name="suggest")
async def suggest(ctx, *, idea):
    sc = find_ch(ctx.guild, "suggestions")
    if not sc:
        sc = await ctx.guild.create_text_channel("suggestions")
    e = discord.Embed(title="New Suggestion", description=idea, color=discord.Color.blurple())
    e.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
    e.set_footer(text="2K Esports | Suggestions")
    e.timestamp = datetime.utcnow()
    await sc.send(embed=e, view=SuggestionView())
    await ctx.send("Suggestion submitted!", delete_after=5)
    await ctx.message.delete()


@bot.command(name="poll")
async def poll(ctx, *, question):
    e = discord.Embed(title="Poll", description=question, color=discord.Color.blurple())
    e.set_footer(text="Poll by " + ctx.author.display_name)
    e.timestamp = datetime.utcnow()
    msg = await ctx.send(embed=e)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    await msg.add_reaction("🤷")


@bot.command(name="giveaway")
@commands.has_permissions(manage_messages=True)
async def giveaway(ctx, minutes: int, *, prize):
    e = discord.Embed(
        title="🎉 Giveaway 🎉",
        description="**Prize:** " + prize + "\n\nReact with 🎉 to enter!\nEnds in **" + str(minutes) + " minute(s)**.",
        color=discord.Color.from_rgb(255, 140, 0),
    )
    e.set_footer(text="Hosted by " + str(ctx.author))
    e.timestamp = datetime.utcnow()
    msg = await ctx.send(embed=e)
    await msg.add_reaction("🎉")
    await asyncio.sleep(minutes * 60)

    msg = await ctx.channel.fetch_message(msg.id)
    users = []
    for reaction in msg.reactions:
        if str(reaction.emoji) == "🎉":
            users = [u async for u in reaction.users() if not u.bot]
            break

    if not users:
        result_e = discord.Embed(title="Giveaway Ended", description="No valid entries. No winner for **" + prize + "**.", color=discord.Color.red())
        await ctx.send(embed=result_e)
        return

    winner = random.choice(users)
    result_e = discord.Embed(title="🎉 Giveaway Ended 🎉", description="Congratulations " + winner.mention + "! You won **" + prize + "**!", color=discord.Color.gold())
    result_e.set_footer(text="2K Esports | Giveaway")
    await ctx.send(embed=result_e)


@bot.command(name="8ball")
async def eightball(ctx, *, question):
    responses = [
        "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes, definitely.",
        "As I see it, yes.", "Most likely.", "Outlook good.", "Yes.",
        "Reply hazy, try again.", "Ask again later.", "Cannot predict now.",
        "Don't count on it.", "My reply is no.", "My sources say no.", "Very doubtful.",
    ]
    e = discord.Embed(color=discord.Color.dark_purple())
    e.add_field(name="Question", value=question, inline=False)
    e.add_field(name="Answer",   value=random.choice(responses), inline=False)
    e.set_footer(text="2K Esports | Magic 8 Ball")
    await ctx.send(embed=e)


@bot.command(name="coinflip")
async def coinflip(ctx):
    e = discord.Embed(title="Coin Flip", description="The coin landed on **" + random.choice(["Heads", "Tails"]) + "**!", color=discord.Color.gold())
    e.set_footer(text="2K Esports")
    await ctx.send(embed=e)


@bot.command(name="roll")
async def roll(ctx):
    e = discord.Embed(title="Dice Roll", description="You rolled a **" + str(random.randint(1, 6)) + "**!", color=discord.Color.green())
    e.set_footer(text="2K Esports")
    await ctx.send(embed=e)


@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    uid = str(member.id)
    if uid not in warn_db:
        warn_db[uid] = []
    warn_db[uid].append({"reason": reason, "by": str(ctx.author)})
    count = len(warn_db[uid])
    try:
        await member.send("You have been warned in **" + ctx.guild.name + "**.\nReason: " + reason + "\nTotal: **" + str(count) + "**")
    except discord.Forbidden:
        pass
    e = discord.Embed(title="Member Warned", description=member.mention + " warned.\nReason: " + reason + "\nTotal: **" + str(count) + "**", color=discord.Color.yellow())
    e.set_footer(text="2K Esports | Warned by " + str(ctx.author))
    e.timestamp = datetime.utcnow()
    await ctx.send(embed=e)
    lc = find_ch(ctx.guild, "mod-logs")
    if lc:
        await lc.send(embed=e)


@bot.command(name="warnings")
async def warnings(ctx, member: discord.Member = None):
    t   = member or ctx.author
    uid = str(t.id)
    ws  = warn_db.get(uid, [])
    e   = discord.Embed(title="Warnings for " + t.display_name, color=discord.Color.yellow())
    if not ws:
        e.description = "No warnings on record."
    else:
        for i, w in enumerate(ws, 1):
            e.add_field(name="Warning " + str(i), value="Reason: " + w["reason"] + "\nBy: " + w["by"], inline=False)
    e.set_footer(text="2K Esports | " + str(len(ws)) + " warning(s)")
    await ctx.send(embed=e)


@bot.command(name="clearwarns")
@commands.has_permissions(manage_messages=True)
async def clearwarns(ctx, member: discord.Member):
    warn_db[str(member.id)] = []
    e = discord.Embed(title="Warnings Cleared", description="All warnings cleared for " + member.mention, color=discord.Color.green())
    e.set_footer(text="2K Esports | Cleared by " + str(ctx.author))
    await ctx.send(embed=e)


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    try:
        await member.send("You have been kicked from **" + ctx.guild.name + "**.\nReason: " + reason)
    except discord.Forbidden:
        pass
    await member.kick(reason=reason)
    e = discord.Embed(title="Member Kicked", description=str(member) + " kicked.\nReason: " + reason, color=discord.Color.orange())
    e.set_footer(text="2K Esports | Kicked by " + str(ctx.author))
    e.timestamp = datetime.utcnow()
    await ctx.send(embed=e)
    lc = find_ch(ctx.guild, "mod-logs")
    if lc:
        await lc.send(embed=e)


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    try:
        await member.send("You have been banned from **" + ctx.guild.name + "**.\nReason: " + reason)
    except discord.Forbidden:
        pass
    await member.ban(reason=reason)
    e = discord.Embed(title="Member Banned", description=str(member) + " banned.\nReason: " + reason, color=discord.Color.red())
    e.set_footer(text="2K Esports | Banned by " + str(ctx.author))
    e.timestamp = datetime.utcnow()
    await ctx.send(embed=e)
    lc = find_ch(ctx.guild, "mod-logs")
    if lc:
        await lc.send(embed=e)


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user):
    banned = [entry async for entry in ctx.guild.bans()]
    for entry in banned:
        if str(entry.user) == user or str(entry.user.id) == user:
            await ctx.guild.unban(entry.user)
            e = discord.Embed(title="Member Unbanned", description=str(entry.user) + " unbanned.", color=discord.Color.green())
            e.set_footer(text="2K Esports | Unbanned by " + str(ctx.author))
            await ctx.send(embed=e)
            return
    await ctx.send("User not found in ban list.")


@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason="No reason provided"):
    mr = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mr:
        mr = await ctx.guild.create_role(name="Muted")
        for ch in ctx.guild.channels:
            await ch.set_permissions(mr, send_messages=False, speak=False)
    await member.add_roles(mr, reason=reason)
    e = discord.Embed(title="Member Muted", description=str(member) + " muted.\nReason: " + reason, color=discord.Color.orange())
    e.set_footer(text="2K Esports | Muted by " + str(ctx.author))
    e.timestamp = datetime.utcnow()
    await ctx.send(embed=e)
    lc = find_ch(ctx.guild, "mod-logs")
    if lc:
        await lc.send(embed=e)


@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    mr = discord.utils.get(ctx.guild.roles, name="Muted")
    if mr and mr in member.roles:
        await member.remove_roles(mr)
        e = discord.Embed(title="Member Unmuted", description=str(member) + " unmuted.", color=discord.Color.green())
        e.set_footer(text="2K Esports | Unmuted by " + str(ctx.author))
        await ctx.send(embed=e)
    else:
        await ctx.send(member.display_name + " is not muted.")


@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    m = await ctx.send("Cleared " + str(amount) + " messages.")
    await asyncio.sleep(3)
    await m.delete()


@bot.command(name="closemodmail")
async def closemodmail(ctx):
    if not is_admin(ctx.author):
        await ctx.send("Only Admin and above can close ModMail channels.", delete_after=5)
        return
    if ctx.channel.id in modmail_map:
        user_id = modmail_map[ctx.channel.id]
        user    = ctx.guild.get_member(user_id)
        if user:
            try:
                close_e = discord.Embed(title="ModMail Closed", description="Your ModMail with **" + ctx.guild.name + "** has been closed.\n\nThank you for reaching out!", color=discord.Color.red())
                close_e.set_footer(text="2K Esports | ModMail")
                await user.send(embed=close_e)
            except discord.Forbidden:
                pass
        modmail_map.pop(ctx.channel.id, None)
        await ctx.send("Closing in 3 seconds...")
        await asyncio.sleep(3)
        await ctx.channel.delete()
    else:
        await ctx.send("This is not a ModMail channel.", delete_after=5)


# ══════════════════════════════════════════════
#  SLASH COMMANDS
# ══════════════════════════════════════════════

@bot.tree.command(name="setup", description="First time setup for 2K Esports")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction):
    guild = interaction.guild
    await interaction.response.defer(ephemeral=True)
    msgs = []

    wc = find_ch(guild, "welcome")
    if not wc:
        wc = await guild.create_text_channel("welcome")
        msgs.append("Created welcome")
    we = discord.Embed(title="Welcome to 2K Esports!", description="This channel greets every new member.\n\nHead to **#tickets** to apply for roster, staff, or reach out to us!", color=discord.Color.from_rgb(255, 140, 0))
    if guild.icon:
        we.set_thumbnail(url=guild.icon.url)
    we.set_footer(text="2K Esports | Welcome System")
    we.timestamp = datetime.utcnow()
    await wc.send(embed=we)

    gc = find_ch(guild, "goodbye")
    if not gc:
        gc = await guild.create_text_channel("goodbye")
        msgs.append("Created goodbye")
    ge = discord.Embed(title="Goodbye Channel", description="Members who leave will be logged here.", color=discord.Color.red())
    ge.set_footer(text="2K Esports | Goodbye System")
    ge.timestamp = datetime.utcnow()
    await gc.send(embed=ge)

    tc = find_ch(guild, "tickets")
    if not tc:
        tc = await guild.create_text_channel("tickets")
        msgs.append("Created tickets")
    te = discord.Embed(
        title="2K Esports — Open a Ticket",
        description=(
            "🏀 **Roster Application** — Apply to join the roster *(13+ only)*\n"
            "🛡️ **Staff Application** — Apply to become staff *(13+, resume required)*\n"
            "🎥 **Content Creator** — Apply to create content\n"
            "💰 **Investment** — Invest in 2K Esports\n"
            "🤝 **Business Inquiry** — Partnerships and general business\n\n"
            "Click a button below to open your **private ticket**.\n"
            "A staff member will respond as soon as possible!"
        ),
        color=discord.Color.from_rgb(255, 140, 0),
    )
    te.set_footer(text="2K Esports | Ticket System")
    te.timestamp = datetime.utcnow()
    await tc.send(embed=te, view=TicketPanelView())
    msgs.append("Ticket panel posted")

    lc = find_ch(guild, "mod-logs")
    if not lc:
        lc = await guild.create_text_channel("mod-logs")
        msgs.append("Created mod-logs")
    await lc.send(embed=discord.Embed(title="Mod Logs Active", description="All mod actions, joins, leaves, edits, deletes, and ticket transcripts logged here.", color=discord.Color.orange()))

    dlc = find_ch(guild, "defense-logs")
    if not dlc:
        dlc = await guild.create_text_channel("defense-logs")
        msgs.append("Created defense-logs")
    await dlc.send(embed=discord.Embed(title="Defense Logs Active", description="Raid alerts, invite blocks, mass mentions, and spam logs here.", color=discord.Color.dark_red()))

    sc = find_ch(guild, "suggestions")
    if not sc:
        sc = await guild.create_text_channel("suggestions")
        msgs.append("Created suggestions")
    await sc.send(embed=discord.Embed(title="Suggestions", description="Use `k?suggest <idea>` to post a suggestion here!", color=discord.Color.blurple()))

    ar = discord.utils.get(guild.roles, name=AUTO_ROLE_NAME)
    if not ar:
        await guild.create_role(name=AUTO_ROLE_NAME, color=discord.Color.light_grey())
        msgs.append("Created Member auto-role")

    rr = discord.utils.get(guild.roles, name=ROSTER_ROLE_NAME)
    if not rr:
        await guild.create_role(name=ROSTER_ROLE_NAME, color=discord.Color.from_rgb(255, 140, 0))
        msgs.append("Created Roster role — assign this to official players")

    await interaction.followup.send("Setup complete!\n" + "\n".join(msgs), ephemeral=True)


@bot.tree.command(name="panel", description="Re-post the ticket panel")
@app_commands.checks.has_permissions(manage_channels=True)
async def panel(interaction):
    te = discord.Embed(
        title="2K Esports — Open a Ticket",
        description=(
            "🏀 **Roster Application** — Apply to join the roster *(13+ only)*\n"
            "🛡️ **Staff Application** — Apply to become staff *(13+, resume required)*\n"
            "🎥 **Content Creator** — Apply to create content\n"
            "💰 **Investment** — Invest in 2K Esports\n"
            "🤝 **Business Inquiry** — Partnerships and general business\n\n"
            "Click a button below to open your **private ticket**.\n"
            "A staff member will respond as soon as possible!"
        ),
        color=discord.Color.from_rgb(255, 140, 0),
    )
    te.set_footer(text="2K Esports | Ticket System")
    te.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=te, view=TicketPanelView())


@bot.tree.command(name="modcheck", description="View a staff member's claimed tickets and messages sent")
async def modcheck(interaction, member: discord.Member):
    if not is_staff(interaction.user):
        await interaction.response.send_message("Only staff can use this command.", ephemeral=True)
        return
    stats = staff_stats.get(str(member.id), {"tickets_claimed": 0, "messages_sent": 0})
    e = discord.Embed(title="Staff Activity — " + member.display_name, color=discord.Color.from_rgb(255, 140, 0))
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="Tickets Claimed", value=str(stats["tickets_claimed"]), inline=True)
    e.add_field(name="Messages Sent Since Last Reset", value=str(stats["messages_sent"]), inline=True)
    e.set_footer(text="2K Esports | Staff Activity Tracker")
    e.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=e)


@bot.tree.command(name="modget", description="View the staff activity leaderboard")
async def modget(interaction):
    if not is_staff(interaction.user):
        await interaction.response.send_message("Only staff can use this command.", ephemeral=True)
        return
    if not staff_stats:
        await interaction.response.send_message("No staff activity recorded yet.", ephemeral=True)
        return

    ranked = sorted(
        staff_stats.items(),
        key=lambda x: (x[1]["tickets_claimed"], x[1]["messages_sent"]),
        reverse=True,
    )
    e = discord.Embed(title="Staff Activity Leaderboard", color=discord.Color.from_rgb(255, 140, 0))
    lines = []
    for i, (uid, stats) in enumerate(ranked[:15], 1):
        member = interaction.guild.get_member(int(uid))
        name = member.display_name if member else "Unknown Staff"
        lines.append(
    str(i) + ". **" + name + "** — " +
    str(stats["tickets_claimed"]) + " tickets claimed, " +
    str(stats["messages_sent"]) + " messages since last reset"
)
    e.description = "\n".join(lines)
    e.set_footer(text="2K Esports | Staff Activity Tracker")
    e.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=e)


@bot.tree.command(name="reset", description="Reset all claimed ticket and message counters to zero (Founder only)")
async def reset_stats(interaction):
    if not is_founder(interaction.user):
        await interaction.response.send_message("Only the Founder role can reset staff activity stats.", ephemeral=True)
        return
    staff_stats.clear()
    e = discord.Embed(title="Staff Activity Reset", description="All claimed ticket and message counters have been reset to zero by " + interaction.user.mention + ".", color=discord.Color.red())
    e.set_footer(text="2K Esports | Staff Activity Tracker")
    e.timestamp = datetime.utcnow()
    await interaction.response.send_message(embed=e)
    lc = find_ch(interaction.guild, "mod-logs")
    if lc:
        await lc.send(embed=e)


@bot.tree.command(name="testraid", description="Test the anti-raid system (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def test_raid(interaction):
    guild = interaction.guild
    await interaction.response.defer(ephemeral=True)
    await lockdown_server(guild, reason="TEST RAID triggered by " + str(interaction.user))
    lc = find_ch(guild, "defense-logs")
    if lc:
        te = discord.Embed(title="RAID TEST TRIGGERED", description="Test by " + str(interaction.user) + ".\nAll channels locked.\nDM alerts sent to: " + ", ".join(RAID_ALERT_USERS), color=discord.Color.orange())
        te.timestamp = datetime.utcnow()
        await lc.send(embed=te)
    await interaction.followup.send("Raid test triggered! Check defense-logs.", ephemeral=True)


@bot.tree.command(name="lockdown", description="Manually lock down the server (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def lockdown(interaction):
    guild = interaction.guild
    await interaction.response.defer(ephemeral=True)
    await lockdown_server(guild, reason="Manual lockdown by " + str(interaction.user))
    await interaction.followup.send("Server locked down.", ephemeral=True)


@bot.tree.command(name="unlock", description="Manually unlock all channels (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def unlock(interaction):
    guild    = interaction.guild
    guild_id = guild.id
    await interaction.response.defer(ephemeral=True)
    raid_active[guild_id] = False
    restored = 0
    if guild_id in locked_channels:
        for channel_id, old_perms in locked_channels[guild_id].items():
            ch = guild.get_channel(channel_id)
            if ch:
                try:
                    await ch.set_permissions(guild.default_role, send_messages=old_perms)
                    restored += 1
                except Exception:
                    pass
        locked_channels.pop(guild_id, None)
    await interaction.followup.send("Unlocked " + str(restored) + " channels.", ephemeral=True)
    lc = find_ch(guild, "defense-logs")
    if lc:
        e = discord.Embed(title="Server Unlocked", description="Unlocked by " + str(interaction.user) + ". " + str(restored) + " channels restored.", color=discord.Color.green())
        e.timestamp = datetime.utcnow()
       @bot.tree.command(name="addroster", description="Add user to roster (Ticket Support only)")
async def addroster(interaction, member: discord.Member):
    if not is_ticket_support(interaction.user):
        await interaction.response.send_message(
            "Only Ticket Support can use this.",
            ephemeral=True
        )
        return

    role = discord.utils.get(interaction.guild.roles, name=ROSTER_ROLE_NAME)

    if role:
        await member.add_roles(role)

    await interaction.response.send_message(
        f"✅ {member.mention} added to roster by {interaction.user.mention}"
    )

    role = discord.utils.get(interaction.guild.roles, name=ROSTER_ROLE_NAME)

    if role:
        await member.add_roles(role)

    await interaction.response.send_message(
        f"✅ {member.mention} added to roster by {interaction.user.mention}"
    )


# ══════════════════════════════════════════════
#  ON READY
# ══════════════════════════════════════════════

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("2K Esports Bot online: " + str(bot.user))
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="2K Esports | k?help"))


bot.run(TOKEN)
