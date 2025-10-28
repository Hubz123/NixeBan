# -*- coding: utf-8 -*-
from __future__ import annotations
import os, pathlib, json, asyncio, logging
import discord
from discord.ext import commands
from nixe.helpers.gemini_bridge import classify_lucky_pull

log = logging.getLogger(__name__)
CFG_PATH = pathlib.Path(__file__).resolve().parents[1] / "config" / "gacha_guard.json"

def _load_cfg() -> dict:
    try:
        with CFG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _cfg_str(name: str, default: str | None = None) -> str | None:
    try:
        from nixe.config.runtime_env import cfg_str
        v = cfg_str(name, None)
        if v not in (None, "", "null", "None"):
            return str(v)
    except Exception:
        pass
    v = os.getenv(name, default if default is not None else "")
    return v if v not in (None, "", "null", "None") else None

class LuckyPullAuto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        cfg = _load_cfg().get("lucky_guard", {})
        g = cfg.get("gemini", {}) or {}
        self.enable = bool(g.get("enable", False))

        key = _cfg_str("GEMINI_API_KEY")
        self.api_key = key
        self.model = _cfg_str("GEMINI_MODEL", str(g.get("model", "gemini-2.5-flash"))) or "gemini-2.5-flash"
        try:
            self.timeout_ms = int(g.get("timeout_ms", 1200))
        except Exception:
            self.timeout_ms = 1200

        self.debug = _cfg_str("LUCKYPULL_DEBUG") in ("1", "true", "yes", "on")

    @commands.Cog.listener("on_message")
    async def _on_message(self, msg: discord.Message):
        if not self.enable or msg.author.bot or not msg.attachments:
            return
        images = [a for a in msg.attachments if (a.content_type or "").startswith("image/")]
        if not images:
            return
        try:
            data = await images[0].read(use_cached=True)
        except Exception:
            return

        cache = getattr(self.bot, "_lp_auto", None)
        if cache is None:
            cache = self.bot._lp_auto = {}

        async def worker():
            try:
                result = await classify_lucky_pull([data], api_key=self.api_key, model=self.model, timeout_ms=self.timeout_ms)
                cache[msg.id] = {"label": result.get("label","other"), "conf": float(result.get("confidence",0.0))}
                if self.debug:
                    log.warning("[lpa:debug] hint msg=%s label=%s conf=%.3f model=%s", msg.id, result.get("label"), float(result.get("confidence",0.0)), self.model)
            except Exception as e:
                if self.debug:
                    log.warning("[lpa:debug] gemini error: %s", e)
                pass
        asyncio.create_task(worker())

async def setup(bot: commands.Bot):
    if bot.get_cog("LuckyPullAuto"):
        return
    try:
        await bot.add_cog(LuckyPullAuto(bot))
    except Exception:
        pass
