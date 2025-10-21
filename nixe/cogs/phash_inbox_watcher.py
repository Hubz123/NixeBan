from __future__ import annotations

import asyncio
import logging
from typing import Set, Tuple, Optional

import discord
from discord.ext import commands, tasks

# Keep config usage exactly as before — do NOT change variable names/types here.
from nixe.config.self_learning_cfg import (
    PHASH_WATCH_FIRST_DELAY,
    PHASH_WATCH_INTERVAL,
    PHASH_INBOX_THREAD,
)

log = logging.getLogger(__name__)

# Accept both comma-separated names and numeric IDs.
# IMPORTANT: No PEP585 annotation here (to avoid SyntaxError on some envs).
def _parse_inbox_tokens(raw):
    s = raw if isinstance(raw, str) else str(raw or "")
    tokens = [t.strip() for t in s.split(",") if t and t.strip()]
    ids: Set[int] = set()
    names: Set[str] = set()
    for t in tokens:
        if t.isdigit():
            try:
                ids.add(int(t))
            except Exception:
                pass
        else:
            names.add(t.lower())
    return names, ids

class NixePhashInboxWatcher(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # interval pulled from config (int). If zero, don't create loop.
        interval = int(PHASH_WATCH_INTERVAL or 0)
        if interval <= 0:
            self._loop_collect = None  # type: ignore[attr-defined]
        else:
            @tasks.loop(seconds=interval)
            async def _loop_collect():
                await self._tick()
            self._loop_collect = _loop_collect
            self._loop_collect.before_loop(self._before)  # type: ignore[union-attr]

    async def cog_load(self) -> None:
        if getattr(self, "_loop_collect", None):
            try:
                self._loop_collect.start()  # type: ignore[attr-defined]
            except RuntimeError:
                # Already started or bot not ready yet
                pass

    async def cog_unload(self) -> None:
        if getattr(self, "_loop_collect", None):
            try:
                self._loop_collect.stop()  # type: ignore[attr-defined]
            except Exception:
                pass

    async def _before(self) -> None:
        # First-delay (int). Keep behaviour intact.
        delay = int(PHASH_WATCH_FIRST_DELAY or 0)
        if delay > 0:
            await asyncio.sleep(delay)

    async def _tick(self) -> None:
        try:
            # Minimal placeholder: iterate guild channels and try resolve the thread
            for guild in self.bot.guilds:
                for ch in getattr(guild, "channels", []):
                    thread = await self._get_inbox_thread(ch)
                    # No-op if not found
                    if thread is not None:
                        # Placeholder behaviour: just log
                        log.debug("[phash-inbox] found inbox thread: %s (%s)", getattr(thread, "name", "?"), getattr(thread, "id", "?"))
        except Exception:
            log.debug("[phash-inbox] tick failure", exc_info=True)

    def _inbox_names(self) -> Set[str]:
        names, _ = _parse_inbox_tokens(PHASH_INBOX_THREAD)
        return names

    async def _get_inbox_thread(self, ch) -> Optional[discord.Thread]:
        names, ids = _parse_inbox_tokens(PHASH_INBOX_THREAD)
        # Try by ID
        try:
            for th in getattr(ch, "threads", []):
                if getattr(th, "id", None) in ids:
                    return th
        except Exception:
            pass
        # Fallback by name (case-insensitive)
        try:
            for th in getattr(ch, "threads", []):
                if getattr(th, "name", "").lower() in names:
                    return th
        except Exception:
            pass
        return None

async def setup(bot: commands.Bot):
    # Guard to avoid double add_cog if a loader already added it
    if 'NixePhashInboxWatcher' in getattr(bot, 'cogs', {}):
        return
    try:
        await bot.add_cog(NixePhashInboxWatcher(bot))
    except Exception:
        log.debug("setup: NixePhashInboxWatcher already loaded or failed softly", exc_info=True)
