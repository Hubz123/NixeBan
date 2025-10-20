from __future__ import annotations
import os
try:
    import discord  # type: ignore
    from ..helpers.once import once_sync as _once
    _real_ban = discord.Guild.ban
    async def _ban_once(self, user, *args, **kwargs):
        ttl = int(os.getenv("BAN_DEDUP_TTL", "10"))
        uid = getattr(user, "id", user)
        key = f"ban:{self.id}:{uid}"
        if not _once(key, ttl=ttl):
            return  # duplicate within TTL; skip silently
        return await _real_ban(self, user, *args, **kwargs)
    discord.Guild.ban = _ban_once
except Exception as e:
    print("[WARN] ban dedupe patch not applied:", e)