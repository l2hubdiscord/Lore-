
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from views import VoteView
import json
from cogs.tickets import TicketView, ViewWithClaimClose, reattach_ticket_views

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

SERVERS_FILE = "servers.json"

@bot.event
async def on_ready():
    bot.add_view(TicketView())          # Dropdown
    bot.add_view(ViewWithClaimClose())  # Buttons Claim/Close
    await reattach_ticket_views(bot)    # <-- προσθήκη εδώ
    print(f"✅ Bot is online as {bot.user}")

    # Επανεγγραφή κουμπιών σε περίπτωση restart
    if os.path.exists(SERVERS_FILE):
        with open(SERVERS_FILE, "r") as f:
            servers = json.load(f)
            for server in servers:
                if "message_id" in server:
                    bot.add_view(VoteView(server['name']))
    print("🔁 Ξαναφορτώθηκαν τα κουμπιά των servers.")

async def load_all_cogs():
    await bot.load_extension("cogs.vote")
    await bot.load_extension("cogs.leaderboard")
    await bot.load_extension("cogs.admin")
    await bot.load_extension("cogs.tickets")


if __name__ == "__main__":
    token = os.getenv("YOUR_BOT_TOKEN")
    if token:
        import asyncio
        asyncio.run(load_all_cogs())
        bot.run(token)
    else:
        print("❌ Δεν βρέθηκε το token.")
