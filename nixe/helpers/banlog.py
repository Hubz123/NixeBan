from __future__ import annotations
from typing import Optional
import discord
from ..config.self_learning_cfg import BAN_LOG_CHANNEL_ID
def get_ban_log_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    if not guild: return None
    if BAN_LOG_CHANNEL_ID:
        ch = guild.get_channel(BAN_LOG_CHANNEL_ID)
        if isinstance(ch, discord.TextChannel): return ch
    for c in guild.text_channels:
        if c.name.lower() in {'log-botphising','log-botphishing','log_botphising','log-phishing'}: return c
    return None
