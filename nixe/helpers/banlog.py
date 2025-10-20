from __future__ import annotations
from typing import Optional, List
import discord

# Prefer light import: only constants
try:
    from ..config.self_learning_cfg import BAN_LOG_CHANNEL_ID
except Exception:
    BAN_LOG_CHANNEL_ID = 0

def get_ban_log_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    """Resolve the ban/log channel.
    Priority:
      1) ENV/CFG BAN_LOG_CHANNEL_ID
      2) Common fallbacks by name
    """
    if not guild:
        return None
    if BAN_LOG_CHANNEL_ID:
        ch = guild.get_channel(BAN_LOG_CHANNEL_ID)
        if isinstance(ch, discord.TextChannel):
            return ch
    for c in guild.text_channels:
        if c.name.lower() in {'log-botphising','log-botphishing','log_botphising','log-phishing'}:
            return c
    return None

def _default_thread_names() -> List[str]:
    """Take thread names from config image section if available; otherwise common defaults."""
    names: List[str] = []
    try:
        from ..config import load as _load
        img = _load('image')
        names = (img.get('THREADS_LIST') or []) or [
            s.strip() for s in str(img.get('IMAGE_PHISH_THREAD_NAMES') or '').split(',') if s.strip()
        ]
    except Exception:
        names = []
    if not names:
        names = ['imagephising','imagelogphising','image-phising','image_phising','image-phishing','image_phishing']
    # unique & lowercase
    seen = set(); out: List[str] = []
    for n in names:
        n = n.strip().lower()
        if n and n not in seen:
            seen.add(n); out.append(n)
    return out

async def ensure_ban_thread(guild: discord.Guild, *, names: Optional[List[str]] = None, create: bool = False) -> Optional[discord.Thread]:
    """Leina-compatible helper.
    Find (and optionally create) a thread inside the ban/log channel that matches `names`.
    If `names` is None, it uses config image thread names.
    Returns the thread or None.
    """
    ch = get_ban_log_channel(guild)
    if not isinstance(ch, discord.TextChannel):
        return None
    wanted = [s.strip().lower() for s in (names or _default_thread_names()) if s.strip()]
    if not wanted:
        return None
    # active threads
    try:
        for t in list(ch.threads):
            if isinstance(t, discord.Thread) and t.name.lower() in wanted:
                return t
    except Exception:
        pass
    # archived threads (fetch limited)
    try:
        async for t in ch.archived_threads(limit=50):
            if isinstance(t, discord.Thread) and t.name.lower() in wanted:
                return t
    except Exception:
        pass
    if create:
        try:
            return await ch.create_thread(name=wanted[0], type=discord.ChannelType.public_thread)
        except Exception:
            return None
    return None

__all__ = ["get_ban_log_channel", "ensure_ban_thread"]
