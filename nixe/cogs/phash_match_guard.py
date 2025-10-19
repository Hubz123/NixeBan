# nixe/cogs/phash_match_guard.py
from __future__ import annotations
import os, re, json, logging
from io import BytesIO
from typing import Optional, List, Set
import discord
from discord.ext import commands

from ..config.self_learning_cfg import (
    LOG_CHANNEL_ID, PHASH_INBOX_THREAD, PHASH_AUTOBAN_ENABLED,
    PHASH_HAMMING_MAX, BAN_DRY_RUN, BAN_DELETE_SECONDS
)
from .ban_embed import build_ban_embed
from ..helpers.banlog import get_ban_log_channel

log = logging.getLogger(__name__)

try:
    from PIL import Image as _PIL_Image
except Exception:
    _PIL_Image = None

try:
    import imagehash as _imagehash
except Exception:
    _imagehash = None

HEX16 = re.compile(r"^[0-9a-f]{16}$", re.I)

def _inbox_names() -> Set[str]:
    return {n.strip().lower() for n in PHASH_INBOX_THREAD.split(",") if n.strip()}

def _hamm(a: str, b: str) -> int:
    return sum(1 for x, y in zip(a, b) if x != y)

def _compute_phash(raw: bytes) -> Optional[str]:
    if _PIL_Image is None or _imagehash is None:
        return None
    try:
        im = _PIL_Image.open(BytesIO(raw)).convert("RGB")
        return str(_imagehash.phash(im))
    except Exception:
        return None

def _extract_db_hashes_from_content(content: str) -> List[str]:
    m = re.search(r"```json\\s*(\\{.*?\\})\\s*```", content or "", re.I | re.S)
    if not m:
        return []
    try:
        obj = json.loads(m.group(1))
        arr = obj.get("phash") or obj.get("items") or []
        out = []
        for it in arr:
            if isinstance(it, str) and HEX16.match(it): out.append(it)
            elif isinstance(it, dict):
                h = it.get("hash")
                if isinstance(h, str) and HEX16.match(h): out.append(h)
        return out
    except Exception:
        return []

class NixePhashMatchGuard(commands.Cog):
    """Default: only Test Ban embed on match (no autoban) to avoid false positives."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _is_inbox(self, thread: discord.Thread) -> bool:
        return thread and isinstance(thread, discord.Thread) and thread.name.lower() in _inbox_names()

    async def _load_db_hashes(self, guild: discord.Guild) -> List[str]:
        # Find the marker JSON message in parent log channel
        ch = None
        if LOG_CHANNEL_ID:
            ch = guild.get_channel(LOG_CHANNEL_ID)
        if not isinstance(ch, discord.TextChannel):
            for c in guild.text_channels:
                if c.name.lower() in {"log-botphising","log-botphishing","log_botphising","log-phishing"}:
                    ch = c; break
        if not isinstance(ch, discord.TextChannel):
            return []
        async for m in ch.history(limit=100):
            if "```json" in (m.content or ""):
                hashes = _extract_db_hashes_from_content(m.content or "")
                if hashes:
                    return hashes
        return []

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message or message.author.bot:
            return
        if not isinstance(message.channel, discord.Thread):
            return
        thread = message.channel
        if not self._is_inbox(thread):
            return

        imgs = [a for a in message.attachments if (a.content_type or "").startswith("image/")
                or str(a.filename).lower().endswith((".png",".jpg",".jpeg",".webp",".gif",".bmp"))]
        if not imgs:
            return

        h = None
        try:
            raw = await imgs[0].read()
            h = _compute_phash(raw)
        except Exception:
            return
        if not (h and HEX16.match(h)):
            return

        db_hashes = await self._load_db_hashes(message.guild)
        if not db_hashes:
            return

        matched = False
        if PHASH_HAMMING_MAX <= 0:
            matched = h in db_hashes
        else:
            for dh in db_hashes:
                if len(dh) == len(h) and sum(1 for x,y in zip(h,dh) if x!=y) <= PHASH_HAMMING_MAX:
                    matched = True; break

        if not matched:
            return

        logch = get_ban_log_channel(message.guild)
        if not logch:
            return

        moderator = message.guild.me  # bot as actor
        e = build_ban_embed(simulate=True, actor=moderator, target=message.author, reason="Match pHash di imagephising", phash=h)
        await logch.send(embed=e, allowed_mentions=discord.AllowedMentions.none())
        # Autoban remains OFF unless enabled by ENV (not implemented here to keep safe)
