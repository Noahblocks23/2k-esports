import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
import json
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")


# =========================
# CONFIG
# =========================

PREFIX = "k?"

SERVER_NAME = "2K Esports"

GENERAL_CHANNEL_ID = 1442706132044087453

AUTO_ROLE_NAME = "Community"
ROSTER_ROLE_NAME = "Roster"


STAFF_ROLES = [
    "Founder",
    "Co-Founder",
    "Admin",
    "Moderator",
    "Ticket Support"
]


ADMIN_ROLES = [
    "Founder",
    "Co-Founder",
    "Admin"
]


TICKET_SUPPORT_ROLE_ID = 1521520766141595689


GENERAL_EVENTS = True


# =========================
# DATABASE
# =========================

FILES = {
    "xp": "data/xp.json",
    "coins": "data/coins.json",
    "warns": "data/warns.json",
    "stats": "data/stats.json",
    "tickets": "data/tickets.json"
}


if not os.path.exists("data"):
    os.makedirs("data")


for file in FILES.values():
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)


def load_db(name):

    with open(FILES[name], "r") as f:
        return json.load(f)



def save_db(name,data):

    with open(FILES[name],"w") as f:
        json.dump(data,f,indent=4)



xp_db = load_db("xp")
coin_db = load_db("coins")
warn_db = load_db("warns")
stats_db = load_db("stats")
ticket_db = load_db("tickets")



# =========================
# INTENTS
# =========================

intents = discord.Intents.default()

intents.members = True
intents.message_content = True
intents.guilds = True



bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)



# =========================
# PERMISSIONS
# =========================


def is_staff(member):

    return any(
        role.name in STAFF_ROLES
        for role in member.roles
    )


def is_admin(member):

    return any(
        role.name in ADMIN_ROLES
        for role in member.roles
    ) or member.guild_permissions.administrator



def find_channel(guild,name):

    return discord.utils.get(
        guild.text_channels,
        name=name
    )



# =========================
# XP SYSTEM
# =========================


def xp_needed(level):

    return level * 100



def get_level(xp):

    level = 0

    while xp >= xp_needed(level+1):

        level += 1

    return level



async def add_xp(member,amount):

    uid=str(member.id)

    old=xp_db.get(uid,0)

    xp_db[uid]=old+amount

    save_db("xp",xp_db)

    old_level=get_level(old)
    new_level=get_level(xp_db[uid])


    if new_level > old_level:

        embed=discord.Embed(
            title="🎉 Level Up!",
            description=f"{member.mention} reached **Level {new_level}**!",
            color=discord.Color.orange()
        )

        await member.channel.send(embed=embed)



# =========================
# RANDOM EVENTS SYSTEM
# =========================


EVENTS=[

    "🏀 **2K Trivia!** First person to answer wins 200 XP!",

    "🔥 **XP BOOST!** Everyone chatting gets bonus XP for 10 minutes!",

    "🎁 **Random Drop!** React to this message for a chance to win coins!",

    "🏆 **MVP Challenge!** First person to say MVP wins!"

]



@tasks.loop(minutes=30)
async def random_event():


    if not GENERAL_EVENTS:
        return


    channel=bot.get_channel(GENERAL_CHANNEL_ID)


    if channel:

        embed=discord.Embed(

            title="🔥 2K Esports Event",

            description=random.choice(EVENTS),

            color=discord.Color.gold()

        )

        embed.set_footer(
            text="2K Esports Community Event"
        )


        await channel.send(embed=embed)



# =========================
# MEMBER JOIN
# =========================


@bot.event
async def on_member_join(member):


    role=discord.utils.get(
        member.guild.roles,
        name=AUTO_ROLE_NAME
    )


    if role:

        try:
            await member.add_roles(role)

        except:
            pass



    channel=find_channel(
        member.guild,
        "welcome"
    )


    if channel:

        embed=discord.Embed(

            title="🏀 Welcome to 2K Esports",

            description=
            f"Welcome {member.mention}!\n\n"
            "Check tickets to apply!",

            color=discord.Color.orange()

        )


        await channel.send(embed=embed)



# =========================
# MESSAGE XP
# =========================


cooldowns={}



@bot.event
async def on_message(message):

    if message.author.bot:
        return


    if message.guild:


        uid=str(message.author.id)

        now=datetime.utcnow()


        if uid not in cooldowns or (
            now-cooldowns[uid]
        ).seconds > 60:


            cooldowns[uid]=now


            await add_xp(
                message.author,
                random.randint(10,20)
            )



    await bot.process_commands(message)



# =========================
# READY
# =========================


@bot.event
async def on_ready():

    await bot.tree.sync()

    if not random_event.is_running():

        random_event.start()


    print(
        f"Logged in as {bot.user}"
    )


    await bot.change_presence(

        activity=discord.Activity(

            type=discord.ActivityType.watching,

            name="2K Esports | k?help"

        )

    )



bot.run(TOKEN)

# ==========================================
# ADVANCED TICKET SYSTEM
# ==========================================


TICKET_CATEGORIES = {

    "roster": {
        "emoji": "🏀",
        "name": "Roster Application",
        "questions": [
            "What is your name?",
            "How old are you?",
            "What is your PSN/XBOX/Gamertag?",
            "What game are you applying for?",
            "Please send your Fortnite tracker or stats.",
            "How many hours per week can you dedicate?",
            "Why do you want to join 2K Esports?"
        ]
    },


    "staff": {
        "emoji": "🛡️",
        "name": "Staff Application",
        "questions": [
            "What is your name?",
            "How old are you?",
            "What staff position are you applying for?",
            "Send your previous experience/resume.",
            "How many hours can you work weekly?",
            "Why should 2K Esports choose you?"
        ]
    },


    "content": {
        "emoji": "🎥",
        "name": "Content Creator Application",
        "questions": [
            "What is your name?",
            "What platform do you create on?",
            "How many followers/subscribers do you have?",
            "Send your social media links.",
            "Send proof you own your accounts.",
            "Why do you want to join 2K Esports?"
        ]
    },


    "investment": {
        "emoji": "💰",
        "name": "Investment Inquiry",
        "questions": [
            "What is your name?",
            "What investment are you interested in?",
            "What resources are you offering?",
            "Have you invested in esports before?",
            "What are your goals?"
        ]
    },


    "business": {
        "emoji": "🤝",
        "name": "Business Partnership",
        "questions": [
            "What is your name/company?",
            "What is your partnership idea?",
            "What are you looking to achieve?",
            "How can this benefit 2K Esports?",
            "Best contact information?"
        ]
    }

}



# ------------------------------------------
# Ticket Buttons
# ------------------------------------------


class TicketButton(discord.ui.Button):


    def __init__(self,key,data):

        super().__init__(
            label=data["name"],
            emoji=data["emoji"],
            style=discord.ButtonStyle.primary
        )

        self.key=key



    async def callback(self,interaction):

        await interaction.response.defer(
            ephemeral=True
        )

        await create_ticket(
            interaction,
            self.key
        )





class TicketPanel(discord.ui.View):


    def __init__(self):

        super().__init__(
            timeout=None
        )


        for key,data in TICKET_CATEGORIES.items():

            self.add_item(
                TicketButton(
                    key,
                    data
                )
            )




# ------------------------------------------
# Ticket Controls
# ------------------------------------------


class TicketControls(discord.ui.View):


    def __init__(self):

        super().__init__(
            timeout=None
        )



    @discord.ui.button(
        label="Claim Ticket",
        emoji="✅",
        style=discord.ButtonStyle.success
    )
    async def claim(
        self,
        interaction,
        button
    ):


        if not is_staff(interaction.user):

            return await interaction.response.send_message(
                "❌ Staff only.",
                ephemeral=True
            )


        ticket_db[str(interaction.channel.id)] = {

            "claimed":
            str(interaction.user.id)

        }


        save_db(
            "tickets",
            ticket_db
        )


        embed=discord.Embed(

            title="Ticket Claimed",

            description=
            f"{interaction.user.mention} is now handling this ticket.",

            color=discord.Color.green()

        )


        await interaction.response.send_message(
            embed=embed
        )




    @discord.ui.button(

        label="Close Ticket",

        emoji="🔒",

        style=discord.ButtonStyle.danger

    )
    async def close(

        self,
        interaction,
        button

    ):


        if not is_staff(interaction.user):

            return await interaction.response.send_message(
                "❌ Staff only.",
                ephemeral=True
            )


        await interaction.response.send_message(

            "Saving transcript and closing in 5 seconds..."

        )


        await save_ticket_transcript(
            interaction.channel
        )


        await asyncio.sleep(5)


        await interaction.channel.delete()




# ------------------------------------------
# Create Ticket
# ------------------------------------------


async def create_ticket(interaction,key):


    guild=interaction.guild

    member=interaction.user


    data=TICKET_CATEGORIES[key]


    existing=discord.utils.get(

        guild.text_channels,

        name=f"{key}-{member.name.lower()}"

    )


    if existing:

        return await interaction.followup.send(

            "❌ You already have a ticket open.",

            ephemeral=True

        )



    category=discord.utils.get(

        guild.categories,

        name="Tickets"

    )


    if not category:

        category=await guild.create_category(
            "Tickets"
        )



    overwrites={

        guild.default_role:
        discord.PermissionOverwrite(
            view_channel=False
        ),


        member:
        discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True
        )

    }



    for role in guild.roles:

        if role.name in STAFF_ROLES:

            overwrites[role]=discord.PermissionOverwrite(

                view_channel=True,

                send_messages=True

            )




    channel=await category.create_text_channel(

        name=f"{key}-{member.name.lower()}",

        overwrites=overwrites

    )



    embed=discord.Embed(

        title=f"{data['emoji']} {data['name']}",

        description=

        f"{member.mention}\n\n"
        "A staff member will assist you shortly.\n\n"
        "**Please answer these questions:**",

        color=discord.Color.orange()

    )



    for i,q in enumerate(data["questions"],1):

        embed.add_field(

            name=f"{i}.",

            value=q,

            inline=False

        )



    await channel.send(

        embed=embed,

        view=TicketControls()

    )



    await interaction.followup.send(

        f"✅ Ticket created: {channel.mention}",

        ephemeral=True

    )




# ------------------------------------------
# Transcript System
# ------------------------------------------


async def save_ticket_transcript(channel):


    messages=[]


    async for msg in channel.history(
        limit=300,
        oldest_first=True
    ):

        messages.append(

            f"{msg.author}: {msg.content}"

        )



    text="\n".join(messages)



    logs=find_channel(

        channel.guild,

        "mod-logs"

    )


    if logs:


        embed=discord.Embed(

            title="📄 Ticket Closed",

            description=
            f"Transcript saved for `{channel.name}`",

            color=discord.Color.red()

        )


        await logs.send(embed=embed)
# ==========================================
# MODERATION + SECURITY SYSTEM
# ==========================================


INVITE_WORDS = [
    "discord.gg/",
    "discord.com/invite/"
]


spam_cache = {}



# ------------------------------------------
# MOD LOG FUNCTION
# ------------------------------------------


async def send_modlog(guild,title,description,color=discord.Color.red()):


    channel=find_channel(
        guild,
        "mod-logs"
    )


    if channel:

        embed=discord.Embed(

            title=title,

            description=description,

            color=color

        )

        embed.timestamp=datetime.utcnow()

        await channel.send(embed=embed)




# ------------------------------------------
# WARN SYSTEM
# ------------------------------------------


@bot.command()
async def warn(ctx,member:discord.Member,*,reason="No reason provided"):


    if not is_staff(ctx.author):

        return await ctx.send(
            "❌ Staff only."
        )



    uid=str(member.id)


    if uid not in warn_db:

        warn_db[uid]=[]



    warn_db[uid].append({

        "reason":reason,

        "staff":str(ctx.author),

        "time":str(datetime.utcnow())

    })


    save_db(
        "warns",
        warn_db
    )



    embed=discord.Embed(

        title="⚠️ Member Warned",

        description=

        f"{member.mention} has received a warning.\n\n"
        f"Reason: **{reason}**",

        color=discord.Color.yellow()

    )


    await ctx.send(embed=embed)



    await send_modlog(

        ctx.guild,

        "Warning Given",

        f"""
Member:
{member.mention}

Staff:
{ctx.author.mention}

Reason:
{reason}
""",

        discord.Color.yellow()

    )





@bot.command()
async def warnings(ctx,member:discord.Member=None):


    member=member or ctx.author


    warns=warn_db.get(
        str(member.id),
        []
    )


    embed=discord.Embed(

        title=f"{member.display_name}'s Warnings",

        color=discord.Color.orange()

    )


    if not warns:

        embed.description="No warnings."

    else:

        for i,w in enumerate(warns,1):

            embed.add_field(

                name=f"Warning #{i}",

                value=
                f"Reason: {w['reason']}\n"
                f"Staff: {w['staff']}",

                inline=False

            )


    await ctx.send(embed=embed)





@bot.command()
async def clearwarns(ctx,member:discord.Member):


    if not is_staff(ctx.author):

        return



    warn_db[str(member.id)]=[]

    save_db(
        "warns",
        warn_db
    )


    await ctx.send(

        f"✅ Cleared warnings for {member.mention}"

    )





# ------------------------------------------
# TIMEOUT SYSTEM
# ------------------------------------------


@bot.command()
async def timeout(
    ctx,
    member:discord.Member,
    minutes:int,
    *,
    reason="No reason"
):


    if not is_staff(ctx.author):

        return



    until=datetime.utcnow()+timedelta(

        minutes=minutes

    )


    await member.timeout(

        until,

        reason=reason

    )


    await ctx.send(

        f"🔇 {member.mention} timed out for {minutes} minutes."

    )


    await send_modlog(

        ctx.guild,

        "Timeout",

        f"{member} timed out by {ctx.author}\nReason: {reason}"

    )





# ------------------------------------------
# KICK
# ------------------------------------------


@bot.command()
async def kick(ctx,member:discord.Member,*,reason="No reason"):


    if not is_staff(ctx.author):

        return



    await member.kick(
        reason=reason
    )


    await ctx.send(

        f"👢 {member} kicked."

    )


    await send_modlog(

        ctx.guild,

        "Member Kicked",

        f"{member} kicked by {ctx.author}\n{reason}"

    )





# ------------------------------------------
# BAN
# ------------------------------------------


@bot.command()
async def ban(ctx,member:discord.Member,*,reason="No reason"):


    if not is_staff(ctx.author):

        return



    await member.ban(
        reason=reason
    )


    await ctx.send(

        f"🔨 {member} banned."

    )


    await send_modlog(

        ctx.guild,

        "Member Banned",

        f"{member} banned by {ctx.author}\n{reason}"

    )






# ------------------------------------------
# CLEAR CHAT
# ------------------------------------------


@bot.command()
async def clear(ctx,amount:int=5):


    if not is_staff(ctx.author):

        return


    await ctx.channel.purge(
        limit=amount+1
    )


    msg=await ctx.send(

        f"🧹 Cleared {amount} messages."

    )


    await asyncio.sleep(3)

    await msg.delete()





# ------------------------------------------
# LOCK CHANNEL
# ------------------------------------------


@bot.command()
async def lock(ctx):


    if not is_staff(ctx.author):

        return



    await ctx.channel.set_permissions(

        ctx.guild.default_role,

        send_messages=False

    )


    await ctx.send(

        "🔒 Channel locked."

    )





@bot.command()
async def unlock(ctx):


    if not is_staff(ctx.author):

        return



    await ctx.channel.set_permissions(

        ctx.guild.default_role,

        send_messages=True

    )


    await ctx.send(

        "🔓 Channel unlocked."

    )





# ------------------------------------------
# ANTI SPAM / INVITE / MENTIONS
# ------------------------------------------


@bot.event
async def on_message_security(message):

    pass# ==========================================
# XP + ECONOMY + FUN SYSTEM
# ==========================================


DAILY_COOLDOWN = {}


SHOP_ITEMS = {

    "boost": {
        "name": "XP Boost",
        "price": 1000
    },

    "badge": {
        "name": "2K Badge",
        "price": 2500
    },

    "trophy": {
        "name": "Champion Trophy",
        "price": 5000
    }

}



# ------------------------------------------
# COINS
# ------------------------------------------


def get_coins(user):

    return coin_db.get(
        str(user.id),
        0
    )



def add_coins(user,amount):

    uid=str(user.id)

    coin_db[uid]=coin_db.get(uid,0)+amount

    save_db(
        "coins",
        coin_db
    )



def remove_coins(user,amount):

    uid=str(user.id)

    coin_db[uid]=max(
        0,
        coin_db.get(uid,0)-amount
    )

    save_db(
        "coins",
        coin_db
    )




# ------------------------------------------
# BALANCE
# ------------------------------------------


@bot.command()
async def balance(ctx,member:discord.Member=None):


    member=member or ctx.author


    embed=discord.Embed(

        title="💰 Balance",

        description=
        f"{member.mention}\n\n"
        f"Coins: **{get_coins(member)}**",

        color=discord.Color.gold()

    )


    await ctx.send(embed=embed)




# ------------------------------------------
# DAILY REWARD
# ------------------------------------------


@bot.command()
async def daily(ctx):


    uid=str(ctx.author.id)


    if uid in DAILY_COOLDOWN:


        remaining = (
            DAILY_COOLDOWN[uid]
            - datetime.utcnow()
        )


        if remaining.total_seconds()>0:

            return await ctx.send(

                f"⏳ Come back in {remaining.seconds//3600} hours."

            )



    reward=random.randint(
        500,
        1000
    )


    add_coins(
        ctx.author,
        reward
    )


    DAILY_COOLDOWN[uid]=datetime.utcnow()+timedelta(days=1)



    embed=discord.Embed(

        title="🎁 Daily Reward",

        description=
        f"You received **{reward} coins**!",

        color=discord.Color.green()

    )


    await ctx.send(embed=embed)





# ------------------------------------------
# GIVE COINS
# ------------------------------------------


@bot.command()
async def givecoins(ctx,member:discord.Member,amount:int):


    if amount <= 0:

        return



    if get_coins(ctx.author)<amount:

        return await ctx.send(
            "❌ You don't have enough coins."
        )



    remove_coins(
        ctx.author,
        amount
    )


    add_coins(
        member,
        amount
    )



    await ctx.send(

        f"💸 {ctx.author.mention} gave {member.mention} **{amount} coins**"

    )





# ------------------------------------------
# SHOP
# ------------------------------------------


@bot.command()
async def shop(ctx):


    embed=discord.Embed(

        title="🛒 2K Shop",

        color=discord.Color.blue()

    )


    for item,data in SHOP_ITEMS.items():

        embed.add_field(

            name=data["name"],

            value=f"{data['price']} coins\nBuy with `k?buy {item}`",

            inline=False

        )


    await ctx.send(embed=embed)





# ------------------------------------------
# INVENTORY
# ------------------------------------------


inventory={}



@bot.command()
async def inventory(ctx):


    items=inventory.get(
        str(ctx.author.id),
        []
    )


    embed=discord.Embed(

        title="🎒 Inventory",

        description=
        "\n".join(items)
        if items else
        "Empty inventory",

        color=discord.Color.purple()

    )


    await ctx.send(embed=embed)





# ------------------------------------------
# BUY ITEMS
# ------------------------------------------


@bot.command()
async def buy(ctx,item):


    item=item.lower()


    if item not in SHOP_ITEMS:

        return await ctx.send(
            "❌ Item does not exist."
        )


    price=SHOP_ITEMS[item]["price"]



    if get_coins(ctx.author)<price:

        return await ctx.send(
            "❌ Not enough coins."
        )



    remove_coins(
        ctx.author,
        price
    )


    uid=str(ctx.author.id)


    if uid not in inventory:

        inventory[uid]=[]



    inventory[uid].append(

        SHOP_ITEMS[item]["name"]

    )


    await ctx.send(

        f"✅ Bought {SHOP_ITEMS[item]['name']}"

    )





# ------------------------------------------
# PLAYER CARD
# ------------------------------------------


@bot.command()
async def playercard(ctx,member:discord.Member=None):


    member=member or ctx.author


    xp=xp_db.get(
        str(member.id),
        0
    )


    level=get_level(xp)



    shooting=random.randint(70,99)
    defense=random.randint(70,99)
    playmaking=random.randint(70,99)



    overall=int(

        (shooting+
        defense+
        playmaking)/3

    )



    embed=discord.Embed(

        title=f"🏀 {member.display_name}'s Player Card",

        color=discord.Color.orange()

    )


    embed.set_thumbnail(

        url=member.display_avatar.url

    )


    embed.add_field(
        name="Overall",
        value=f"⭐ {overall}",
        inline=True
    )


    embed.add_field(
        name="Level",
        value=level,
        inline=True
    )


    embed.add_field(
        name="Shooting",
        value=shooting,
        inline=True
    )


    embed.add_field(
        name="Defense",
        value=defense,
        inline=True
    )


    embed.add_field(
        name="Playmaking",
        value=playmaking,
        inline=True
    )


    await ctx.send(embed=embed)





# ------------------------------------------
# RANDOM GAMES
# ------------------------------------------


@bot.command()
async def coinflip(ctx):


    result=random.choice(
        ["Heads 🪙","Tails 🪙"]
    )


    await ctx.send(

        f"🪙 Coin landed on **{result}**"

    )





@bot.command()
async def roll(ctx):


    await ctx.send(

        f"🎲 You rolled **{random.randint(1,6)}**"

    )





@bot.command()
async def shot(ctx):


    result=random.randint(1,100)


    if result>=80:

        text="🔥 GREEN BEAN! Perfect shot!"

    elif result>=50:

        text="🏀 Made the shot!"

    else:

        text="❌ Brick!"



    await ctx.send(text)





@bot.command()
async def dribble(ctx):


    moves=[

        "Ankles broken 🥶",

        "Clean crossover 🔥",

        "Lost the ball 💀"

    ]


    await ctx.send(

        random.choice(moves)

    )





# ------------------------------------------
# LEADERBOARD
# ------------------------------------------


@bot.command()
async def leaderboard(ctx):


    top=sorted(

        xp_db.items(),

        key=lambda x:x[1],

        reverse=True

    )[:10]



    embed=discord.Embed(

        title="🏆 XP Leaderboard",

        color=discord.Color.gold()

    )


    text=""


    for i,(uid,xp) in enumerate(top,1):


        member=ctx.guild.get_member(
            int(uid)
        )


        name=member.display_name if member else "Unknown"


        text+=(
            f"**{i}. {name}** "
            f"- Level {get_level(xp)}\n"
        )


    embed.description=text or "No players yet."


    await ctx.send(embed=embed)

# ==========================================
# MODMAIL SYSTEM
# ==========================================


MODMAIL_CATEGORY = "ModMail"

modmail_sessions = {}



async def create_modmail(member, message):

    guild = member.guild if hasattr(member, "guild") else None

    if guild is None:
        return


    category = discord.utils.get(
        guild.categories,
        name=MODMAIL_CATEGORY
    )


    if not category:

        category = await guild.create_category(
            MODMAIL_CATEGORY
        )



    channel_name = f"modmail-{member.name.lower()}"



    existing = discord.utils.get(
        guild.text_channels,
        name=channel_name
    )


    if existing:

        await existing.send(
            f"📩 **{member} replied:**\n{message}"
        )

        return existing




    overwrites = {

        guild.default_role:
        discord.PermissionOverwrite(
            view_channel=False
        ),

        guild.me:
        discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True
        ),

        member:
        discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True
        )

    }



    for role in guild.roles:

        if role.name in ADMIN_ROLES:

            overwrites[role] = discord.PermissionOverwrite(

                view_channel=True,

                send_messages=True

            )




    channel = await category.create_text_channel(

        channel_name,

        overwrites=overwrites

    )



    modmail_sessions[channel.id]=member.id



    embed=discord.Embed(

        title="📨 New ModMail",

        description=
        f"User: {member.mention}\n\n"
        f"Message:\n{message}",

        color=discord.Color.orange()

    )


    await channel.send(embed=embed)


    return channel





@bot.event
async def on_message(message):

    if message.author.bot:
        return



    # DM MODMAIL

    if isinstance(message.channel, discord.DMChannel):


        for guild in bot.guilds:


            member=guild.get_member(
                message.author.id
            )


            if member:


                await create_modmail(

                    member,

                    message.content

                )


                await message.author.send(

                    "✅ Your message was sent to 2K Esports staff."

                )


                return




    await bot.process_commands(message)







# ==========================================
# SUGGESTION SYSTEM
# ==========================================


@bot.command()
async def suggest(ctx, *, idea):


    channel=find_channel(

        ctx.guild,

        "suggestions"

    )


    if not channel:


        channel=await ctx.guild.create_text_channel(

            "suggestions"

        )



    embed=discord.Embed(

        title="💡 New Suggestion",

        description=idea,

        color=discord.Color.blue()

    )


    embed.set_author(

        name=str(ctx.author),

        icon_url=ctx.author.display_avatar.url

    )


    msg=await channel.send(

        embed=embed

    )


    await msg.add_reaction("👍")

    await msg.add_reaction("👎")



    await ctx.send(

        "✅ Suggestion submitted!",

        delete_after=5

    )





# ==========================================
# POLLS
# ==========================================


@bot.command()
async def poll(ctx, *, question):


    embed=discord.Embed(

        title="📊 Poll",

        description=question,

        color=discord.Color.purple()

    )


    embed.set_footer(

        text=f"Created by {ctx.author}"

    )



    msg=await ctx.send(

        embed=embed

    )


    await msg.add_reaction("👍")

    await msg.add_reaction("👎")

    await msg.add_reaction("🤷")





# ==========================================
# 8 BALL
# ==========================================


@bot.command()
async def eightball(ctx, *, question):


    answers=[

        "Yes 🏀",

        "No ❌",

        "Maybe 🤔",

        "Definitely 🔥",

        "Ask again later ⏳",

        "Most likely ✅",

        "Never 💀"

    ]



    embed=discord.Embed(

        title="🎱 Magic 8 Ball",

        color=discord.Color.dark_purple()

    )


    embed.add_field(

        name="Question",

        value=question,

        inline=False

    )


    embed.add_field(

        name="Answer",

        value=random.choice(answers),

        inline=False

    )


    await ctx.send(embed=embed)





# ==========================================
# SERVER INFO
# ==========================================


@bot.command()
async def serverinfo(ctx):


    guild=ctx.guild


    embed=discord.Embed(

        title=f"🏀 {guild.name}",

        color=discord.Color.orange()

    )


    if guild.icon:

        embed.set_thumbnail(

            url=guild.icon.url

        )



    embed.add_field(

        name="Members",

        value=guild.member_count

    )


    embed.add_field(

        name="Roles",

        value=len(guild.roles)

    )


    embed.add_field(

        name="Channels",

        value=len(guild.channels)

    )


    embed.add_field(

        name="Owner",

        value=str(guild.owner)

    )


    await ctx.send(embed=embed)





# ==========================================
# USER INFO
# ==========================================


@bot.command()
async def userinfo(ctx,member:discord.Member=None):


    member=member or ctx.author


    embed=discord.Embed(

        title=f"👤 {member.display_name}",

        color=discord.Color.orange()

    )


    embed.set_thumbnail(

        url=member.display_avatar.url

    )


    embed.add_field(

        name="Username",

        value=str(member)

    )


    embed.add_field(

        name="ID",

        value=member.id

    )


    embed.add_field(

        name="Joined",

        value=discord.utils.format_dt(
            member.joined_at,
            "R"
        )
        if member.joined_at else "Unknown"

    )


    await ctx.send(embed=embed)





# ==========================================
# AVATAR
# ==========================================


@bot.command()
async def avatar(ctx,member:discord.Member=None):


    member=member or ctx.author


    embed=discord.Embed(

        title=f"{member.display_name}'s Avatar",

        color=discord.Color.orange()

    )


    embed.set_image(

        url=member.display_avatar.url

    )


    await ctx.send(embed=embed)





# ==========================================
# HELP COMMAND UPGRADE
# ==========================================


@bot.command()
async def help(ctx):


    embed=discord.Embed(

        title="🏀 2K Esports Commands",

        description=
        "Prefix: `k?`",

        color=discord.Color.orange()

    )


    commands_list=[

        "balance",

        "daily",

        "shop",

        "buy",

        "inventory",

        "playercard",

        "leaderboard",

        "ticket",

        "suggest",

        "poll",

        "warn",

        "kick",

        "ban",

        "timeout",

        "clear",

        "lock",

        "unlock",

        "userinfo",

        "serverinfo",

        "avatar"

    ]


    embed.add_field(

        name="Commands",

        value="\n".join(
            f"`k?{x}`"
            for x in commands_list
        ),

        inline=False

    )


    embed.set_footer(

        text="2K Esports | Bot System"

    )


    await ctx.send(embed=embed)
    # ==========================================
# TICKET PANEL SETUP
# ==========================================


@bot.tree.command(
    name="panel",
    description="Send the 2K Esports ticket panel"
)
async def panel(interaction: discord.Interaction):


    if not is_staff(interaction.user):

        return await interaction.response.send_message(
            "❌ Staff only.",
            ephemeral=True
        )



    embed=discord.Embed(

        title="🏀 2K Esports Support",

        description=
        """
Need help or want to join 2K Esports?

Click a button below to open a private ticket.

🏀 Roster Application
🛡️ Staff Application
🎥 Content Creator
💰 Investment
🤝 Business Partnership

A staff member will respond shortly.
""",

        color=discord.Color.orange()

    )


    embed.set_footer(
        text="2K Esports | Ticket System"
    )


    await interaction.channel.send(

        embed=embed,

        view=TicketPanel()

    )


    await interaction.response.send_message(

        "✅ Ticket panel created.",

        ephemeral=True

    )





# ==========================================
# SERVER SETUP
# ==========================================


@bot.tree.command(
    name="setup",
    description="Setup 2K Esports channels"
)
async def setup(interaction:discord.Interaction):


    if not is_admin(interaction.user):

        return await interaction.response.send_message(
            "❌ Admin only.",
            ephemeral=True
        )



    guild=interaction.guild



    created=[]



    channels=[

        "welcome",

        "goodbye",

        "tickets",

        "suggestions",

        "mod-logs",

        "general"

    ]



    for name in channels:


        channel=find_channel(
            guild,
            name
        )


        if not channel:

            await guild.create_text_channel(
                name
            )

            created.append(name)




    role=discord.utils.get(

        guild.roles,

        name=AUTO_ROLE_NAME

    )


    if not role:


        await guild.create_role(

            name=AUTO_ROLE_NAME

        )



    await interaction.response.send_message(

        "✅ Setup complete.\nCreated:\n"
        +
        "\n".join(created)
        if created
        else
        "Everything already exists.",

        ephemeral=True

    )





# ==========================================
# ANTI SPAM SYSTEM
# ==========================================


spam_messages={}


@bot.event
async def on_message_edit(before,after):


    if before.author.bot:
        return


    if before.content != after.content:


        await send_modlog(

            before.guild,

            "✏️ Message Edited",

            f"{before.author.mention}\n\nBefore:\n{before.content}\n\nAfter:\n{after.content}",

            discord.Color.yellow()

        )





@bot.event
async def on_message_delete(message):


    if message.author.bot:

        return


    if message.guild:


        await send_modlog(

            message.guild,

            "🗑️ Message Deleted",

            f"{message.author.mention}\n\n{message.content}",

            discord.Color.red()

        )





async def security_check(message):


    if not message.guild:

        return



    if is_staff(message.author):

        return



    content=message.content.lower()



    # INVITE BLOCK


    for word in INVITE_WORDS:


        if word in content:


            await message.delete()


            await message.channel.send(

                f"❌ {message.author.mention} Discord invites are not allowed.",

                delete_after=5

            )


            return False




    # MASS MENTION


    if len(message.mentions)>=5:


        await message.delete()


        await message.channel.send(

            "❌ Mass mentions blocked.",

            delete_after=5

        )


        return False





    # SPAM


    uid=str(message.author.id)



    if uid not in spam_messages:

        spam_messages[uid]=[]



    spam_messages[uid].append(

        datetime.utcnow()

    )


    spam_messages[uid]=[

        x for x in spam_messages[uid]

        if (datetime.utcnow()-x).seconds < 5

    ]



    if len(spam_messages[uid])>=6:


        await message.delete()



        await message.channel.send(

            f"⚠️ {message.author.mention} slow down.",

            delete_after=5

        )


        return False



    return True





# ==========================================
# FINAL MESSAGE HANDLER FIX
# ==========================================


old_message_event = bot.on_message



@bot.event
async def on_message(message):


    if message.author.bot:

        return



    allowed=await security_check(message)


    if allowed:


        await bot.process_commands(message)





# ==========================================
# STAFF ACTIVITY
# ==========================================


@bot.command()
async def staffstats(ctx):


    if not is_staff(ctx.author):

        return



    embed=discord.Embed(

        title="🛡️ Staff System",

        description=
        "Staff activity tracking is active.",

        color=discord.Color.orange()

    )


    await ctx.send(embed=embed)





# ==========================================
# READY
# ==========================================


@bot.event
async def on_ready():


    await bot.tree.sync()



    print(
        f"""
========================
2K ESPORTS BOT ONLINE
Bot: {bot.user}
Servers: {len(bot.guilds)}
========================
"""
    )



    await bot.change_presence(

        activity=discord.Activity(

            type=discord.ActivityType.watching,

            name="2K Esports 🏀"

        )

    )





# ==========================================
# START BOT
# ==========================================


if TOKEN:

    bot.run(TOKEN)

else:

    print(
        "ERROR: DISCORD_TOKEN missing from .env"
    )
