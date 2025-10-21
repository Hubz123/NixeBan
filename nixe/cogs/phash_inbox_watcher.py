# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re, json, logging, asyncio
from io import BytesIO
from typing import Optional, List, Set
import discord
from discord.ext import commands, tasks
from nixe.config.self_learning_cfg import (
    LOG_CHANNEL_ID, PHASH_INBOX_THREAD, PHASH_DB_MARKER,
    PHASH_WATCH_FIRST_DELAY, PHASH_WATCH_INTERVAL
)

log = logging.getLogger(__name__)

try:
    from PIL import Image as _PIL_Image
except Exception:
    _PIL_Image = None

try:
    import imagehash as _imagehash
except Exception:
    _imagehash = None

HEX16 = re.compile(r'^[0-9a-f]{16}$', re.I)
BLOCK_RE = re.compile(
    r'(?:^|\n)\s*%s\s*```(?:json)?\s*(\{.*?\})\s*```' % re.escape(PHASH_DB_MARKER),
    re.I | re.S
)

def _compute_phash(raw: bytes) -> Optional[str]:
    if _PIL_Image is None or _imagehash is None:
        return None
    try:
        im = _PIL_Image.open(BytesIO(raw)).convert('RGB')
        return str(_imagehash.phash(im))
    except Exception:
        return None

def _norm_list(obj) -> List[str]:
    out: List[str] = []
    def push(x):
        if isinstance(x, str) and HEX16.match(x.strip()):
            out.append(x.strip())
    if isinstance(obj, dict):
        arr = obj.get('phash') or obj.get('items') or []
        if isinstance(arr, list):
            for it in arr:
                push(it if isinstance(it, str) else (it.get('hash') if isinstance(it, dict) else None))
    elif isinstance(obj, list):
        for it in obj:
            push(it if isinstance(it, str) else (it.get('hash') if isinstance(it, dict) else None))
    seen = set(); uniq: List[str] = []
    for h in out:
        if h not in seen:
            seen.add(h); uniq.append(h)
    return uniq

class NixePhashInboxWatcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.loop = self._loop_collect.start()

    def cog_unload(self):
        try:
            self._loop_collect.cancel()
        except Exception:
            pass

    def _inbox_names(self) -> Set[str]:
        return {n.strip().lower() for n in PHASH_INBOX_THREAD.split(',') if n.strip()}

    async def _get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        if LOG_CHANNEL_ID:
            ch = guild.get_channel(LOG_CHANNEL_ID)
            if isinstance(ch, discord.TextChannel):
                return ch
        for c in guild.text_channels:
            if c.name.lower() in {'log-botphising','log-botphishing','log_botphising','log-phishing'}:
                return c
        return None

    async def _get_inbox_thread(self, ch: discord.TextChannel) -> Optional[discord.Thread]:
        wanted = self._inbox_names()
        for t in list(ch.threads):
            if isinstance(t, discord.Thread) and t.name.lower() in wanted:
                return t
        try:
            async for t in ch.archived_threads(limit=50):
                if isinstance(t, discord.Thread) and t.name.lower() in wanted:
                    return t
        except Exception:
            pass
        return None

    async def _get_own_db_message(self, container: discord.abc.Messageable) -> Optional[discord.Message]:
        try:
            async for msg in container.history(limit=100):
                if not isinstance(msg.content, str):
                    continue
                if PHASH_DB_MARKER in msg.content and BLOCK_RE.search(msg.content):
                    # only accept if authored by this bot
                    if msg.author and self.bot.user and msg.author.id == self.bot.user.id:
                        return msg
        except Exception:
            pass
        return None

    async def _get_any_db_message(self, container: discord.abc.Messageable) -> Optional[discord.Message]:
        try:
            async for msg in container.history(limit=100):
                if isinstance(msg.content, str) and PHASH_DB_MARKER in msg.content and BLOCK_RE.search(msg.content):
                    return msg
        except Exception:
            pass
        return None

    async def _create_db_message(self, container: discord.abc.Messageable, total: int = 0) -> Optional[discord.Message]:
        try:
            content = f"{PHASH_DB_MARKER}\n```json\n{{\"phash\":[]}}\n```"
            return await container.send(content, embed=self._summary_embed(total=total))
        except Exception:
            return None

    async def _get_or_create_db_message(self, container: discord.abc.Messageable) -> Optional[discord.Message]:
        # Prefer our own message; if not exist, create new one (avoid editing others' message)
        own = await self._get_own_db_message(container)
        if own:
            return own
        # if someone else already has a marker, do NOT edit it; create ours
        new_msg = await self._create_db_message(container, total=0)
        if new_msg:
            return new_msg
        # last resort fallback: return any marker (we will not edit it if not ours)
        return await self._get_any_db_message(container)

    def _summary_embed(self, total: int) -> discord.Embed:
        e = discord.Embed(
            title='pHash DB (imagephising)',
            description=f'Total unik: **{total}**\n\n_Disimpan pada pesan ini; selalu di-EDIT (no spam)._',
            color=0x2e8b57
        )
        e.set_footer(text='NIXE • pHash inbox watcher')
        return e

    @tasks.loop(seconds=PHASH_WATCH_INTERVAL)
    async def _loop_collect(self):
        if not self.bot.is_ready():
            return
        guilds = list(self.bot.guilds or [])
        if not guilds:
            return
        guild = guilds[0]
        ch = await self._get_log_channel(guild)
        if not ch:
            return
        thread = await self._get_inbox_thread(ch)
        if not thread:
            return
        db_msg = await self._get_or_create_db_message(ch)
        if not db_msg:
            return

        try:
            m = BLOCK_RE.search(db_msg.content or '')
            current = _norm_list(json.loads(m.group(1)) if m else {'phash': []})
        except Exception:
            current = []

        collected: List[str] = []
        try:
            async for msg in thread.history(limit=400):
                for a in msg.attachments:
                    ctype = (a.content_type or '')
                    ok = ctype.startswith('image/') or str(a.filename).lower().endswith(('.png','.jpg','.jpeg','.webp','.gif','.bmp'))
                    if not ok:
                        continue
                    try:
                        raw = await a.read()
                    except Exception:
                        continue
                    h = _compute_phash(raw)
                    if h:
                        collected.append(h)
        except Exception as e:
            log.warning('[phash-inbox] history error: %s', e)

        seen = set(current)
        merged = current + [h for h in collected if h not in seen]

        # Only edit if the marker is ours; otherwise, create our own and edit that
        try:
            if db_msg.author and self.bot.user and db_msg.author.id != self.bot.user.id:
                # not ours → create our own marker and edit it
                new_msg = await self._create_db_message(ch, total=len(merged))
                if new_msg:
                    db_msg = new_msg
            content = f"{PHASH_DB_MARKER}\n```json\n" + json.dumps({'phash': merged}, ensure_ascii=False) + "\n```"
            await db_msg.edit(content=content, embed=self._summary_embed(total=len(merged)))
        except discord.Forbidden:
            # fallback: create our own marker then edit
            new_msg = await self._create_db_message(ch, total=len(merged))
            if new_msg:
                db_msg = new_msg
                content = f"{PHASH_DB_MARKER}\n```json\n" + json.dumps({'phash': merged}, ensure_ascii=False) + "\n```"
                try:
                    await db_msg.edit(content=content, embed=self._summary_embed(total=len(merged)))
                except Exception as e:
                    log.error('[phash-inbox] edit failed after create: %s', e)
            else:
                log.error('[phash-inbox] failed to create marker message; skipping update')
        except Exception as e:
            log.warning('[phash-inbox] edit failed: %s', e)

    @_loop_collect.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(PHASH_WATCH_FIRST_DELAY)
        log.info('[phash-inbox] started (first=%ss / every=%s)', PHASH_WATCH_FIRST_DELAY, PHASH_WATCH_INTERVAL)


async def setup(bot: commands.Bot):
    await bot.add_cog(NixePhashInboxWatcher(bot))
