from __future__ import annotations
import os, re, logging
from typing import Set
import discord
from discord.ext import commands
try:
    from nixe.context_flags import mark_skip_phash
except Exception:
    def mark_skip_phash(_): return None
log = logging.getLogger(__name__)

def _ids(env: str) -> Set[int]:
    raw = os.getenv(env, "") or ""
    s: Set[int] = set()
    for p in raw.split(","):
        p = p.strip()
        if not p: continue
        try: s.add(int(p))
        except ValueError: pass
    return s

class LuckyPullGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.strict = (os.getenv("LUCKYPULL_STRICT_MODE", "1") == "1")
        self.allow_channels = _ids("LUCKYPULL_ALLOW_CHANNELS")
        self.guard_channels = _ids("LUCKYPULL_GUARD_CHANNELS")
        self._pat = re.compile(r"(?ix)(lucky\s*pull|wish|gacha|pull\s*\d+x|\d+x\s*pull|banner\s*result|hasil\s*pull|convene|warp)")

    def _target(self, ch_id: int) -> bool:
        if ch_id in self.allow_channels: return False
        return (ch_id in self.guard_channels) if self.guard_channels else True

    def _looks(self, m: discord.Message) -> bool:
        if not self.strict: return False
        for a in m.attachments:
            if self._pat.search((a.filename or "").lower()): return True
        return bool(m.content and self._pat.search(m.content.lower()))

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if m.author.bot: return
        ch = m.channel
        if not isinstance(ch, (discord.TextChannel, discord.Thread)): return
        if not self._target(ch.id): return
        if not self._looks(m): return
        try: mark_skip_phash(m.id)
        except Exception: pass
        try:
            await m.delete(reason="Lucky Pull in non-allowed channel")
            log.info("[lucky_pull_guard] deleted in #%s (%s)", getattr(ch, "name", "?"), ch.id)
        except Exception: log.debug("[lucky_pull_guard] delete failed", exc_info=True)

async def setup(bot: commands.Bot):
    # Avoid duplicate registration if loader already added this cog
    if 'LuckyPullGuard' in getattr(bot, 'cogs', {}):
        return
    try:
        await bot.add_cog(LuckyPullGuard(bot))
    except Exception:
        # If already loaded or another race, swallow to keep startup healthy
        import logging; logging.getLogger(__name__).debug("setup: LuckyPullGuard already loaded or failed softly", exc_info=True)
