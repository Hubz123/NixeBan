# nixe/helpers/banlog.py
from __future__ import annotations
from typing import Optional
import discord
from ..config.self_learning_cfg import BAN_LOG_CHANNEL_ID

def get_ban_log_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    if not guild:
        return None
    ch = None
    if BAN_LOG_CHANNEL_ID:
        ch = guild.get_channel(BAN_LOG_CHANNEL_ID)
    if ch and isinstance(ch, discord.TextChannel):
        return ch
    # fallback kecil: cari nama standar
    names = {"log-botphising", "log-botphishing", "log_botphising", "log-phishing"}
    for c in guild.text_channels:
        if c.name.lower() in names:
            return c
    return None

async def ensure_ban_thread(channel: discord.TextChannel):
    # Kompat: jika Leina biasa membuat thread per kasus, di sini cukup no-op
    # Return channel saja; implementasi thread spesifik bisa ditambah bila perlu.
    return channel
