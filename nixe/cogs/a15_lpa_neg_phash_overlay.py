
# -*- coding: utf-8 -*-
"""
a15_lpa_neg_phash_overlay
Safelist untuk menurunkan false positive Lucky Pull:
- Cek pHash gambar terhadap daftar "NEGATIVE" (UI/layar bukan gacha).
- Jika match >= LPG_NEG_MATCH_THRESHOLD => paksa benign, skip delete/mention.

ENV:
- LPG_NEG_PHASHES             : "hash1,hash2,..."
- LPG_NEG_MATCH_THRESHOLD     : default 0.93
Integrasi:
- Overlay ini hook ke event on_message, dan hanya bertindak jika
  extension lucky_pull_auto aktif. Ia menandai message lewat cache agar
  lucky_pull_auto melewati tindakan delete.
"""
from __future__ import annotations
import os, logging, asyncio
import discord
from discord.ext import commands

log = logging.getLogger("nixe.cogs.a15_lpa_neg_phash_overlay")

def _parse_hashes(s: str | None) -> set[str]:
    if not s: return set()
    return {h.strip().lower() for h in s.split(",") if h.strip()}

def _parse_float(s: str | None, default: float) -> float:
    try:
        return float(s)
    except Exception:
        return default

# Hamming distance on hex pHash
def _ham_dist_hex(a: str, b: str) -> int:
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except Exception:
        return 256  # far

def _similarity_hex(a: str, b: str) -> float:
    # 64-bit phash -> max bits = 64
    d = _ham_dist_hex(a, b)
    return 1.0 - (d / 64.0)

class LpaNegPhashOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.neg = _parse_hashes(os.getenv("LPG_NEG_PHASHES", ""))
        self.thr = _parse_float(os.getenv("LPG_NEG_MATCH_THRESHOLD"), 0.93)
        # cache message ids to skip by other cogs
        self.skip = set()
        if self.neg:
            log.warning("[lpa-neg] active: %d negative phash(es), thr=%.2f", len(self.neg), self.thr)
        else:
            log.info("[lpa-neg] no negative phash set")

    @commands.Cog.listener("on_message")
    async def _on_message(self, message: discord.Message):
        try:
            if message.author.bot or not message.attachments:
                return
            # Only act in channels guarded by lucky pull (optional speed-up)
            # If you want strict scope, set LPG_GUARD_CHANNELS and check here.
            # Compute phash using existing helper if available
            pfunc = None
            try:
                from nixe.helpers.phash_board import phash_hex_from_bytes as pfunc  # type: ignore
            except Exception:
                pass
            if not pfunc:
                return
            # evaluate each image
            for att in message.attachments:
                if not (att.content_type and att.content_type.startswith("image/")):
                    continue
                data = await att.read()
                try:
                    h = pfunc(data)
                except Exception:
                    continue
                for neg in self.neg:
                    sim = _similarity_hex(h, neg)
                    if sim >= self.thr:
                        self.skip.add(message.id)
                        log.warning("[lpa-neg] safelisted msg=%s sim=%.3f hash=%s neg=%s", message.id, sim, h, neg)
                        return
        except Exception as e:
            log.debug("[lpa-neg] error: %r", e)

    @commands.Cog.listener("on_message_delete")
    async def _on_del(self, msg: discord.Message):
        # cleanup cache best effort
        self.skip.discard(getattr(msg, "id", None))

    # helper untuk dicek dari lucky_pull_auto (opsional)
    def should_skip(self, message_id: int) -> bool:
        return message_id in self.skip

async def setup(bot):
    await bot.add_cog(LpaNegPhashOverlay(bot))
