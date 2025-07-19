import discord

CHRONICLE_COLORS = {
    "interlude": "#1C7BB9",
    "high five": "#8552f2",
    "essence": "#016903",
    "classic": "#314507",
    "how": "#4c1ea1",
    "rod": "#4c1ea1",
    "sod": "#4c1ea1",
    "gracia final": "#f29829",
    "gracia epilogue": "#f29828",
    "freya": "#3b9cd9"
}

FEATURE_MAP = {
    "auto_farm": "Auto Events",
    "buff_store": "NPC Buffer",
    "custom_events": "Custom Zones",
    "retail": "Retail Like",
    "dualbox_limit": "Multi box",
    "customs": "Custom Set",
    "skins": "Costumes",
    "global_gk": "Global GK"
}

STYLE_EMOJI = {
    "pvp server": "🗡️",
    "craft server": "⛏️",
    "low rate": "🌿"
}

SEP = "\u202F•\u202F"


def generate_embed(server: dict, context: str) -> discord.Embed:
    # === Βασικά στοιχεία ===
    name = server.get("name", "Unknown Server")
    chronicle = server.get("chronicle", "Unknown").lower().strip()
    style = server.get("style", None)
    rates = server.get("rates", "")
    votes = server.get("votes", 0)
    website = server.get("website", "#")
    discord_link = server.get("discord", "#")
    thumbnail = server.get("thumbnail", "")
    image = server.get("image", "")
    premium = server.get("premium", False)
    rank = server.get("rank", None)
    spoil = server.get("spoil", "").strip()

    # === Rates split ===
    xp, sp, adena, drop = ["?"] * 4
    rate_parts = [part.strip().lower().replace("x", "") for part in rates.split("/")]
    if rate_parts:
        xp = rate_parts[0] if len(rate_parts) > 0 else "?"
        sp = rate_parts[1] if len(rate_parts) > 1 else "?"
        adena = rate_parts[2] if len(rate_parts) > 2 else "?"
        drop = rate_parts[3] if len(rate_parts) > 3 else "?"

    # === Features ===
    enabled_features = [label for key, label in FEATURE_MAP.items() if server.get(key)]
    features_text = " • ".join(enabled_features) if enabled_features else "N/A"

    # === Style Emoji ===
    style_emoji = STYLE_EMOJI.get(style.lower(), "") if style else ""

    # === Τίτλος ===
    if premium:
        title = f"👑 {name}"
    elif context == "leaderboard" and rank is not None:
        title = f"Rank {rank}: {name}"
    else:
        title = name

    # === Χρώμα ===
    hex_color = CHRONICLE_COLORS.get(chronicle, "#95a5a6")
    color = discord.Color.gold() if premium else discord.Color(int(hex_color.lstrip("#"), 16))

    # === Περιγραφή ===
    if premium:
        desc_lines = [
            f"🍁 **Chronicle:** {chronicle.capitalize()}",
            f"👍 **Votes:** {votes}",
            f"{style_emoji} **{style}**" if style else "",
            "",
            "⚔️ **Rates:**",
            f"• XP x{xp}",
            f"• SP x{sp}",
            f"• Adena x{adena}",
            f"• Drop x{drop}",
            f"• Spoil x{spoil}" if spoil and spoil != "?" else "",
            "",
            "🧩 **Features:**",
            *(f"• {f}" for f in enabled_features),
            "",
            f"🔗 [Website]({website}) • [Discord]({discord_link})"
        ]
    else:
        rates_line = f"⚔️ **Rates:** **XP** x{xp} {SEP} **SP** x{sp} {SEP} **Adena** x{adena} {SEP} **Drop** x{drop}"
        if spoil and spoil != "?":
            rates_line += f" {SEP} **Spoil** x{spoil}"

        desc_lines = [
            f"🍁 **Chronicle:** {chronicle.capitalize()}" +
            (f"{SEP}{style_emoji} **{style}**" if style else "") +
            f"{SEP}👍 **Votes:** {votes}",
            rates_line,
            f"🧩 **Features:** {features_text}",
            f"📌 **More infos:** 🔗 **Visit:** [Website]({website}) {SEP} 💬 **Join:** [Discord]({discord_link})"
        ]

    description = "\n".join([line for line in desc_lines if line.strip()])

    # === Κατασκευή Embed ===
    embed = discord.Embed(title=title, description=description, color=color)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if premium and image:
        embed.set_image(url=image)

    return embed
