import discord
from discord.ext import commands
import asyncio

MODERATOR_ROLE_ID = 1392795214397050971
ADMIN_USER_ID = 374615142723485698

TICKET_REASONS = {
    "general_support": {"label": "General Support", "emoji": "📌", "description": "Ask for help with general issues or questions about the community."},
    "report_user": {"label": "Report User", "emoji": "🚩", "description": "Report a user for breaking rules"},
    "report_bug": {"label": "Report Bug", "emoji": "🐞", "description": "Report bugs or glitches"},
    "add_server": {"label": "Add Server", "emoji": "➕", "description": "Submit your server for listing or promotion."},
    "other": {"label": "Other", "emoji": "❓", "description": "Anything else you need help with"}
}



class ClaimButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Claim Ticket",
            emoji="🔒",
            custom_id="claim_ticket"
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or MODERATOR_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("Only staff can claim tickets.", ephemeral=True)
            return

        if interaction.message is None:
            await interaction.response.send_message("Could not retrieve message context.", ephemeral=True)
            return

        self.disabled = True
        self.label = f"Claimed by {interaction.user.name}"

        view = discord.ui.View(timeout=None)

        for action_row in interaction.message.components:
            for comp in getattr(action_row, "children", []):  # type: ignore
                if isinstance(comp, discord.ui.Button) and comp.custom_id == "claim_ticket":
                    view.add_item(self)
                elif isinstance(comp, discord.ui.Button):  # type: ignore
                    view.add_item(discord.ui.Button(
                        style=comp.style,         # type: ignore
                        label=comp.label,         # type: ignore
                        emoji=comp.emoji,         # type: ignore
                        custom_id=comp.custom_id, # type: ignore
                        disabled=comp.disabled    # type: ignore
                    ))
                elif isinstance(comp, discord.ui.Select):  # σε περίπτωση dropdown
                    view.add_item(discord.ui.Select(
                        placeholder=comp.placeholder,  # type: ignore
                        options=comp.options,          # type: ignore
                        custom_id=comp.custom_id,      # type: ignore
                        disabled=comp.disabled         # type: ignore
                    ))

        view.add_item(CloseButton())  

        await interaction.message.edit(view=view)
        await interaction.response.send_message(f"{interaction.user.mention} has claimed this ticket.", ephemeral=False)





class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Close Ticket",
            emoji="❌",
            custom_id="close_ticket"
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This command must be used in a text channel.", ephemeral=True)
            return

        await interaction.response.send_message("This ticket will be closed in 10 seconds...", ephemeral=True)
        await interaction.channel.send("Closing ticket in 10 seconds...")

        await asyncio.sleep(10)
        await interaction.channel.delete()


class ViewWithClaimClose(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # persistent view
        self.add_item(ClaimButton())
        self.add_item(CloseButton())



class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=data["label"],
                value=key,
                emoji=data["emoji"],
                description=data["description"]
            )
            for key, data in TICKET_REASONS.items()
        ]
        super().__init__(
            placeholder="Select the reason for your ticket...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_reason_dropdown"
        )


    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This must be used by a server member.", ephemeral=True)
            return

        member = interaction.user
        bot_member = guild.me
        default_role = guild.default_role
        mod_role = guild.get_role(MODERATOR_ROLE_ID)

        if not default_role or not mod_role:
            await interaction.response.send_message("Required roles not found.", ephemeral=True)
            return

        # ✅ Anti-spam: μην ανοίγεις δεύτερο ticket για τον ίδιο user
        existing = discord.utils.find(
            lambda c: c.name.startswith(f"ticket-{member.name.lower()}"),
            guild.text_channels
        )
        if existing:
            await interaction.response.send_message(
                f"You already have an open ticket: {existing.mention}",
                ephemeral=True
            )
            return

        reason_key = self.values[0]
        reason_data = TICKET_REASONS[reason_key]

        overwrites = {
            default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            mod_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            bot_member: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        channel_name = f"ticket-{member.name.lower()}"
        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,  # type: ignore
            position=0
        )

        embed = discord.Embed(
            title=f"{reason_data['emoji']} {reason_data['label']}",
            description=(
                f"Hello {member.mention}, support will be with you shortly.\n\n"
                f"Our support team will assist you shortly."
            ),
            color=discord.Color.red()
        )

        # View με Claim / Close
        view = ViewWithClaimClose()

        # Στέλνουμε και ΚΑΤΑΧΩΡΟΥΜΕ το view ως persistent για αυτό το μήνυμα
        msg = await channel.send(embed=embed, view=view)
        interaction.client.add_view(view, message_id=msg.id)

        # Αν είναι Add Server, στέλνουμε template
        if reason_key == "add_server":
            await channel.send(
                "**Please provide your server details using the template below:**\n\n"
                "```yaml\n"
                "Server Name: \n"
                "Website: \n"
                "Discord Invite: \n"
                "Thumbnail URL: \n"
                "Description: \n"
                "```"
            )

        # DM στον admin
        admin_user = guild.get_member(ADMIN_USER_ID)
        if admin_user:
            try:
                await admin_user.send(
                    f"📬 New ticket created by **{member}**\nChannel: {channel.mention}\nReason: **{reason_data['label']}**"
                )
            except discord.Forbidden:
                print("Cannot send DM to admin.")

        # Ephemeral μήνυμα στον χρήστη
        await interaction.response.send_message(f"Your ticket has been created: {channel.mention}", ephemeral=True)






class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


class tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setticket")
    @commands.has_permissions(administrator=True)
    async def setticket(self, ctx):
        await ctx.channel.purge()

        embed = discord.Embed(
            title="📩 Support Ticket System",
            description=(
                "**Welcome! Need help? Choose a category below to open a ticket.**\n\n"
                "*Please reply to all so that everyone—including our office team—sees your message for full transparency.*\n\n"
                "📌 **General Support**\nAsk for help with general issues or questions about the community\n"
                "🚩 **Report User**\nReport a user for breaking rules\n"
                "🐞 **Report Bug**\nReport bugs or glitches\n"
                "➕ **Add Server**\nSubmit your server for listing or promotion\n"
                "❓ **Other**\nAnything else you need help with\n\n"
                "_Our team will respond as soon as possible!_"
            ),
            color=discord.Color.dark_red()
        )

        await ctx.send(embed=embed, view=TicketView())



async def setup(bot):
    await bot.add_cog(tickets(bot))
