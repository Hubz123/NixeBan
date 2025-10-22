
from __future__ import annotations
import os, re, asyncio, logging
from typing import Optional, Set, List

import discord
from discord.ext import commands, tasks

log = logging.getLogger("nixe.cogs.phash_leina_bridge")

# --- Config (defaults baked-in; can override via ENV) ---
LEINA_SOURCE_THREAD_ID = int(os.getenv("LEINA_SOURCE_THREAD_ID", os.getenv("PHASH_SOURCE_THREAD_ID", "1409949797313679492")))
LEINA_SOURCE_CHANNEL_ID = int(os.getenv("LEINA_SOURCE_CHANNEL_ID", "0"))
LEINA_TITLE = os.getenv("LEINA_DB_TITLE", "SATPAMBOT_PHASH_DB_V1")
LEINA_JSON_KEY = os.getenv("LEINA_JSON_KEY", "phash")

DEST_DB_THREAD_ID = int(os.getenv("PHASH_DB_THREAD_ID", "1430048839556927589"))
IMPORT_MARKER = os.getenv("LEINA_IMPORT_MARKER", "[leina-phash-import]")
TICK_SEC = int(os.getenv("LEINA_BRIDGE_EVERY_SEC", "300"))
MAX_BYTES = int(os.getenv("LEINA_IMPORT_MAX_BYTES", "1800"))

HEX16 = re.compile(r"\b[0-9a-f]{16}\b")

def _collect_tokens(text: str, out: Set[str]) -> None:
    if not text:
        return
    for tok in HEX16.findall(text.lower()):
        out.add(tok)

async def _ensure_unarchived(th: discord.Thread) -> None:
    try:
        if getattr(th, "archived", False):
            await th.edit(archived=False)
    except Exception:
        pass

def _render_import_message(tokens: List[str], title: str, key: str) -> str:
    """Build JSON block like Leina and fit under MAX_BYTES without funky escaping."""
    head = f"{title}\n\n```json\n{{\n\"{key}\": [\n"
    tail = "\n]\n}\n```\n" + IMPORT_MARKER

    def body_for(n: int) -> str:
        if n <= 0:
            return ""
        lines = [f"\"{t}\"," for t in tokens[:n]]
        lines[-1] = lines[-1].rstrip(",")
        return "\n".join(lines)

    # Binary search for max items that fit
    lo, hi, best = 0, len(tokens), 0
    while lo <= hi:
        mid = (lo + hi) // 2
        trial = head + body_for(mid) + tail
        if len(trial) <= MAX_BYTES:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1

    return head + body_for(best) + tail

class PhashLeinaBridge(commands.Cog):
    """Read Leina's JSON board and mirror tokens into a single pinned message in Nixe DB thread."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._src_th: Optional[discord.Thread] = None
        self._src_ch: Optional[discord.TextChannel] = None
        self._dest: Optional[discord.Thread] = None
        self._msg: Optional[discord.Message] = None
        self._tick.start()

    def cog_unload(self):
        self._tick.cancel()

    async def _load_sources(self) -> None:
        if DEST_DB_THREAD_ID and self._dest is None:
            ch = await self.bot.fetch_channel(DEST_DB_THREAD_ID)
            if isinstance(ch, discord.Thread):
                self._dest = ch
                await _ensure_unarchived(ch)
        if LEINA_SOURCE_THREAD_ID and self._src_th is None:
            try:
                th = await self.bot.fetch_channel(LEINA_SOURCE_THREAD_ID)
                if isinstance(th, discord.Thread):
                    self._src_th = th
                    await _ensure_unarchived(th)
            except Exception:
                pass
        if LEINA_SOURCE_CHANNEL_ID and self._src_ch is None:
            try:
                ch = await self.bot.fetch_channel(LEINA_SOURCE_CHANNEL_ID)
                if isinstance(ch, discord.TextChannel):
                    self._src_ch = ch
            except Exception:
                pass

    async def _find_or_create_import_message(self) -> None:
        if not self._dest:
            return
        try:
            pins = await self._dest.pins()
        except Exception:
            pins = []
        for p in pins:
            if IMPORT_MARKER in (p.content or ""):
                self._msg = p
                return
        async for m in self._dest.history(limit=200, oldest_first=False):
            if IMPORT_MARKER in (m.content or ""):
                self._msg = m
                try:
                    await m.pin(reason="Pin Leina import")
                except Exception:
                    pass
                return
        created = await self._dest.send(content=IMPORT_MARKER + "\n(empty)")
        try:
            await created.pin(reason="Pin Leina import")
        except Exception:
            pass
        self._msg = created

    async def _pull_tokens_from_leina(self) -> List[str]:
        tokens: Set[str] = set()
        sources = []
        for src in (self._src_th, self._src_ch):
            if not src:
                continue
            try:
                sources.extend(await src.pins())
            except Exception:
                pass
        for m in sources:
            _collect_tokens(m.content or "", tokens)
        for src in (self._src_th, self._src_ch):
            if not src:
                continue
            async for m in src.history(limit=None if src is self._src_th else 500, oldest_first=True):
                _collect_tokens(m.content or "", tokens)
        # Stable, first-appearance order
        order: List[str] = []
        seen: Set[str] = set()
        for m in sources:
            for tok in HEX16.findall((m.content or "").lower()):
                if tok in tokens and tok not in seen:
                    seen.add(tok)
                    order.append(tok)
        for src in (self._src_th, self._src_ch):
            if not src:
                continue
            async for m in src.history(limit=None if src is self._src_th else 500, oldest_first=True):
                for tok in HEX16.findall((m.content or "").lower()):
                    if tok in tokens and tok not in seen:
                        seen.add(tok)
                        order.append(tok)
        return order

    async def _update(self) -> None:
        await self._load_sources()
        await self._find_or_create_import_message()
        if not self._msg:
            return
        tokens = await self._pull_tokens_from_leina()
        content = _render_import_message(tokens, LEINA_TITLE, LEINA_JSON_KEY)
        try:
            await self._msg.edit(content=content)
        except Exception as e:
            log.error("edit import message failed: %r", e, exc_info=True)

    @tasks.loop(seconds=TICK_SEC)
    async def _tick(self):
        try:
            await self.bot.wait_until_ready()
            await self._update()
        except Exception as e:
            log.error("leina bridge tick error: %r", e, exc_info=True)

    @_tick.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashLeinaBridge(bot))
