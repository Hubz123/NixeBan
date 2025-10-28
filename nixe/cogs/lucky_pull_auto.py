# -*- coding: utf-8 -*-
from __future__ import annotations
import logging

import discord
from discord.ext import commands
from nixe.helpers.gemini_bridge import classify_lucky_pull

log = logging.getLogger(__name__)

# -*- coding: utf-8 -*-
# Patch v17: robust image detect + dynamic refresh + post-ready log + force read runtime_env.json
import asyncio, time, os, json, pathlib
IMAGE_EXTS = ('.png','.jpg','.jpeg','.webp','.gif','.bmp','.heic','.heif','.tiff','.tif')
def _is_image(att):
    ct = (getattr(att, 'content_type', None) or '').lower()
    if ct.startswith('image/'):
        return True
    name = (getattr(att, 'filename', '') or '').lower()
    return name.endswith(IMAGE_EXTS)

# runtime_env.json loader (cached)
_ENV_JSON_CACHE = None
_ENV_JSON_MTIME = None
def _envjson_path():
    # allow override; else locate next to this cog under nixe/config/runtime_env.json
    cand = os.getenv("NIXE_RUNTIME_ENV_PATH")
    if cand and os.path.exists(cand):
        return pathlib.Path(cand)
    return pathlib.Path(__file__).resolve().parents[1] / "config" / "runtime_env.json"

def _load_envjson(force=False):
    global _ENV_JSON_CACHE, _ENV_JSON_MTIME
    p = _envjson_path()
    try:
        mtime = p.stat().st_mtime
    except Exception:
        mtime = None
    if force or (_ENV_JSON_CACHE is None) or (_ENV_JSON_MTIME != mtime):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        _ENV_JSON_CACHE = data
        _ENV_JSON_MTIME = mtime
    return _ENV_JSON_CACHE or {}

def _cfg_pull_raw(name: str):
    # try helper first
    origin = "helper"
    v = None
    try:
        from nixe.config.runtime_env import cfg_str
        v = cfg_str(name, None)
    except Exception:
        pass
    if v in (None, "", "null", "None"):
        # try OS env
        origin = "osenv"
        v = os.getenv(name, None)
    if v in (None, "", "null", "None"):
        # fallback to JSON file
        origin = "json"
        envj = _load_envjson()
        v = envj.get(name)
    return v, origin

def _cfg_str(name: str, default: str | None = None):
    v, _ = _cfg_pull_raw(name)
    if v in (None, "", "null", "None"):
        return default
    return str(v)

def _cfg_float(name: str, default: float):
    v, _ = _cfg_pull_raw(name)
    if v in (None, "", "null", "None"):
        return default
    try:
        return float(v)
    except Exception:
        return default

def _cfg_bool(name: str, default: bool=False):
    v, _ = _cfg_pull_raw(name)
    if v is None: return default
    s = str(v).strip().lower()
    if s in ("1","true","yes","on"): return True
    if s in ("0","false","no","off"): return False
    return default

def _cfg_origin(name: str):
    _, origin = _cfg_pull_raw(name)
    return origin


class LuckyPullAuto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # enable via JSON or runtime_env
        try:
            import json, pathlib
            CFG_PATH = pathlib.Path(__file__).resolve().parents[1] / "config" / "gacha_guard.json"
            with CFG_PATH.open("r", encoding="utf-8") as f:
                _cfg = json.load(f)
        except Exception:
            _cfg = {}
        g = (_cfg.get("lucky_guard", {}) or {}).get("gemini", {}) or {}
        self.enable = bool(g.get("enable", False)) or _cfg_bool("LUCKYPULL_GEMINI_ENABLE", False)

        self.api_key = _cfg_str("GEMINI_API_KEY")
        self.model = _cfg_str("GEMINI_MODEL", str(g.get("model", "gemini-2.5-flash"))) or "gemini-2.5-flash"
        try:
            self.timeout_ms = int(g.get("timeout_ms", 1200))
        except Exception:
            self.timeout_ms = 1200

        if _cfg_bool("LUCKYPULL_DEBUG", False):
            log.warning("[lpa] gemini enable=%s model=%s timeout_ms=%s key=%s",
                        self.enable, self.model, self.timeout_ms, "set" if bool(self.api_key) else "missing")

    @commands.Cog.listener("on_message")
    async def _on_message(self, msg: discord.Message):
        if not self.enable or msg.author.bot or not msg.attachments:
            return
        images = [a for a in msg.attachments if _is_image(a)]
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
                if _cfg_bool("LUCKYPULL_DEBUG", False):
                    log.warning("[lpa:debug] hint msg=%s label=%s conf=%.3f model=%s", msg.id, result.get("label"), float(result.get("confidence",0.0)), self.model)
            except Exception as e:
                if _cfg_bool("LUCKYPULL_DEBUG", False):
                    log.warning("[lpa:debug] gemini error: %s", e)
                pass
        asyncio.create_task(worker())

async def setup(bot: commands.Bot):
    if bot.get_cog("LuckyPullAuto"): return
    try:
        await bot.add_cog(LuckyPullAuto(bot))
    except Exception:
        pass
