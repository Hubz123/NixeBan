import discord, asyncio, logging
from typing import Optional

log = logging.getLogger("nixe.locator")

async def find_text_channel(guild: discord.Guild, *, channel_id: int = 0, channel_name: str = "") -> Optional[discord.TextChannel]:
    if channel_id:
        ch = guild.get_channel(channel_id)
        if isinstance(ch, discord.TextChannel):
            return ch
    if channel_name:
        for ch in guild.text_channels:
            if ch.name.lower() == channel_name.lower():
                return ch
    return None

async def find_thread(guild: discord.Guild, *, thread_id: int = 0, thread_name: str = "", parent_hint: Optional[discord.TextChannel] = None):
    if thread_id:
        th = guild.get_thread(thread_id)
        if th: return th
    # search in active + archived under parent_hint if provided, else over all
    parents = [parent_hint] if parent_hint else guild.text_channels
    for parent in parents:
        for th in parent.threads:
            if th.name.lower() == thread_name.lower():
                return th
        try:
            async for th in parent.archived_threads(limit=50):
                if th.name.lower() == thread_name.lower():
                    return th
        except Exception:
            pass
    return None

async def ensure_thread(guild: discord.Guild, *, thread_name: str, parent: discord.TextChannel, reason: str = "ensure imagephising thread"):
    # Create a public thread under the parent if missing
    try:
        th = await find_thread(guild, thread_name=thread_name, parent_hint=parent)
        if th:
            return th, False
        # Need permission: create_public_threads
        th = await parent.create_thread(name=thread_name, reason=reason)
        log.info("Created thread %s under %s", thread_name, parent.name)
        return th, True
    except Exception as e:
        log.warning("ensure_thread failed: %s", e)
        return None, False