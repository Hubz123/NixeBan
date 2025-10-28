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

def _get_env_model_default(default: str) -> str:
    # Prefer runtime_env.json via helper if available, else OS env; fallback to default
    try:
        from nixe.config.runtime_env import cfg_str
        val = cfg_str("GEMINI_MODEL", None)
        if val: return val
    except Exception:
        pass
    return os.getenv("GEMINI_MODEL", default)

class LuckyPullAuto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        cfg = _load_cfg().get("lucky_guard", {})
        g = cfg.get("gemini", {}) or {}
        # Prefer env for API key & model; fallback to config JSON
        key = None
        try:
            from nixe.config.runtime_env import cfg_str
            key = cfg_str("GEMINI_API_KEY", None)
        except Exception:
            key = None
        if not key:
            key = os.getenv("GEMINI_API_KEY")
        self.api_key = key

        default_model = str(g.get("model", "gemini-2.5-flash"))
        self.model = _get_env_model_default(default_model)
        try:
            self.timeout_ms = int(g.get("timeout_ms", 1200))
        except Exception:
            self.timeout_ms = 1200

    @commands.Cog.listener("on_message")
    async def _on_message(self, msg: discord.Message):
        if msg.author.bot or not msg.attachments:
            return
        # feature enable flag via config JSON
        cfg = _load_cfg().get("lucky_guard", {})
        g = cfg.get("gemini", {}) or {}
        if not bool(g.get("enable", False)):
            return

        # Only consider images
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
            except Exception:
                pass
        asyncio.create_task(worker())

async def setup(bot: commands.Bot):
    if bot.get_cog("LuckyPullAuto"):
        return
    try:
        await bot.add_cog(LuckyPullAuto(bot))
    except Exception:
        pass
