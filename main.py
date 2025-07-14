import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import os
import json
import datetime
import re


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
last_refresh_date = None

VOTES_FILE = "votes.json"
ROLE_NAME = "✅ Voter"
SERVERS_FILE = "servers.json"


# Load servers from JSON or fallback to empty list
def load_servers():
    if os.path.exists(SERVERS_FILE):
        with open(SERVERS_FILE, "r") as f:
            return json.load(f)
    return []


def load_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, "r") as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    return {}


def save_votes(votes):
    with open(VOTES_FILE, "w") as f:
        json.dump(votes, f)


servers = load_servers()
server_votes = load_votes()


class VoteButton(Button):

    def __init__(self, server_id):
        super().__init__(label="🗳 Vote",
                         style=discord.ButtonStyle.success,
                         custom_id=f"vote_{server_id}")
        self.server_id = server_id

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        today = datetime.datetime.now().strftime("%Y-%m-%d")

        # Βρες τον server από το servers.json με βάση το ID
        server = next(
            (s
             for s in servers if s['name'].lower() == self.server_id.lower()),
            None)
        if not server or "message_id" not in server:
            await interaction.response.send_message(
                "⚠️ Δεν βρέθηκε το μήνυμα του server.", ephemeral=True)
            return

        server_name = server["name"]

        for data in server_votes.values():
            if today in data.get("by_day",
                                 {}) and user_id in data["by_day"][today]:
                await interaction.response.send_message(
                    "❗ Έχεις ήδη ψηφίσει έναν server σήμερα.", ephemeral=True)
                return

        # Προετοιμασία votes
        if server_name not in server_votes:
            server_votes[server_name] = {"total": 0, "by_day": {}}
        if today not in server_votes[server_name]["by_day"]:
            server_votes[server_name]["by_day"][today] = []

        server_votes[server_name]["by_day"][today].append(user_id)
        server_votes[server_name]["total"] += 1
        save_votes(server_votes)

        # Απόδοση ρόλου
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "⚠️ Δεν έγινε μέσα σε server.", ephemeral=True)
            return

        voter_role = discord.utils.get(guild.roles, name="✅ Voter")
        member = guild.get_member(interaction.user.id)
        if member and voter_role:
            await member.add_roles(voter_role)

        # Εύρεση καναλιού και ενημέρωση embed
        channel = discord.utils.get(guild.text_channels, name="📜server-list")
        if not channel:
            await interaction.response.send_message(
                "❌ Δεν βρέθηκε το κανάλι 📜server-list.", ephemeral=True)
            return

        try:
            message = await channel.fetch_message(server["message_id"])
        except discord.NotFound:
            await interaction.response.send_message(
                "⚠️ Το μήνυμα του server δεν βρέθηκε.", ephemeral=True)
            return

        if not message.embeds:
            await interaction.response.send_message(
                "⚠️ Δεν υπάρχει embed στο μήνυμα.", ephemeral=True)
            return

        embed = message.embeds[0]
        description = embed.description or ""
        new_votes = server_votes[server_name]["total"]

        # Ενημέρωση του description με zero-width space για forced render
        match = re.search(r"👍 Votes:[^\d]*(\d+)", description)
        if match:
            start, end = match.span(1)
            ZWSP = "\u200b"
            embed.description = description[:start] + str(
                new_votes) + ZWSP + description[end:]
        else:
            embed.description = description  # fallback

        # Ενημέρωση servers.json
        server["votes"] = new_votes
        with open(SERVERS_FILE, "w") as f:
            json.dump(servers, f, indent=2)

        await message.edit(embed=embed, view=self.view)
        await interaction.response.send_message(
            "✅ Thank you for voting!\n\nYou now have full access to:\n🏆 Leaderboards  \n📚 Guides  \n📖 Lores  \n💬 Community Chat\n\nSee you in 24 hours!",
            ephemeral=True)


class VoteView(View):

    def __init__(self, server_id):
        super().__init__(timeout=None)
        self.add_item(VoteButton(server_id))


@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    channel = discord.utils.get(ctx.guild.text_channels, name="📜server-list")
    if not channel:
        await ctx.send("❌ Δεν βρέθηκε το κανάλι 📜server-list.")
        return

    await channel.purge()

    for server in servers:
        title = f"👑 {server['name']}" if server.get(
            "premium") else server['name']
        color = discord.Color.gold() if server.get(
            "premium") else discord.Color.blue()
        votes = server_votes.get(server['name'], {}).get("total", 0)

        if server.get("premium"):
            description = (f"**⚔️ Chronicle:** {server['chronicle']}\n"
                           f"**🛡️ Rates:** {server['rates']}\n"
                           f"👍 Votes: {votes}\n\n"
                           f"🌐 {server['website']}\n"
                           f"💬 {server['discord']}")
            embed = discord.Embed(title=title,
                                  description=description,
                                  color=color)
            embed.set_thumbnail(url=server['thumbnail'])
            if server.get("image"):
                embed.set_image(url=server['image'])

        else:
            description = (f"**⚔️ Chronicle:** {server['chronicle']} "
                           f"**🛡️ Rates:** {server['rates']} "
                           f"**👍 Votes:** {votes}\n\n"
                           f"🌐 {server['website']}   💬 {server['discord']}")
            embed = discord.Embed(title=title,
                                  description=description,
                                  color=color)
            embed.set_thumbnail(url=server['thumbnail'])

        message = await channel.send(embed=embed,
                                     view=VoteView(server['name']))
        server["message_id"] = message.id

    with open(SERVERS_FILE, "w") as f:
        json.dump(servers, f, indent=2)


@bot.command()
@commands.has_permissions(administrator=True)
async def addserver(ctx,
                    name,
                    chronicle,
                    rates,
                    website,
                    discord_link,
                    thumbnail,
                    image=None):
    await ctx.message.delete()

    # Premium flag
    premium = image is not None

    # Βρες το κανάλι
    channel = discord.utils.get(ctx.guild.text_channels, name="📜server-list")
    if not channel:
        await ctx.send("❌ Δεν βρέθηκε το κανάλι 📜server-list.")
        return

    # Κατασκευή embed
    title = f"👑 {name}" if premium else name
    color = discord.Color.gold() if premium else discord.Color.blue()
    votes = 0

    if premium:
        description = (f"**⚔️ Chronicle:** {chronicle}\n"
                       f"**🛡️ Rates:** {rates}\n"
                       f"👍 Votes: {votes}\n\n"
                       f"🌐 {website}\n"
                       f"💬 {discord_link}")
        embed = discord.Embed(title=title,
                              description=description,
                              color=color)
        embed.set_thumbnail(url=thumbnail)
        embed.set_image(url=image)
    else:
        description = (f"**⚔️ Chronicle:** {chronicle} "
                       f"**🛡️ Rates:** {rates} "
                       f"**👍 Votes:** {votes}\n\n"
                       f"🌐 {website}   💬 {discord_link}")
        embed = discord.Embed(title=title,
                              description=description,
                              color=color)
        embed.set_thumbnail(url=thumbnail)

    # Αποστολή embed
    message = await channel.send(embed=embed, view=VoteView(name))

    # Ενημέρωση servers.json
    new_server = {
        "name": name,
        "chronicle": chronicle,
        "rates": rates,
        "website": website,
        "discord": discord_link,
        "thumbnail": thumbnail,
        "premium": premium,
        "message_id": message.id
    }
    if premium:
        new_server["image"] = image

    servers.append(new_server)
    with open(SERVERS_FILE, "w") as f:
        json.dump(servers, f, indent=2)

    # Ενημέρωση votes.json
    server_votes[name] = {"total": 0, "by_day": {}}
    save_votes(server_votes)

    # Προσθήκη View για μελλοντικό restart
    bot.add_view(VoteView(name))


@bot.command()
@commands.has_permissions(administrator=True)
async def resetvotes(ctx):
    for server_name in server_votes:
        server_votes[server_name] = {"total": 0, "by_day": {}}
    save_votes(server_votes)
    await ctx.send("✅ All votes have been reset manually.")
    print("🔁 Manual vote reset executed via command.")


@tasks.loop(minutes=1)
async def reset_votes_monthly():
    await bot.wait_until_ready()
    now = datetime.datetime.now()

    if now.day == 1 and now.hour == 5 and now.minute == 0:
        print("🔄 Resetting all votes for the new month...")
        for server_name in server_votes:
            server_votes[server_name] = {"total": 0, "by_day": {}}
        save_votes(server_votes)
        print("✅ Votes have been reset.")


@tasks.loop(minutes=1)
async def update_leaderboard_loop():
    await bot.wait_until_ready()
    now = datetime.datetime.now()

    global last_refresh_date
    today = now.date()

    if now.hour == 6 and now.minute == 0:
        if last_refresh_date != today:
            print("🔁 Auto updating leaderboard at 06:00...")
            for guild in bot.guilds:
                channel = discord.utils.get(guild.text_channels, name="🥇leaderboards")
                if channel:
                    ctx = await bot.get_context(await channel.send("🔄"))
                    await refreshleaderboard(ctx)
            last_refresh_date = today
            print("✅ Leaderboard updated.")


@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")
    reset_voter_roles.start()
    reset_votes_monthly.start()
    update_leaderboard_loop.start()

    # 👉 Επανεγγραφή των κουμπιών (VoteButton) μετά από restart
    for server in servers:
        if "message_id" in server:
            bot.add_view(VoteView(server['name']))
    print("🔁 Ξαναφορτώθηκαν τα κουμπιά των servers.")


@tasks.loop(hours=24)
async def reset_voter_roles():
    await bot.wait_until_ready()
    for guild in bot.guilds:
        voter_role = discord.utils.get(guild.roles, name="✅ Voter")
        if not voter_role:
            continue
        for member in guild.members:
            member = guild.get_member(member.id)
            if member and voter_role and voter_role in member.roles:
                try:
                    await member.remove_roles(voter_role)
                    print(
                        f"🔁 Removed '✅ Voter' role from {member.display_name}")
                except Exception as e:
                    print(
                        f"❌ Error removing role from {member.display_name}: {e}"
                    )


LEADERBOARD_FILE = "leaderboard.json"
LEADERBOARD_CHANNEL_NAME = "🥇leaderboards"


def save_leaderboard_message_id(message_id):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump({"message_id": message_id}, f)


def load_leaderboard_message_id():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r") as f:
            return json.load(f).get("message_id")
    return None


async def update_leaderboard(guild):
    leaderboard_channel = discord.utils.get(guild.text_channels,
                                            name=LEADERBOARD_CHANNEL_NAME)
    if not leaderboard_channel:
        print(
            f"❌ Δεν βρέθηκε κανάλι leaderboard με όνομα '{LEADERBOARD_CHANNEL_NAME}'"
        )
        return

    # Ταξινόμηση servers βάσει ψήφων (φθίνουσα σειρά)
    sorted_servers = sorted(server_votes.items(),
                            key=lambda item: item[1].get("total", 0),
                            reverse=True)

    description = ""
    for i, (server_name, data) in enumerate(sorted_servers, start=1):
        votes = data.get("total", 0)
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        description += f"{medal} **{server_name}** — {votes} votes\n"

    embed = discord.Embed(title="🏆 Top L2 Servers (Live)",
                          description=description,
                          color=discord.Color.gold())

    existing_message_id = load_leaderboard_message_id()
    if existing_message_id:
        try:
            message = await leaderboard_channel.fetch_message(
                existing_message_id)
            await message.edit(embed=embed)
            return
        except discord.NotFound:
            pass  # Αν δεν υπάρχει το μήνυμα, συνεχίζουμε να το δημιουργήσουμε

    new_message = await leaderboard_channel.send(embed=embed)
    save_leaderboard_message_id(new_message.id)


@bot.command()
@commands.has_permissions(administrator=True)
async def refreshleaderboard(ctx):
    leaderboard_channel = discord.utils.get(ctx.guild.text_channels,
                                            name="🥇leaderboards")
    if not leaderboard_channel:
        await ctx.send("❌ Δεν βρέθηκε το κανάλι 🥇leaderboards.")
        return

    await leaderboard_channel.purge()

    # Φόρτωσε servers και ψήφους
    with open("servers.json", "r") as f:
        all_servers = json.load(f)
    with open("votes.json", "r") as f:
        all_votes = json.load(f)

    # Ενημέρωσε κάθε server με τις ψήφους του
    for s in all_servers:
        s["votes"] = all_votes.get(s["name"], {}).get("total", 0)

    # Διαχωρισμός premium και non-premium
    premium_servers = [s for s in all_servers if s.get("premium")]
    non_premium_servers = [s for s in all_servers if not s.get("premium")]

    # Ταξινόμηση non-premium κατά ψήφους (φθίνουσα) και μετά αλφαβητικά
    sorted_non_premiums = sorted(non_premium_servers,
                                 key=lambda x:
                                 (-x["votes"], x["name"].lower()))

    # Ανάθεση δυναμικού rank: ο πρώτος έχει Rank 1
    for idx, server in enumerate(sorted_non_premiums):
        server["rank"] = idx + 1

    # Τελική λίστα: πρώτα οι non-premium (από λίγους προς πολλούς), μετά οι premium
    sorted_non_premiums.reverse()  # Rank 1 στο τέλος της λίστας
    final_list = sorted_non_premiums + premium_servers

    # Αποστολή embed για κάθε server
    for server in final_list:
        premium = server.get("premium", False)
        title = f"👑 {server['name']}" if premium else f"Rank {server['rank']}: {server['name']}"
        color = discord.Color.gold() if premium else discord.Color.blue()
        votes = server.get("votes", 0)

        if premium:
            description = (f"**⚔️ Chronicle:** {server['chronicle']}"
                           f"**🛡️ Rates:** {server['rates']}"
                           f"👍 Votes: {votes}"
                           f"🌐 {server['website']}"
                           f"💬 {server['discord']}")
        else:
            description = (f"**⚔️ Chronicle:** {server['chronicle']} "
                           f"**🛡️ Rates:** {server['rates']} "
                           f"**👍 Votes:** {votes}"
                           f"🌐 {server['website']}   💬 {server['discord']}")

        embed = discord.Embed(title=title,
                              description=description,
                              color=color)
        embed.set_thumbnail(url=server["thumbnail"])
        if premium and server.get("image"):
            embed.set_image(url=server["image"])

        message = await leaderboard_channel.send(embed=embed)
        server["leaderboard_message_id"] = message.id

    with open("servers.json", "w") as f:
        json.dump(all_servers, f, indent=2)

    print("✅ Leaderboard refreshed.")


token = os.getenv("YOUR_BOT_TOKEN")

if token:
    bot.run(token)
else:
    print("❌ Δεν βρέθηκε το token.")

