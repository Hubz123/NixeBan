
# -*- coding: utf-8 -*-
import os, asyncio, json, logging
from typing import Optional
import discord

log = logging.getLogger(__name__)

_THREAD_CACHE = {}
_LOCKS = {}

def _get_lock(name: str) -> asyncio.Lock:
    if name not in _LOCKS:
        _LOCKS[name] = asyncio.Lock()
    return _LOCKS[name]

async def _find_existing(channel: discord.TextChannel, thread_name: str) -> Optional[discord.Thread]:
    try:
        for t in getattr(channel, "threads", []):
            if str(t.name).strip() == str(thread_name).strip():
                return t
    except Exception:
        pass
    try:
        async for t in channel.archived_threads(limit=200, private=False):
            if str(t.name).strip() == str(thread_name).strip():
                return t
    except Exception:
        pass
    try:
        async for t in channel.archived_threads(limit=50, private=True):
            if str(t.name).strip() == str(thread_name).strip():
                return t
    except Exception:
        pass
    return None

async def get_or_create_thread(
    bot: discord.Client,
    parent_channel_id: int,
    thread_name: str,
    cache_env_key: str = None,
    auto_archive_duration: int = 10080,
    reason: str = None,
) -> Optional[discord.Thread]:
    if not parent_channel_id:
        return None

    tid = _THREAD_CACHE.get(thread_name)
    if tid:
        ch = bot.get_channel(int(tid)) or await bot.fetch_channel(int(tid))
        if isinstance(ch, discord.Thread):
            return ch

    if cache_env_key:
        env_tid = (os.getenv(cache_env_key) or "").strip()
        if env_tid.isdigit():
            ch = bot.get_channel(int(env_tid)) or await bot.fetch_channel(int(env_tid))
            if isinstance(ch, discord.Thread):
                _THREAD_CACHE[thread_name] = int(env_tid)
                return ch

    async with _get_lock(thread_name):
        parent = bot.get_channel(int(parent_channel_id)) or await bot.fetch_channel(int(parent_channel_id))
        if not isinstance(parent, discord.TextChannel):
            return None

        exist = await _find_existing(parent, thread_name)
        if exist:
            try:
                if exist.archived:
                    await exist.edit(archived=False, reason=reason or "reopen")
            except Exception:
                pass
            _THREAD_CACHE[thread_name] = int(exist.id)
            if cache_env_key:
                os.environ[cache_env_key] = str(exist.id)
            return exist

        try:
            t = await parent.create_thread(
                name=thread_name,
                auto_archive_duration=auto_archive_duration,
                reason=reason or "create whitelist singleton",
            )
            _THREAD_CACHE[thread_name] = int(t.id)
            if cache_env_key:
                os.environ[cache_env_key] = str(t.id)
            return t
        except Exception as e:
            log.error("[thread-singleton] create failed: %s", e)
            return None
