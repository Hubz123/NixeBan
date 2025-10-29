# -*- coding: utf-8 -*-
from __future__ import annotations
import logging, asyncio
import discord
from discord.ext import commands
classify_lucky_pull = None  # lazy import

log = logging.getLogger(__name__)

IMAGE_EXTS = ('.png','.jpg','.jpeg','.webp','.gif','.bmp','.heic','.heif','.tiff','.tif')
def _is_image(att):
    ct = (getattr(att, 'content_type', None) or '').lower()
    if ct.startswith('image/'): return True
    name = (getattr(att, 'filename', '') or '').lower()
    return name.endswith(IMAGE_EXTS)

def _cfg_bool(name: str, default: bool=False):
    import os
    try:
        from nixe.config.runtime_env import cfg_str
        v = cfg_str(name, None)
    except Exception:
        v = os.getenv(name, None)
    if v is None: return default
    s = str(v).strip().lower()
    if s in ('1','true','yes','on'): return True
    if s in ('0','false','no','off'): return False
    return default

def _cfg_str(name: str, default: str | None=None):
    import os
    try:
        from nixe.config.runtime_env import cfg_str as _c
        v = _c(name, None)
    except Exception:
        v = os.getenv(name, None)
    if v in (None, '', 'null', 'None'): return default
    return str(v)

class LuckyPullAuto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enable = _cfg_bool('LUCKYPULL_GEMINI_ENABLE', False)
        self.api_key = _cfg_str('GEMINI_API_KEY')
        # Enforce latest-only: respect ENV/JSON model, default gemini-2.5-flash, NO fallback.
        self.model = _cfg_str('GEMINI_MODEL', 'gemini-2.5-flash') or 'gemini-2.5-flash'
        try:
            self.timeout_ms = int(_cfg_str('LUCKYPULL_MAX_LATENCY_MS', '1200') or '1200')
        except Exception:
            self.timeout_ms = 1200
        if _cfg_bool('LUCKYPULL_DEBUG', False):
            log.warning('[lpa] gemini enable=%s model=%s timeout_ms=%s key=%s',
                        self.enable, self.model, self.timeout_ms, 'set' if bool(self.api_key) else 'missing')

    @commands.Cog.listener('on_message')
    async def _on_message(self, msg: discord.Message):
        if not self.enable or msg.author.bot or not msg.attachments:
            return
        images = [a for a in msg.attachments if _is_image(a)][:3]
        if not images: return

        datas = []
        for a in images:
            try: datas.append(await a.read(use_cached=True))
            except Exception: pass
        if not datas: return

        txt = (msg.content or '').lower()
        kw = []
        for k in ('pull','wish','gacha','rate up','pity','x10','10x','multi-draw','ssr','ur','banner','result'):
            if k in txt: kw.append(k)
        for a in images:
            fn = (a.filename or '').lower()
            for k in ('pull','wish','gacha','rate','pity','x10','10x','ssr','ur','banner','result'):
                if k in fn and k not in kw: kw.append(k)
        hints = ', '.join(kw) if kw else ''

        cache = getattr(self.bot, '_lp_auto', None)
        if cache is None:
            cache = self.bot._lp_auto = {}

        async def worker():
            try:
                result = await classify_lucky_pull(datas, api_key=self.api_key, model=self.model, timeout_ms=self.timeout_ms, hints=hints)
                cache[msg.id] = {'label': result.get('label','other'), 'conf': float(result.get('confidence',0.0))}
                if _cfg_bool('LUCKYPULL_DEBUG', False):
                    log.warning('[lpa:debug] hint msg=%s label=%s conf=%.3f model=%s', msg.id, result.get('label'), float(result.get('confidence',0.0)), self.model)
            except Exception as e:
                if _cfg_bool('LUCKYPULL_DEBUG', False):
                    log.warning('[lpa:debug] gemini error: %s', e)
        asyncio.create_task(worker())

async def setup(bot: commands.Bot):
    # lazy import once when cog is added
    global classify_lucky_pull
    if classify_lucky_pull is None:
        try:
            from nixe.helpers.gemini_bridge import classify_lucky_pull as _clf
            classify_lucky_pull = _clf
        except Exception as e:
            logging.getLogger(__name__).warning('[lpa] gemini unavailable: %s', e)
            # still add cog; it will just skip gemini path

    if bot.get_cog('LuckyPullAuto'): return
    try:
        await bot.add_cog(LuckyPullAuto(bot))
    except Exception:
        pass
