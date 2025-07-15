
import discord

def generate_embed(server: dict, context: str) -> discord.Embed:
    """
    Δημιουργεί ένα κοινό embed για χρήση σε serverlist ή leaderboard.

    Args:
        server (dict): Τα δεδομένα του server από το servers.json
        context (str): "serverlist" ή "leaderboard"

    Returns:
        discord.Embed: Το τελικό embed
    """
    name = server.get("name", "Unknown Server")
    chronicle = server.get("chronicle", "Unknown")
    rates = server.get("rates", "N/A")
    votes = server.get("votes", 0)
    website = server.get("website", "#")
    discord_link = server.get("discord", "#")
    thumbnail = server.get("thumbnail", "")
    image = server.get("image", None)
    premium = server.get("premium", False)
    rank = server.get("rank", None)

    # Τίτλος
    if premium:
        title = f"👑 {name}"
    elif context == "leaderboard" and rank is not None:
        title = f"Rank {rank}: {name}"
    else:
        title = name

    # Χρώμα
    color = discord.Color.gold() if premium else discord.Color.blue()

    # Περιγραφή με hyperlinks (μέσα στο embed)
    line1 = f"**⚔️ Chronicle:** {chronicle} **🛡️ Rates:** {rates} **👍 Votes:** {votes}"
    line2 = f"🌐 [Visit Website]({website})  💬 [Join Discord]({discord_link})"
    description = f"{line1}\n\n{line2}"


    embed = discord.Embed(title=title, description=description, color=color)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if premium and image:
        embed.set_image(url=image)

    return embed
