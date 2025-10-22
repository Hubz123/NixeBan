from __future__ import annotations
import os, re, asyncio, logging, time
from typing import Optional, Set, List, Iterable, Union

import discord
from discord.ext import commands, tasks

log = logging.getLogger("nixe.cogs.phash_db_board")

# ===== Defaults (baked-in) =====
DB_THREAD_ID = int(os.getenv("PHASH_DB_THREAD_ID", "1430048839556927589"))
# Sumber PIN (bisa Thread atau Channel) — default ke log-botphising:
PIN_SOURCE_ID = int(os.getenv("PHASH_PIN_SOURCE_ID", os.getenv("PHASH_PIN_SOURCE_THREAD_ID", "1400375184048787566")))
SOURCE_THREAD_ID = int(os.getenv("PHASH_SOURCE_THREAD_ID", "1409949797313679492"))  # imagephish (fallback)
SOURCE_CHANNEL_ID = int(os.getenv("PHASH_SOURCE_CHANNEL_ID", "0"))

TITLE = os.getenv("PHASH_DB_TITLE", "SATPAMBOT_PHASH_DB_V1")
JSON_KEY = os.getenv("PHASH_JSON_KEY", "phash")
BOARD_TAG = os.getenv("PHASH_DB_BOARD_MARKER", "[phash-db-board]")
SCAN_LIMIT = int(os.getenv("PHASH_DB_SCAN_LIMIT", "12000"))
MAX_BYTES = int(os.getenv("PHASH_DB_MAX_BYTES", "1800"))
EDIT_MIN_INTERVAL = int(os.getenv("PHASH_BOARD_EDIT_MIN_INTERVAL", "20"))

HEX16 = re.compile(r"\b[0-9a-f]{16}\b")

def _is_board_message(msg: discord.Message) -> bool:
    c = (msg.content or "")
    return (TITLE in c) or (BOARD_TAG in c)

def _collect_tokens(texts: Iterable[str], out: Set[str]) -> None:
    for text in texts:
        if not text:
            continue
        for tok in HEX16.findall(text.lower()):
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
            trial_lines = [f"\"{t}\"," for t in tokens[:max(mid-1,0)]]
            if mid > 0:
                trial_lines += [f"\"{tokens[mid-1]}\""]
            trial = head + "\n".join(trial_lines) + tail
            if len(trial) <= MAX_BYTES:
                best = mid; lo = mid + 1
            else:
                hi = mid - 1
        use = tokens[:best]
        body = [f"\"{t}\"," for t in use]
        if body: body[-1] = body[-1].rstrip(",")
        content = head + "\n".join(body) + tail
    return content

async def _read_pinned_json(chan: Union[discord.Thread, discord.TextChannel]) -> List[str]:
    """Parse all pinned messages in `chan` and extract 16-hex tokens."""
    try:
        pins = await chan.pins()
    except Exception:
        pins = []
    tokens: Set[str] = set()
    _collect_tokens((p.content or "" for p in pins), tokens)
    return list(tokens)

class PhashDbBoard(commands.Cog):
    """Pinned JSON pHash list ala Leina; baca dari PIN channel/thread sumber; edit hanya saat berubah."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._db: Optional[discord.Thread] = None
        self._pin_src: Optional[Union[discord.Thread, discord.TextChannel]] = None
        self._src_th: Optional[discord.Thread] = None
        self._src_ch: Optional[discord.TextChannel] = None
        self._msg: Optional[discord.Message] = None
        self._last_tokens: List[str] = []
        self._last_edit_ts: float = 0.0
        self._update_lock = asyncio.Lock()
        self._tick.start()

    def cog_unload(self):
        self._tick.cancel()

    async def _load_threads(self) -> None:
        if DB_THREAD_ID and self._db is None:
            ch = await self.bot.fetch_channel(DB_THREAD_ID)
            if isinstance(ch, discord.Thread):
                self._db = ch
                await _ensure_unarchived(ch)
        if PIN_SOURCE_ID and self._pin_src is None:
            ch = await self.bot.fetch_channel(PIN_SOURCE_ID)
            if isinstance(ch, (discord.Thread, discord.TextChannel)):
                self._pin_src = ch
                if isinstance(ch, discord.Thread):
                    await _ensure_unarchived(ch)
        if SOURCE_THREAD_ID and self._src_th is None and SOURCE_THREAD_ID != PIN_SOURCE_ID:
            try:
                th = await self.bot.fetch_channel(SOURCE_THREAD_ID)
                if isinstance(th, discord.Thread):
                    self._src_th = th
                    await _ensure_unarchived(th)
            except Exception:
                pass
        if SOURCE_CHANNEL_ID and self._src_ch is None and SOURCE_CHANNEL_ID != PIN_SOURCE_ID:
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
        # 1) Pinned JSON from channel/thread sumber
        if self._pin_src:
            pinned_tokens = await _read_pinned_json(self._pin_src)
            tokens.update(pinned_tokens)

        # 2) Fallback: free-text tokens dari DB/SOURCE
        async def texts_from(src):
            async for msg in src.history(limit=None if not isinstance(src, discord.TextChannel) else 500, oldest_first=True):
                yield (msg.content or "")

        for src in (self._db, self._src_th, self._src_ch):
            if not src: continue
            buf: List[str] = []
            async for t in texts_from(src):
                buf.append(t)
            _collect_tokens(buf, tokens)

        # Order stabil: berdasarkan kemunculan pertama di pin_src → db → lainnya
        order: List[str] = []
        seen: Set[str] = set()

        async def append_in_order(src):
            if not src: return
            async for msg in src.history(limit=None if not isinstance(src, discord.TextChannel) else 500, oldest_first=True):
                for tok in HEX16.findall((msg.content or "").lower()):
                    if tok in tokens and tok not in seen:
                        seen.add(tok); order.append(tok)

        for src in (self._pin_src, self._db, self._src_th, self._src_ch):
            await append_in_order(src)

        return order[:SCAN_LIMIT]

    async def _update_board(self, force: bool = False) -> None:
        async with self._update_lock:
            await self._load_threads()
            await self._find_or_create_board()
            if not self._msg:
                return

            now = time.time()
            if not force and now - self._last_edit_ts < EDIT_MIN_INTERVAL:
                return  # throttle edits

            toks = await self._gather_tokens()
            if not force and toks == self._last_tokens:
                return  # nothing changed

            content = _render_json(toks) + f"\n{BOARD_TAG}"
            if self._msg.content == content and not force:
                self._last_tokens = toks
                self._last_edit_ts = now
                return

            try:
                await self._msg.edit(content=content)
                self._last_tokens = toks
                self._last_edit_ts = now
                log.info("[phash-db-board] updated with %d tokens", len(toks))
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
        # Refresh bila ada pesan baru di DB / PIN source
        watch_ids = {DB_THREAD_ID, PIN_SOURCE_ID}
        if message.channel.id in watch_ids:
            asyncio.create_task(self._update_board())

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashDbBoard(bot))
