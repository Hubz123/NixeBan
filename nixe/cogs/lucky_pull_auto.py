from __future__ import annotations
import os, re, logging
from typing import Set
from io import BytesIO
try:
    from PIL import Image, ImageFilter, ImageOps
except Exception:
    Image = None; ImageFilter = None; ImageOps = None
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

class LuckyPullAuto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.strict = (os.getenv("LUCKYPULL_STRICT_MODE", "1") == "1")
        self.allow_channels = _ids("LUCKYPULL_ALLOW_CHANNELS")
        self.guard_channels = _ids("LUCKYPULL_GUARD_CHANNELS")
        self.redirect_chan = int(os.getenv("LUCKYPULL_REDIRECT_CHANNEL_ID", "0") or 0)
        self.notice_ttl = int(os.getenv("LUCKYPULL_NOTICE_TTL", "20") or 20)
        self.notice_mention = (os.getenv("LUCKYPULL_MENTION", "1") == "1")
        self._last_notice = {}  # user_id -> ts
        self.image_heur = (os.getenv("LUCKYPULL_IMAGE_HEURISTICS","1")=="1")
        self.grid_min_v = int(os.getenv("LUCKYPULL_GRID_MIN_VLINES","3") or 3)
        self.grid_min_h = int(os.getenv("LUCKYPULL_GRID_MIN_HLINES","2") or 2)
        self.grid_max_v = int(os.getenv("LUCKYPULL_GRID_MAX_VLINES","20") or 20)
        self.grid_max_h = int(os.getenv("LUCKYPULL_GRID_MAX_HLINES","10") or 10)
        self._pat = re.compile(r"(?ix)(lucky\s*pull|wish|gacha|pull\s*\d+x|\d+x\s*pull|banner\s*result|hasil\s*pull|convene|warp)")

    def _target(self, ch_id: int) -> bool:
        if ch_id in self.allow_channels: return False
        return (ch_id in self.guard_channels) if self.guard_channels else True

    def _looks(self, m: discord.Message) -> bool:
        if not self.strict: return False
        for a in m.attachments:
            if self._pat.search((a.filename or "").lower()): return True
        return bool(m.content and self._pat.search(m.content.lower()))

    
def _looks_image(self, raw: bytes) -> bool:
    if not Image or not ImageFilter:
        return False
    try:
        im = Image.open(BytesIO(raw)).convert("L")
        im = im.resize((256, 256))
        ed = ImageOps.autocontrast(im.filter(ImageFilter.FIND_EDGES))
        w, h = ed.size; px = ed.load()
        col = [0]*w; row = [0]*h
        for y in range(h):
            s=0
            for x in range(w): s += px[x,y]
            row[y]=s
        for x in range(w):
            s=0
            for y in range(h): s += px[x,y]
            col[x]=s
        rmax = max(row) or 1; cmax = max(col) or 1
        row=[r/rmax for r in row]; col=[c/cmax for c in col]
        def smooth(arr):
            out=[]; n=len(arr)
            for i in range(n):
                s=0; c=0
                for k in range(-2,3):
                    j=i+k
                    if 0<=j<n: s+=arr[j]; c+=1
                out.append(s/max(1,c))
            return out
        row_s=smooth(row); col_s=smooth(col)
        def count_peaks(arr, thr):
            count=0; on=False
            for v in arr:
                if not on and v>=thr: on=True; count+=1
                elif on and v<thr*0.8: on=False
            return count
        vh = count_peaks(row_s, 0.6)
        vv = count_peaks(col_s, 0.6)
        return (self.grid_min_v <= vv <= self.grid_max_v) and (self.grid_min_h <= vh <= self.grid_max_h)
    except Exception:
        return False

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if m.author.bot: return
        ch = m.channel
        if not isinstance(ch, (discord.TextChannel, discord.Thread)): return
        if not self._target(ch.id): return
        looks = self._looks(m)
        if not looks and self.image_heur and m.attachments:
            for a in m.attachments:
                try:
                    raw = await a.read()
                except Exception:
                    raw = None
                if raw and self._looks_image(raw):
                    looks = True; break
        if not looks: return
        try: mark_skip_phash(m.id)
        except Exception: pass
        try:
            await m.delete(reason="Lucky Pull in non-allowed channel")
            try:
                target_id = self.redirect_chan or (next(iter(self.allow_channels)) if self.allow_channels else 0)
                target_mention = f"<#{target_id}>" if target_id else "channel yang ditentukan"
                uid = getattr(m.author, 'id', 0)
                import time
                now = time.time()
                if uid and self._last_notice.get(uid, 0) + 45 > now:
                    pass
                else:
                    self._last_notice[uid] = now
                    content = (f"{m.author.mention} gambar Lucky Pull tidak boleh di sini. Silakan pindah ke {target_mention} ya.") if self.notice_mention else (
                               f"Gambar Lucky Pull tidak boleh di sini. Silakan pindah ke {target_mention} ya.")
                    try:
                        from discord import AllowedMentions
                        am = AllowedMentions(everyone=False, users=self.notice_mention, roles=False)
                    except Exception:
                        am = None
                    msg = await ch.send(content, allowed_mentions=am)
                    if self.notice_ttl > 0:
                        try:
                            import asyncio
                            await asyncio.sleep(self.notice_ttl)
                            await msg.delete()
                        except Exception:
                            pass
            except Exception:
                log.debug('[lucky_pull_auto] notify failed', exc_info=True)
            log.info("[lucky_pull_auto] deleted in #%s (%s)", getattr(ch, "name", "?"), ch.id)
        except Exception: log.debug("[lucky_pull_auto] delete failed", exc_info=True)

async def setup(bot: commands.Bot):
    # Avoid duplicate registration if loader already added this cog
    if 'LuckyPullAuto' in getattr(bot, 'cogs', {}):
        return
    try:
        await bot.add_cog(LuckyPullAuto(bot))
    except Exception:
        # If already loaded or another race, swallow to keep startup healthy
        import logging; logging.getLogger(__name__).debug("setup: LuckyPullAuto already loaded or failed softly", exc_info=True)
