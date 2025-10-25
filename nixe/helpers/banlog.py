import os, logging, discord
from typing import Optional
__all__=['get_log_channel','get_ban_log_channel','ensure_ban_thread']
log=logging.getLogger(__name__)
LOG_CH_ID=int(os.getenv('LOG_CHANNEL_ID','0') or 0)
BAN_LOG_CH_ID=int(os.getenv('NIXE_BAN_LOG_CHANNEL_ID', str(LOG_CH_ID)) or 0)
PREF=(os.getenv('MOD_LOG_CHANNEL_NAME','nixe-only') or 'nixe-only').lower()
BLOCKED=int(os.getenv('LOG_CHANNEL_ID','0') or 0)

def _prefer(ch):
    if not ch: return None
    if getattr(ch,'id',0)==BLOCKED: return None
    return ch

async def get_log_channel(guild: discord.Guild)->Optional[discord.TextChannel]:
    if BAN_LOG_CH_ID:
        try:
            ch=guild.get_channel(BAN_LOG_CH_ID) or await guild.fetch_channel(BAN_LOG_CH_ID)
            ch=_prefer(ch)
            if ch: return ch
        except Exception: pass
    if LOG_CH_ID and LOG_CH_ID!=BAN_LOG_CH_ID:
        try:
            ch=guild.get_channel(LOG_CH_ID) or await guild.fetch_channel(LOG_CH_ID)
            ch=_prefer(ch)
            if ch: return ch
        except Exception: pass
    try:
        for c in guild.text_channels:
            if (c.name or '').lower()==PREF and c.id!=BLOCKED: return c
    except Exception: pass
    return None

async def get_ban_log_channel(guild: discord.Guild):
    return await get_log_channel(guild)

async def ensure_ban_thread(ch: discord.TextChannel):
    if not ch or ch.id==BLOCKED: return None
    return None
