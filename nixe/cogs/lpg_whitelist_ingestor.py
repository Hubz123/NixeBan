# nixe/cogs/lpg_whitelist_ingestor.py
from __future__ import annotations
import asyncio, logging, os, json, io, time
from typing import Optional
import discord
from discord.ext import commands
from .lpg_whitelist_thread_manager import LPGWhitelistThreadManager
from nixe.helpers.hash_utils import ahash_hex_from_bytes, dhash_hex_from_bytes, sha256_hex

log = logging.getLogger("nixe.cogs.lpg_whitelist_ingestor")

def _cfg() -> dict:
    path = os.getenv("RUNTIME_ENV_PATH") or "nixe/config/runtime_env.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

NEG_FILE_DEFAULT = "data/lpg_negative_hashes.txt"

def _neg_file(cfg: dict) -> str:
    return os.getenv("LPG_NEG_FILE") or cfg.get("LPG_NEG_FILE") or NEG_FILE_DEFAULT

def _thread_id(cfg: dict) -> int:
    v = os.getenv("LPG_NEG_THREAD_ID") or cfg.get("LPG_NEG_THREAD_ID")
    if v: 
        try: return int(v)
        except: return 0
    return 0

def _ensure_file(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Negative hash whitelist (auto-filled from whitelist thread)\n")

def _append_if_new(path: str, lines: list[str]) -> list[str]:
    added = []
    existing = set()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for ln in f:
                s = ln.strip().lower()
                if not s or s.startswith("#"): continue
                existing.add(s)
    with open(path, "a", encoding="utf-8") as f:
        for ln in lines:
            s = ln.strip().lower()
            if s in existing: 
                continue
            f.write(ln.rstrip()+"\n")
            existing.add(s); added.append(ln.rstrip())
    return added

class LPGWhitelistIngestor(commands.Cog):
    """Listen for images posted to whitelist thread; compute hashes and persist into file."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = _cfg()
        self.neg_file = _neg_file(self.cfg)
        _ensure_file(self.neg_file)
        self.thread_id = _thread_id(self.cfg)
        self._guard_reload_notify = os.getenv("LPG_NEG_TOUCH_FILE") or self.cfg.get("LPG_NEG_TOUCH_FILE") or "data/lpg_neg_reload.touch"

    async def _ingest_bytes(self, b: bytes, meta: str) -> list[str]:
        a = ahash_hex_from_bytes(b, 8)
        d = dhash_hex_from_bytes(b)
        s = sha256_hex(b)
        lines = [
            f"ahash:{a}  # {meta}",
            f"dhash:{d}  # {meta}",
            f"sha256:{s} # {meta}",
        ]
        added = _append_if_new(self.neg_file, lines)
        # touch flag to inform guard (mtime change)
        try:
            os.makedirs(os.path.dirname(self._guard_reload_notify), exist_ok=True)
            with open(self._guard_reload_notify, "w") as f:
                f.write(str(time.time()))
        except Exception:
            pass
        return added

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        try:
            if self.thread_id == 0:
                # Try to fetch from thread manager
                tm = self.bot.get_cog("LPGWhitelistThreadManager")
                if tm and tm.thread_id:
                    self.thread_id = tm.thread_id
            if self.thread_id and message.channel.id != self.thread_id:
                return
            if not message.attachments:
                return
            img = None
            for a in message.attachments:
                if (getattr(a, "content_type", "") or "").startswith("image/"):
                    img = await a.read()
                    break
            if not img:
                return
            label = f"discord:{message.id}@{message.channel.id} by {message.author.id}"
            added = await self._ingest_bytes(img, label)
            if added:
                note = await message.reply(f"✅ Ditambahkan ke whitelist ({len(added)} baris).")
                await asyncio.sleep(10)
                await note.delete()
        except Exception:
            log.exception("[lpg-wl] ingest failed")

async def setup(bot: commands.Bot):
    await bot.add_cog(LPGWhitelistIngestor(bot))
