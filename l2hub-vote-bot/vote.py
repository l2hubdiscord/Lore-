
import discord
from discord.ext import commands, tasks
import datetime
import json
import os

from views import VoteView
from utils import generate_embed

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

class VoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reset_voter_roles.start()

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

async def setup(bot):
    await bot.add_cog(VoteCog(bot))
