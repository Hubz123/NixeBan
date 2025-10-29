# -*- coding: utf-8 -*-
from __future__ import annotations
import asyncio, logging, time, base64
from discord.ext import commands
from nixe.helpers.env_reader import get as _cfg_get, get_int as _cfg_int, get_bool01 as _cfg_bool01
log = logging.getLogger(__name__)
_PNG_1x1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAoMBgV31vHUAAAAASUVORK5CYII=")
class GeminiWarmup(commands.Cog):
    def __init__(self, bot): self.bot = bot; self._once=False
    @commands.Cog.listener()
    async def on_ready(self):
        if self._once: return
        self._once=True
        asyncio.create_task(self._go(), name="gemini-warmup")
    async def _go(self):
        try:
            if _cfg_bool01("GEMINI_WARMUP_ENABLE","1")!="1": 
                log.info("[gemini-warmup] disabled"); return
            tout = _cfg_int("GEMINI_WARMUP_TIMEOUT_MS", 4000)
        except Exception as e:
            log.warning("[gemini-warmup] cfg fail: %r", e); return
        try:
            import importlib, time
            mod = importlib.import_module("nixe.helpers.gemini_bridge")
            func = getattr(mod, "classify_lucky_pull", None)
            if not callable(func): raise RuntimeError("classify_lucky_pull missing")
            t0=time.perf_counter()
            label, conf = await func([_PNG_1x1], hints="warmup", timeout_ms=tout)
            dt=int((time.perf_counter()-t0)*1000)
            log.info("[gemini-warmup] label=%s conf=%.3f in %dms", label, conf, dt)
        except Exception as e:
            log.warning("[gemini-warmup] warmup failed: %r", e)
async def setup(bot): 
    try: await bot.add_cog(GeminiWarmup(bot)); log.info("[gemini-warmup] loaded")
    except Exception as e: log.error("[gemini-warmup] setup failed: %r", e)
