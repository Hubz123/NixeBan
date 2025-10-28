# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from typing import Set

import discord
from discord.ext import commands

from nixe.helpers.persona import yandere
from nixe.helpers.lucky_classifier import classify_image_meta

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


def _parse_id_list(s: str | None) -> Set[int]:
    out: Set[int] = set()
    if not s:
        return out
    for tok in str(s).replace(";", ",").split(","):
        tok = tok.strip()
        if not tok:
            continue
        tok = tok.strip("<#> ").replace("_", "")
        if tok.isdigit():
            try:
                out.add(int(tok))
            except Exception:
                pass
    return out

class LuckyPullGuard(commands.Cog):
    """Yandere guard with:
    - robust image detect (content_type/filename)
    - dynamic env refresh
    - post-ready env log showing origins (helper/osenv/json)
    - strict delete on guard channels if enabled
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # JSON defaults (from gacha_guard.json)
        try:
            import json, pathlib
            CFG_PATH = pathlib.Path(__file__).resolve().parents[1] / "config" / "gacha_guard.json"
            with CFG_PATH.open("r", encoding="utf-8") as f:
                _cfg = json.load(f)
        except Exception:
            _cfg = {}
        cfg = _cfg.get("lucky_guard", {})
        self.enable = bool(cfg.get("enable", True))
        base_json = {int(x) for x in cfg.get("guard_channels", []) if str(x).isdigit()}
        self.redirect_channel = int(cfg.get("redirect_channel", 0)) or None
        self._json_delete = float(cfg.get("min_confidence_delete", 0.85))
        self._json_redirect = float(cfg.get("min_confidence_redirect", 0.60))
        g = cfg.get("gemini", {}) or {}
        self._json_wait = int(g.get("timeout_ms", 1200)) if bool(g.get("enable", False)) else 0

        # Runtime (will refresh)
        self.guard_channels: Set[int] = base_json | _parse_id_list(_cfg_str("LUCKYPULL_GUARD_CHANNELS")) | _parse_id_list(_cfg_str("LUCKYPULL_GUARD_CHANNELS_EXTRA"))
        self.min_conf_delete = self._json_delete
        self.min_conf_redirect = self._json_redirect
        self.wait_ms = self._json_wait
        self.strict_delete_on_guard = False
        self.gemini_lucky_thr = 0.65
        self.debug = False
        self._last_tick = 0.0

        # Boot log (pre-refresh)
        log.warning("[lpg] guard_channels=%s redirect=%s wait_ms=%s delete>=%.2f redirect>=%.2f strict_on_guard=%s gem_thr=%.2f",
                    sorted(self.guard_channels), self.redirect_channel, self.wait_ms,
                    self.min_conf_delete, self.min_conf_redirect,
                    self.strict_delete_on_guard, self.gemini_lucky_thr)

        # Post-ready refresh & log with ORIGINS
        bot.loop.create_task(self._post_ready())

    async def _post_ready(self):
        try:
            await self.bot.wait_until_ready()
            await asyncio.sleep(1.0)
            self._refresh_env(force=True)
            log.warning("[lpg:env] (post-ready) wait_ms=%s delete>=%.2f redirect>=%.2f strict_on_guard=%s gem_thr=%.2f",
                        self.wait_ms, self.min_conf_delete, self.min_conf_redirect, self.strict_delete_on_guard, self.gemini_lucky_thr)
            # Origins
            log.warning("[lpg:envsrc] del_thr=%s redir_thr=%s wait=%s strict=%s gem_thr=%s",
                        _cfg_origin("LUCKYPULL_DELETE_THRESHOLD"),
                        _cfg_origin("LUCKYPULL_REDIRECT_THRESHOLD"),
                        _cfg_origin("LUCKYPULL_MAX_LATENCY_MS"),
                        _cfg_origin("LUCKYPULL_DELETE_ON_GUARD"),
                        _cfg_origin("GEMINI_LUCKY_THRESHOLD"))
        except Exception:
            pass

    def _refresh_env(self, force: bool=False):
        import time as _t
        if not force and (_t.monotonic() - self._last_tick) < 5.0:
            return
        self._last_tick = _t.monotonic()
        self.min_conf_delete = _cfg_float("LUCKYPULL_DELETE_THRESHOLD", self._json_delete)
        self.min_conf_redirect = _cfg_float("LUCKYPULL_REDIRECT_THRESHOLD", self._json_redirect)
        self.wait_ms = int(_cfg_float("LUCKYPULL_MAX_LATENCY_MS", float(self._json_wait)))
        if self.wait_ms > 2000: self.wait_ms = 2000
        if self.wait_ms < 0: self.wait_ms = 0
        self.strict_delete_on_guard = _cfg_bool("LUCKYPULL_DELETE_ON_GUARD", False)
        self.gemini_lucky_thr = _cfg_float("GEMINI_LUCKY_THRESHOLD", 0.65)
        self.debug = _cfg_bool("LUCKYPULL_DEBUG", False)

    @commands.Cog.listener("on_message")
    async def _on_message(self, msg: discord.Message):
        try:
            if not self.enable or msg.author.bot or not msg.attachments:
                return
            if self.guard_channels and msg.channel.id not in self.guard_channels:
                return

            self._refresh_env()
            images = [a for a in msg.attachments if _is_image(a)]
            if not images:
                return

            # pull gemini hint
            cache = getattr(self.bot, "_lp_auto", None)
            gem_label = None; gem_conf = None
            if cache and msg.id in cache:
                hint = cache.pop(msg.id)
                gem_label = hint.get("label"); 
                try: gem_conf = float(hint.get("conf", 0.0))
                except: gem_conf = 0.0

            best_conf = 0.0; per_file = []
            for a in images:
                meta = classify_image_meta(filename=a.filename, gemini_label=gem_label, gemini_conf=gem_conf)
                c = float(meta.get("confidence", 0.0))
                per_file.append((a.filename, c))
                best_conf = max(best_conf, c)

            # Decision
            action = "none"
            if self.strict_delete_on_guard and (
                best_conf >= self.min_conf_redirect or
                (gem_label == "lucky_pull" and (gem_conf or 0.0) >= self.gemini_lucky_thr)
            ):
                action = "delete"
            elif best_conf >= self.min_conf_delete:
                action = "delete"
            elif best_conf >= self.min_conf_redirect and self.redirect_channel:
                action = "redirect"

            if self.debug:
                log.warning("[lpg:debug] chan=%s(%s) best=%.3f files=%s gem_hint=(%s, %.3f) action=%s thr(del=%.2f redir=%.2f gem=%.2f) wait=%sms",
                            msg.channel.id, getattr(msg.channel, 'name', '?'),
                            best_conf, per_file, gem_label, gem_conf or 0.0, action,
                            self.min_conf_delete, self.min_conf_redirect, self.gemini_lucky_thr, self.wait_ms)

            if action == "delete":
                reason = "deteksi lucky pull"
                user_mention = msg.author.mention
                channel_name = f"#{{getattr(msg.channel, 'name', '?')}}"
                line = yandere(user=user_mention, channel=channel_name, reason=reason)
                await msg.delete()
                await msg.channel.send(line, delete_after=10)
                if self.redirect_channel:
                    try:
                        target = msg.guild.get_channel(self.redirect_channel) or await self.bot.fetch_channel(self.redirect_channel)
                        files = [await a.to_file() for a in images]
                        await target.send(content=f"{{user_mention}} dipindah ke sini karena {{reason}}.", files=files)
                    except Exception:
                        pass
                return

            if action == "redirect":
                try:
                    target = msg.guild.get_channel(self.redirect_channel) or await self.bot.fetch_channel(self.redirect_channel)
                    files = [await a.to_file() for a in images]
                    await target.send(content=f"{{msg.author.mention}} kontenmu dipindah (uncertain).", files=files)
                except Exception:
                    pass
                return
        except discord.Forbidden:
            return
        except Exception as e:
            if self.debug:
                log.warning("[lpg:debug] exception: %s", e)
            return

async def setup(bot: commands.Bot):
    if bot.get_cog("LuckyPullGuard"): return
    try:
        await bot.add_cog(LuckyPullGuard(bot))
    except Exception:
        pass
