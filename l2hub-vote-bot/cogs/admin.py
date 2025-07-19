
import discord
from discord.ext import commands
import json
import os
from utils import generate_embed
from views import VoteView
import aiohttp



SERVERS_FILE = "servers.json"
VOTES_FILE = "votes.json"

def load_servers():
    if os.path.exists(SERVERS_FILE):
        with open(SERVERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_servers(servers):
    with open(SERVERS_FILE, "w") as f:
        json.dump(servers, f, indent=2)

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

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        channel = discord.utils.get(ctx.guild.text_channels, name="📜server-list")
        if not channel:
            await ctx.send("❌ Δεν βρέθηκε το κανάλι 📜server-list.")
            return

        await channel.purge()

        servers = load_servers()
        votes = load_votes()

        for server in servers:
            server["votes"] = votes.get(server["name"], {}).get("total", 0)
            embed = generate_embed(server, context="serverlist")
            message = await channel.send(embed=embed, view=VoteView(server["name"]))
            server["message_id"] = message.id

        save_servers(servers)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addserver(self, ctx, name, chronicle, rates, website, discord_link, thumbnail, image=None):
        await ctx.message.delete()

        premium = image is not None
        votes = load_votes()
        servers = load_servers()

        new_server = {
            "name": name,
            "chronicle": chronicle,
            "rates": rates,
            "website": website,
            "discord": discord_link,
            "thumbnail": thumbnail,
            "premium": premium,
            "votes": 0
        }

        if premium:
            new_server["image"] = image

        embed = generate_embed(new_server, context="serverlist")
        channel = discord.utils.get(ctx.guild.text_channels, name="📜server-list")
        if not channel:
            await ctx.send("❌ Δεν βρέθηκε το κανάλι 📜server-list.")
            return

        message = await channel.send(embed=embed, view=VoteView(name))
        new_server["message_id"] = message.id

        servers.append(new_server)
        votes[name] = {"total": 0, "by_day": {}}
        save_votes(votes)
        save_servers(servers)

        # Προσθήκη View για μελλοντικό restart
        self.bot.add_view(VoteView(name))

    @commands.command(name="checkinvites")
    @commands.has_permissions(administrator=True)
    async def check_invites(self, ctx):
        with open("servers.json", "r", encoding="utf-8") as f:
            servers = json.load(f)

        invalid = []

        for server in servers:
            name = server["name"]
            invite = server.get("discord")
            if not invite:
                continue
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(invite) as resp:
                        if resp.status != 200:
                            invalid.append(f"❌ {name} – Invalid: {invite}")
            except Exception as e:
                invalid.append(f"❌ {name} – Invalid: {invite}")

        if not invalid:
            await ctx.send("✅ Όλα τα invite links είναι έγκυρα.", ephemeral=True)
            return

        # Σπάσιμο embed αν ξεπερνάμε το όριο
        MAX_CHARS = 3900
        current = ""
        embeds = []

        for line in invalid:
            if len(current) + len(line) > MAX_CHARS:
                embed = discord.Embed(
                    title="❌ Invalid Invite Links",
                    description=current,
                    color=discord.Color.red()
                )
                embeds.append(embed)
                current = ""
            current += line + "\n"

        if current:
            embed = discord.Embed(
                title="❌ Invalid Invite Links",
                description=current,
                color=discord.Color.red()
            )
            embeds.append(embed)

        for embed in embeds:
            await ctx.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
