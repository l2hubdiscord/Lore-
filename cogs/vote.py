
import discord
from discord.ext import commands, tasks
import datetime
import json
import os

from views import VoteView
from utils import generate_embed

LAST_RESET_FILE = "last_reset.json"
VOTES_FILE = "votes.json"
SERVERS_FILE = "servers.json"
ROLE_NAME = "✅ Voter"

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

def load_last_reset():
    if os.path.exists(LAST_RESET_FILE):
        with open(LAST_RESET_FILE, "r") as f:
            return json.load(f)
    return {"last_reset_date": None}

def save_last_reset(date_str):
    with open(LAST_RESET_FILE, "w") as f:
        json.dump({"last_reset_date": date_str}, f)

class VoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reset_voter_roles.start()
        self.reset_votes_monthly.start()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def resetvotes(self, ctx):
        votes = load_votes()
        for server_name in votes:
            votes[server_name] = {"total": 0, "by_day": {}}
        save_votes(votes)
        await ctx.send("✅ All votes have been reset manually.")
        print("🔁 Manual vote reset executed via command.")

    @tasks.loop(hours=24)
    async def reset_voter_roles(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            voter_role = discord.utils.get(guild.roles, name=ROLE_NAME)
            if not voter_role:
                continue
            for member in guild.members:
                if voter_role in member.roles:
                    try:
                        await member.remove_roles(voter_role)
                        print(f"🔁 Removed '✅ Voter' role from {member.display_name}")
                    except Exception as e:
                        print(f"❌ Error removing role from {member.display_name}: {e}")

    @tasks.loop(hours=24)
    async def reset_votes_monthly(self):
        await self.bot.wait_until_ready()
        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        last_reset = load_last_reset()

        if now.day != 1 or last_reset["last_reset_date"] == today_str:
            return

        votes = load_votes()
        for server_name in votes:
            votes[server_name]["total"] = 0
            votes[server_name]["by_day"] = {}
        save_votes(votes)
        save_last_reset(today_str)
        print("🗓️ Votes reset for all servers (monthly).")

async def setup(bot):
    await bot.add_cog(VoteCog(bot))
