
# -*- coding: utf-8 -*-
from __future__ import annotations

import os, re, time, logging, asyncio
from io import BytesIO
from typing import Optional, List

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

# Optional PIL heuristic (grid detector)
try:
    from PIL import Image, ImageFilter, ImageOps
except Exception:
    Image = ImageFilter = ImageOps = None

IMAGE_EXTS = (".png",".jpg",".jpeg",".webp",".gif",".bmp",".tif",".tiff",".heic",".heif")

def _csv_ids(v: str) -> List[int]:
    out: List[int] = []
    for p in (v or "").split(","):
        p = p.strip()
        if not p: 
            continue
        try: out.append(int(p))
        except Exception: pass
    return out

# Import Gemini helper (2.5 defaults)
try:
    from nixe.cogs._lp_gemini_helper import gemini_judge_images, DEFAULT_GEMINI_MODEL, GEMINI_MIN_CONF
except Exception:  # fallback import style
    from ._lp_gemini_helper import gemini_judge_images, DEFAULT_GEMINI_MODEL, GEMINI_MIN_CONF

class LuckyPullAuto(commands.Cog):
    """Auto-moderasi gambar Lucky Pull (gacha) dengan heuristik + Gemini 2.5 (opsional)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # channels
        self.allow_channels = _csv_ids(os.getenv("LUCKYPULL_ALLOW_CHANNELS",""))
        self.guard_channels = _csv_ids(os.getenv("LUCKYPULL_GUARD_CHANNELS",""))  # empty => global guard
        self.redirect_channel_id = int(os.getenv("LUCKYPULL_REDIRECT_CHANNEL_ID","0") or 0)

        # behavior
        self.mention = (os.getenv("LUCKYPULL_MENTION","1") == "1")
        self.notice_ttl = int(os.getenv("LUCKYPULL_NOTICE_TTL","20") or 20)
        self.antispam_sec = int(os.getenv("LUCKYPULL_ANTISPAM_SEC","45") or 45)

        # text pattern
        pat = os.getenv("LUCKYPULL_PATTERN", r"\b(wish|warp|pull|tenpull|gacha|roll|multi|banner|rate up|pity|constellation|character event|weapon event)\b")
        self._pat = re.compile(pat, re.I)

        # image heuristic
        self.image_heur = (os.getenv("LUCKYPULL_IMAGE_HEURISTICS","1") == "1")
        self.grid_min_v = int(os.getenv("LUCKYPULL_GRID_MIN_VLINES","3") or 3)
        self.grid_min_h = int(os.getenv("LUCKYPULL_GRID_MIN_HLINES","2") or 2)
        self.grid_max_v = int(os.getenv("LUCKYPULL_GRID_MAX_VLINES","20") or 20)
        self.grid_max_h = int(os.getenv("LUCKYPULL_GRID_MAX_HLINES","10") or 10)

        # Gemini 2.5
        self.gemini_enable = (os.getenv("LUCKYPULL_GEMINI_ENABLE","1") == "1")
        self.gemini_model = os.getenv("LUCKYPULL_GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        try:
            self.gemini_min_conf = float(os.getenv("LUCKYPULL_GEMINI_MIN_CONF", str(GEMINI_MIN_CONF)))
        except Exception:
            self.gemini_min_conf = 0.55

        self._last_notice: dict[int, float] = {}

    # ---------------- Heuristics ----------------
    def _looks_text(self, content: str) -> bool:
        return bool(self._pat.search(content or ""))

    def _looks_image(self, raw: bytes) -> bool:
        if not (self.image_heur and Image and ImageFilter and ImageOps):
            return False
        try:
            im = Image.open(BytesIO(raw)).convert("L").resize((256,256))
            ed = ImageOps.autocontrast(im.filter(ImageFilter.FIND_EDGES))
            w,h=ed.size; px=ed.load()
            col=[0]*w; row=[0]*h
            for y in range(h):
                s=0
                for x in range(w): s+=px[x,y]
                row[y]=s
            for x in range(w):
                s=0
                for y in range(h): s+=px[x,y]
                col[x]=s
            rmax=max(row) or 1; cmax=max(col) or 1
            row=[r/rmax for r in row]; col=[c/cmax for c in col]
            def smooth(a):
                o=[]; n=len(a)
                for i in range(n):
                    s=0; c=0
                    for k in range(-2,3):
                        j=i+k
                        if 0<=j<n: s+=a[j]; c+=1
                    o.append(s/max(1,c))
                return o
            def peaks(a,t):
                cnt=0; on=False
                for v in a:
                    if not on and v>=t: on=True; cnt+=1
                    elif on and v<t*0.8: on=False
                return cnt
            vh=peaks(smooth(row),0.6); vv=peaks(smooth(col),0.6)
            return (self.grid_min_v <= vv <= self.grid_max_v) and (self.grid_min_h <= vh <= self.grid_max_h)
        except Exception:
            return False

    def _is_guarded_here(self, ch: discord.abc.GuildChannel) -> bool:
        if self.allow_channels and getattr(ch, "id", None) in self.allow_channels:
            return False  # allowed channel
        if self.guard_channels:
            return getattr(ch, "id", None) in self.guard_channels
        return True  # global guard

    # ---------------- Listener ----------------
    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        try:
            if not m or not m.guild or m.author.bot:
                return
            if not self._is_guarded_here(m.channel):
                return

            # quick text+ext check
            looks = self._looks_text(m.content or "")
            if not looks and m.attachments:
                for a in m.attachments:
                    fn = (a.filename or "").lower()
                    if any(fn.endswith(ext) for ext in IMAGE_EXTS):
                        try:
                            raw = await a.read()
                        except Exception:
                            raw = None
                        if raw and self._looks_image(raw):
                            looks = True
                            break

            # ask Gemini 2.5 if still uncertain
            if not looks and self.gemini_enable and m.attachments:
                gj = await gemini_judge_images(m.attachments, model=self.gemini_model)
                if isinstance(gj, tuple):
                    is_gacha, conf, used_model = gj
                    if conf >= self.gemini_min_conf and is_gacha:
                        looks = True

            if not looks:
                return

            # enforce
            redir = f"<#{self.redirect_channel_id}>" if self.redirect_channel_id else "channel yang ditentukan"

            # anti-spam per user
            now = time.time()
            last = self._last_notice.get(m.author.id, 0)
            if now - last < self.antispam_sec:
                try:
                    await m.delete()
                except Exception:
                    pass
                return

            # delete & notify
            try:
                await m.delete()
            except Exception:
                pass
            try:
                mention = m.author.mention if self.mention else ""
                msg = await m.channel.send(f"{mention} gambar lucky-pull/gacha dipindahkan. Silakan post di {redir}.")
                self._last_notice[m.author.id] = now
                if self.notice_ttl > 0:
                    try:
                        await asyncio.sleep(self.notice_ttl)
                        await msg.delete()
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception as e:
            log.exception("[lucky-pull] on_message error: %s", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(LuckyPullAuto(bot))
