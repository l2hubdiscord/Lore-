
import discord
from discord.ext import commands, tasks
import datetime
import json
import os
from utils import generate_embed
from views import VoteView

LEADERBOARD_FILE = "leaderboard.json"
VOTES_FILE = "votes.json"
SERVERS_FILE = "servers.json"
LEADERBOARD_CHANNEL_NAME = "🥇︱leaderboards"

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

def load_servers():
    if os.path.exists(SERVERS_FILE):
        with open(SERVERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_servers(servers):
    with open(SERVERS_FILE, "w") as f:
        json.dump(servers, f, indent=2)

def save_leaderboard_message_id(message_id):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump({"message_id": message_id}, f)

def load_leaderboard_message_id():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r") as f:
            return json.load(f).get("message_id")
    return None

class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_refresh_date = None
        self.last_reset_date = None

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def refreshleaderboard(self, ctx):
        leaderboard_channel = discord.utils.get(ctx.guild.text_channels, name=LEADERBOARD_CHANNEL_NAME)
        if not leaderboard_channel:
            await ctx.send("❌ Δεν βρέθηκε το κανάλι 🥇︱leaderboards.")
            return

        await leaderboard_channel.purge()

        all_servers = load_servers()
        all_votes = load_votes()

        for s in all_servers:
            s["votes"] = all_votes.get(s["name"], {}).get("total", 0)

        premium_servers = [s for s in all_servers if s.get("premium")]
        non_premium_servers = [s for s in all_servers if not s.get("premium")]

        sorted_non_premiums = sorted(non_premium_servers, key=lambda x: (-x["votes"], x["name"].lower()))
        for idx, server in enumerate(sorted_non_premiums):
            server["rank"] = idx + 1

        sorted_non_premiums.reverse()
        final_list = sorted_non_premiums + premium_servers

        for server in final_list:
            embed = generate_embed(server, context="leaderboard")
            message = await leaderboard_channel.send(embed=embed)
            server["leaderboard_message_id"] = message.id

        save_servers(all_servers)

    @tasks.loop(minutes=1)
    async def update_leaderboard_loop(self):
        await self.bot.wait_until_ready()
        now = datetime.datetime.now()
        today = now.date()

        if now.hour == 6 and now.minute == 0:
            if self.last_refresh_date != today:
                for guild in self.bot.guilds:
                    channel = discord.utils.get(guild.text_channels, name=LEADERBOARD_CHANNEL_NAME)
                    if channel:
                        ctx = await self.bot.get_context(await channel.send("🔄"))
                        await self.refreshleaderboard(ctx)
                self.last_refresh_date = today

    @tasks.loop(minutes=10)
    async def reset_votes_loop(self):
        now = datetime.datetime.now()
        today = now.date()

        if now.day == 1 and self.last_reset_date != today:
            votes = load_votes()
            for server_data in votes.values():
                server_data["total"] = 0
                server_data["by_day"] = {}
            save_votes(votes)

            servers = load_servers()
            for server in servers:
                server["votes"] = 0
            save_servers(servers)

            for guild in self.bot.guilds:
                channel = discord.utils.get(guild.text_channels, name=LEADERBOARD_CHANNEL_NAME)
                if channel:
                    ctx = await self.bot.get_context(await channel.send("🔄"))
                    await self.refreshleaderboard(ctx)

            # Ενημέρωση των embeds στο 📜︱server-list
            for guild in self.bot.guilds:
                list_channel = discord.utils.get(guild.text_channels, name="📜︱server-list")
                if list_channel:
                    servers = load_servers()
                    for server in servers:
                        try:
                            message_id = server.get("message_id")
                            if message_id:
                                msg = await list_channel.fetch_message(message_id)
                                embed = generate_embed(server, context="serverlist")
                                await msg.edit(embed=embed, view=VoteView(server["name"]))
                        except Exception:
                            continue


            self.last_reset_date = today

    @reset_votes_loop.before_loop
    async def before_reset_votes(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.update_leaderboard_loop.is_running():
            self.update_leaderboard_loop.start()
        if not self.reset_votes_loop.is_running():
            self.reset_votes_loop.start()

async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot))
