
import discord
from discord.ui import Button, View
from utils import generate_embed
import json
import datetime
import os

VOTES_FILE = "votes.json"
SERVERS_FILE = "servers.json"

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

class VoteButton(Button):
    def __init__(self, server_id):
        super().__init__(
            label="Vote",
            style=discord.ButtonStyle.primary,
            custom_id=f"vote_{server_id}"
        )
        self.server_id = server_id

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        votes = load_votes()
        servers = load_servers()

        server = next((s for s in servers if s['name'].lower() == self.server_id.lower()), None)
        if not server or "message_id" not in server:
            await interaction.response.send_message("⚠️ Δεν βρέθηκε το μήνυμα του server.", ephemeral=True)
            return

        server_name = server["name"]

        for data in votes.values():
            if today in data.get("by_day", {}) and user_id in data["by_day"][today]:
                await interaction.response.send_message("❗ Έχεις ήδη ψηφίσει έναν server σήμερα.", ephemeral=True)
                return

        if server_name not in votes:
            votes[server_name] = {"total": 0, "by_day": {}}
        if today not in votes[server_name]["by_day"]:
            votes[server_name]["by_day"][today] = []

        votes[server_name]["by_day"][today].append(user_id)
        votes[server_name]["total"] += 1
        save_votes(votes)

        # Απόδοση ρόλου
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("⚠️ Δεν έγινε μέσα σε server.", ephemeral=True)
            return

        voter_role = discord.utils.get(guild.roles, name="✅ Voter")
        member = guild.get_member(interaction.user.id)
        if member and voter_role:
            await member.add_roles(voter_role)

        # Ενημέρωση του embed στο 📜server-list
        channel = discord.utils.get(guild.text_channels, name="📜server-list")
        if not channel:
            await interaction.response.send_message("❌ Δεν βρέθηκε το κανάλι 📜server-list.", ephemeral=True)
            return

        try:
            message = await channel.fetch_message(server["message_id"])
        except discord.NotFound:
            await interaction.response.send_message("⚠️ Το μήνυμα του server δεν βρέθηκε.", ephemeral=True)
            return

        server["votes"] = votes[server_name]["total"]
        embed = generate_embed(server, context="serverlist")
        await message.edit(embed=embed, view=VoteView(server["name"]))

        # Ενημέρωση servers.json
        with open(SERVERS_FILE, "w") as f:
            json.dump(servers, f, indent=2)

            await interaction.response.send_message(
                "✅ Thank you for voting!\n\n"
                "You now have full access to:\n"
                "🏆 Leaderboards\n"
                "📚 Guides\n"
                "📖 Lores\n"
                "💬 Community Chat\n\n"
                "See you in 24 hours!",
                ephemeral=True
            )


class VoteView(View):
    def __init__(self, server_id):
        super().__init__(timeout=None)
        self.add_item(VoteButton(server_id))
