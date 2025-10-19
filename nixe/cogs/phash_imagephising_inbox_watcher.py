# -*- coding: utf-8 -*-
# phash_imagephising_inbox_watcher.py
#
# Tujuan:
# - Pantau channel LOG (log-botphising) dan ambil thread bernama "imagephising" (atau via ENV PHASH_INBOX_THREAD)
# - Kumpulkan semua gambar di thread tsb, hitung pHash, dan simpan ke satu pesan (MARKER) yg sama
# - Edit pesan/embeds (bukan kirim pesan baru) -> menghindari spam
# - Aman untuk smoke_cogs.py: tidak ada side-effect di import; loop start di cog_load/before_loop
#
# ENV/Config yang digunakan:
#   PHASH_DB_MARKER           (default: SATPAMBOT_PHASH_DB_V1)
#   PHASH_INBOX_THREAD        (default: "imagephising,imagelogphising,image-phising,image_phising,image-phishing,image_phishing")
#   PHASH_WATCH_FIRST_DELAY   (detik; default: 60)
#   PHASH_WATCH_INTERVAL      (detik; default: 600)
#
#   LOG_CHANNEL_ID            (diambil dari self_learning_cfg.LOG_CHANNEL_ID)
#
from __future__ import annotations

import os, io, re, json, asyncio, logging
from typing import Optional, List, Tuple, Dict, Set
from io import BytesIO

import discord
from discord.ext import commands, tasks

# Optional deps for pHash
try:
    from PIL import Image as _PIL_Image
except Exception:
    _PIL_Image = None

try:
    import imagehash as _imagehash
except Exception:
    _imagehash = None

log = logging.getLogger(__name__)

# Marker & thread names
MARKER = os.getenv("PHASH_DB_MARKER", "SATPAMBOT_PHASH_DB_V1").strip()
_DEFAULT_INBOX = "imagephising,imagelogphising,image-phising,image_phising,image-phishing,image_phishing"
INBOX_NAMES = [n.strip() for n in os.getenv("PHASH_INBOX_THREAD", _DEFAULT_INBOX).split(",") if n.strip()]
HEX16 = re.compile(r"^[0-9a-f]{16}$", re.I)
BLOCK_RE = re.compile(r"(?:^|\n)\s*%s\s*```(?:json)?\s*(\{.*?\})\s*```" % re.escape(MARKER), re.I | re.S)

def _norm_hashes(obj):
    out: List[str] = []
    def push(x):
        if isinstance(x, str) and HEX16.match(x.strip()):
            out.append(x.strip())
    if isinstance(obj, dict):
        if isinstance(obj.get("phash"), list):
            for h in obj["phash"]:
                push(h)
        if isinstance(obj.get("items"), list):
            for it in obj["items"]:
                if isinstance(it, dict):
                    push(it.get("hash"))
                else:
                    push(it)
    elif isinstance(obj, list):
        for it in obj:
            if isinstance(it, dict):
                push(it.get("hash"))
            else:
                push(it)
    # unique preserve order
    seen: Set[str] = set()
    uniq: List[str] = []
    for h in out:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    return uniq

def _compute_phash(raw: bytes) -> Optional[str]:
    if _PIL_Image is None or _imagehash is None:
        return None
    try:
        im = _PIL_Image.open(BytesIO(raw)).convert("RGB")
        return str(_imagehash.phash(im))
    except Exception:
        return None

async def _get_or_create_db_message(container: discord.abc.Messageable) -> Optional[discord.Message]:
    """Cari pesan dengan MARKER; jika tidak ketemu, buat baru."""
    try:
        async for msg in container.history(limit=100):
            try:
                if isinstance(msg.content, str) and MARKER in msg.content:
                    if BLOCK_RE.search(msg.content):
                        return msg
            except Exception:
                continue
    except Exception:
        pass
    # create baru
    try:
        payload = {"phash": []}
        content = f"{MARKER}\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
        return await container.send(content)
    except Exception:
        return None

def _ensure_embed_summary(msg: discord.Message, total: int) -> Optional[discord.Embed]:
    """Siapkan embed ringkas untuk menghindari spam; hanya diedit."""
    e = discord.Embed(
        title="pHash DB (imagephising)",
        description=f"Total unik: **{total}**\n\n_Entry disimpan pada pesan ini; akan selalu di-EDIT, bukan spam._",
        color=0x2e8b57,
    )
    e.set_footer(text="SatpamBot • pHash inbox watcher")
    return e

class PhashImagephisingInboxWatcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.loop = self._loop_collect.start()

    def cog_unload(self):
        try:
            self._loop_collect.cancel()
        except Exception:
            pass

    @tasks.loop(seconds=int(os.getenv("PHASH_WATCH_INTERVAL", "600")))
    async def _loop_collect(self):
        # Cari channel log
        try:
            from satpambot.bot.modules.discord_bot.config.self_learning_cfg import LOG_CHANNEL_ID
        except Exception:
            LOG_CHANNEL_ID = 0

        if not self.bot.is_ready():
            return
        guilds = list(self.bot.guilds or [])
        if not guilds:
            return
        guild = guilds[0]

        ch = None
        if LOG_CHANNEL_ID:
            try:
                ch = self.bot.get_channel(LOG_CHANNEL_ID) or await self.bot.fetch_channel(LOG_CHANNEL_ID)
            except Exception as e:
                log.warning("[phash_inbox] cannot fetch LOG_CHANNEL_ID=%s: %s", LOG_CHANNEL_ID, e)
        # fallback: cari berdasarkan nama yg mirip
        if not ch:
            for c in guild.text_channels:
                if c.name.lower() in ("log-botphising", "log-phishing", "log_botphising", "log-botphishing"):
                    ch = c; break
        if not ch or not isinstance(ch, discord.TextChannel):
            return

        # Cari thread target (by names list)
        target_thread: Optional[discord.Thread] = None
        # cek thread aktif dan archived (panggil API jika perlu)
        for t in list(ch.threads):
            if isinstance(t, discord.Thread) and t.name.lower() in {n.lower() for n in INBOX_NAMES}:
                target_thread = t; break
        if not target_thread:
            try:
                async for t in ch.archived_threads(limit=50):
                    if isinstance(t, discord.Thread) and t.name.lower() in {n.lower() for n in INBOX_NAMES}:
                        target_thread = t; break
            except Exception:
                pass
        if not target_thread:
            return

        # Ambil pesan DB (disimpan di parent channel supaya gampang diakses)
        db_msg = await _get_or_create_db_message(ch)
        if not db_msg:
            return

        # Baca DB saat ini
        try:
            m = BLOCK_RE.search(db_msg.content or "")
            current = _norm_hashes(json.loads(m.group(1)) if m else {"phash": []})
        except Exception:
            current = []

        # Kumpulkan pHash dari semua image di thread
        collected: List[str] = []
        try:
            async for msg in target_thread.history(limit=400):
                # Ambil attachment gambar saja
                for a in msg.attachments:
                    try:
                        if not (a.content_type or "").startswith("image/"):
                            continue
                    except Exception:
                        # fallback: cek nama
                        ok = str(a.filename).lower().endswith((".png",".jpg",".jpeg",".webp",".gif",".bmp"))
                        if not ok: continue
                    try:
                        raw = await a.read()
                    except Exception:
                        continue
                    h = _compute_phash(raw)
                    if h and HEX16.match(h):
                        collected.append(h)
        except Exception as e:
            log.warning("[phash_inbox] history error: %s", e)

        # Merge & dedup
        seen = set(current)
        merged = current + [h for h in collected if h not in seen]
        if merged != current:
            content = f"{MARKER}\n```json\n{json.dumps({'phash': merged}, ensure_ascii=False)}\n```"
            try:
                await db_msg.edit(content=content, embed=_ensure_embed_summary(db_msg, len(merged)))
                log.info("[phash_inbox] updated: +%s (total=%s)", len(merged)-len(current), len(merged))
            except Exception as e:
                log.warning("[phash_inbox] failed to edit db msg: %s", e)
        else:
            # tetap refresh embed (update TS) tanpa ubah konten
            try:
                await db_msg.edit(embed=_ensure_embed_summary(db_msg, len(current)))
            except Exception:
                pass

    @_loop_collect.before_loop
    async def _before_loop_collect(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(int(os.getenv("PHASH_WATCH_FIRST_DELAY", "60")))
        log.info("[phash_inbox] started (first_delay=%ss, every=%ss) inbox=%s",
                 os.getenv("PHASH_WATCH_FIRST_DELAY","60"),
                 os.getenv("PHASH_WATCH_INTERVAL","600"),
                 ",".join(INBOX_NAMES))

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashImagephisingInboxWatcher(bot))
