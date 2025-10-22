
from __future__ import annotations
import os, re, asyncio, logging
from typing import Optional, Set, List

import discord
from discord.ext import commands, tasks

log = logging.getLogger("nixe.cogs.phash_db_board")

# Defaults using user's IDs
DB_THREAD_ID = int(os.getenv("PHASH_DB_THREAD_ID", "1430048839556927589"))   # Nixe DB thread
SOURCE_THREAD_ID = int(os.getenv("PHASH_SOURCE_THREAD_ID", os.getenv("PHASH_IMPORT_SOURCE_THREAD_ID", "1409949797313679492")))  # Source/imagephish
SOURCE_CHANNEL_ID = int(os.getenv("PHASH_SOURCE_CHANNEL_ID", "0"))
TITLE = os.getenv("PHASH_DB_TITLE", "SATPAMBOT_PHASH_DB_V1")
JSON_KEY = os.getenv("PHASH_JSON_KEY", "phash")
BOARD_TAG = os.getenv("PHASH_DB_BOARD_MARKER", "[phash-db-board]")
SCAN_LIMIT = int(os.getenv("PHASH_DB_SCAN_LIMIT", "12000"))
MAX_BYTES = int(os.getenv("PHASH_DB_MAX_BYTES", "1800"))

HEX16 = re.compile(r"\b[0-9a-f]{16}\b")

def _is_board_message(msg: discord.Message) -> bool:
    c = (msg.content or "")
    return (TITLE in c) or (BOARD_TAG in c)

def _collect_tokens_from_text(text: str, out: Set[str]) -> None:
    for tok in HEX16.findall((text or "").lower()):
        out.add(tok)

async def _ensure_unarchived(th: discord.Thread) -> None:
    try:
        if getattr(th, "archived", False):
            await th.edit(archived=False)
    except Exception:
        pass

def _render_json(tokens: List[str]) -> str:
    head = f"{TITLE}\n\n```json\n{{\n\"{JSON_KEY}\": [\n"
    body_lines = [f"\"{t}\"," for t in tokens]
    if body_lines:
        body_lines[-1] = body_lines[-1].rstrip(",")
    tail = "\n]\n}\n```"
    content = head + "\n".join(body_lines) + tail
    if len(content) > MAX_BYTES:
        lo, hi, best = 0, len(tokens), 0
        while lo <= hi:
            mid = (lo + hi) // 2
            trial = head
            if mid > 0:
                trial += "\n".join([f"\"{t}\"," for t in tokens[:mid-1]] + [f"\"{tokens[mid-1]}\""])
            trial += tail
            if len(trial) <= MAX_BYTES:
                best = mid; lo = mid + 1
            else:
                hi = mid - 1
        use = tokens[:best]
        body = [f"\"{t}\"," for t in use]
        if body: body[-1] = body[-1].rstrip(",")
        content = head + "\n".join(body) + tail
    return content

class PhashDbBoard(commands.Cog):
    """Pinned JSON pHash list ala Leina; auto-update membaca DB + optional sumber Leina."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._db: Optional[discord.Thread] = None
        self._msg: Optional[discord.Message] = None
        self._src_th: Optional[discord.Thread] = None
        self._src_ch: Optional[discord.TextChannel] = None
        self._tick.start()

    def cog_unload(self):
        self._tick.cancel()

    async def _load_threads(self) -> None:
        if DB_THREAD_ID and self._db is None:
            ch = await self.bot.fetch_channel(DB_THREAD_ID)
            if isinstance(ch, discord.Thread):
                self._db = ch
                await _ensure_unarchived(ch)
            else:
                log.error("PHASH_DB_THREAD_ID=%s is not a thread", DB_THREAD_ID)
        if SOURCE_THREAD_ID and self._src_th is None:
            try:
                th = await self.bot.fetch_channel(SOURCE_THREAD_ID)
                if isinstance(th, discord.Thread):
                    self._src_th = th
                    await _ensure_unarchived(th)
            except Exception:
                pass
        if SOURCE_CHANNEL_ID and self._src_ch is None:
            try:
                ch = await self.bot.fetch_channel(SOURCE_CHANNEL_ID)
                if isinstance(ch, discord.TextChannel):
                    self._src_ch = ch
            except Exception:
                pass

    async def _find_or_create_board(self) -> None:
        if not self._db:
            return
        try:
            pins = await self._db.pins()
        except Exception:
            pins = []
        for p in pins:
            if _is_board_message(p):
                self._msg = p; return
        async for m in self._db.history(limit=300, oldest_first=False):
            if _is_board_message(m):
                self._msg = m
                try: await m.pin(reason="Pin pHash JSON board")
                except Exception: pass
                return
        placeholder = f"{TITLE}\n\n```json\n{{\"{JSON_KEY}\": []}}\n```"
        created = await self._db.send(content=placeholder + f"\n{BOARD_TAG}")
        try: await created.pin(reason="Pin pHash JSON board")
        except Exception: pass
        self._msg = created

    async def _gather_tokens(self) -> List[str]:
        tokens: Set[str] = set()
        if self._db:
            async for msg in self._db.history(limit=None, oldest_first=True):
                _collect_tokens_from_text(msg.content, tokens)
        if self._src_th:
            async for msg in self._src_th.history(limit=None, oldest_first=True):
                _collect_tokens_from_text(msg.content, tokens)
        if self._src_ch:
            async for msg in self._src_ch.history(limit=500, oldest_first=False):
                _collect_tokens_from_text(msg.content, tokens)
        order: List[str] = []
        seen: Set[str] = set()
        for src in (self._db, self._src_th, self._src_ch):
            if not src: continue
            async for msg in src.history(limit=None if src is not self._src_ch else 500, oldest_first=True):
                for tok in HEX16.findall((msg.content or "").lower()):
                    if tok in tokens and tok not in seen:
                        seen.add(tok); order.append(tok)
        return order[:SCAN_LIMIT]

    async def _update_board(self) -> None:
        await self._load_threads()
        await self._find_or_create_board()
        if not self._msg: return
        toks = await self._gather_tokens()
        content = _render_json(toks) + f"\n{BOARD_TAG}"
        try:
            await self._msg.edit(content=content)
        except Exception as e:
            log.error("edit board failed: %r", e, exc_info=True)

    @tasks.loop(seconds=300)
    async def _tick(self):
        try:
            await self.bot.wait_until_ready()
            await self._update_board()
        except Exception as e:
            log.error("board tick error: %r", e, exc_info=True)

    @_tick.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self._db and message.channel.id == self._db.id:
            asyncio.create_task(self._update_board())

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashDbBoard(bot))
