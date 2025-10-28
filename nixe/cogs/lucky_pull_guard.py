# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, pathlib, logging, asyncio, time
from typing import Set

import discord
from discord.ext import commands

from nixe.helpers.persona import yandere
from nixe.helpers.lucky_classifier import classify_image_meta

log = logging.getLogger(__name__)
CFG_PATH = pathlib.Path(__file__).resolve().parents[1] / "config" / "gacha_guard.json"

# -*- coding: utf-8 -*-
# Patch v16: robust image detection (handles missing content_type) + boot env refresh
import asyncio, time
IMAGE_EXTS = ('.png','.jpg','.jpeg','.webp','.gif','.bmp','.heic','.heif','.tiff','.tif')
def _is_image(att):
    ct = (getattr(att, 'content_type', None) or '').lower()
    if ct.startswith('image/'):
        return True
    name = (getattr(att, 'filename', '') or '').lower()
    return name.endswith(IMAGE_EXTS)


def _load_cfg() -> dict:
    try:
        with CFG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"lucky_guard": {}}

def _cfg_str(name: str, default: str | None = None) -> str | None:
    # Prefer runtime_env.json helper if available, else OS env
    try:
        from nixe.config.runtime_env import cfg_str
        v = cfg_str(name, None)
        if v not in (None, "", "null", "None"):
            return str(v)
    except Exception:
        pass
    v = os.getenv(name, default if default is not None else "")
    return v if v not in (None, "", "null", "None") else None

def _cfg_float(name: str, default: float) -> float:
    v = _cfg_str(name, None)
    if v is None:
        return default
    try:
        return float(v)
    except Exception:
        return default

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
    """Yandere persona; strict delete on guard channels if enabled.
    - Robust image detection (content_type fallback to filename ext)
    - Dynamic runtime_env refresh (boot + periodic + pre-decision)
    - Boot env log after refresh for clear visibility
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        cfg = _load_cfg().get("lucky_guard", {})
        self.enable = bool(cfg.get("enable", True))

        base_json = {int(x) for x in cfg.get("guard_channels", []) if str(x).isdigit()}
        env_main = _parse_id_list(_cfg_str("LUCKYPULL_GUARD_CHANNELS"))
        env_extra = _parse_id_list(_cfg_str("LUCKYPULL_GUARD_CHANNELS_EXTRA"))
        self.guard_channels: Set[int] = base_json | env_main | env_extra

        self.redirect_channel = int(cfg.get("redirect_channel", 0)) or None

        # JSON defaults; env may override at runtime
        self._json_delete = float(cfg.get("min_confidence_delete", 0.85))
        self._json_redirect = float(cfg.get("min_confidence_redirect", 0.60))
        g = cfg.get("gemini", {}) or {}
        self._json_wait = int(g.get("timeout_ms", 1200)) if bool(g.get("enable", False)) else 0

        # Runtime values (refreshed)
        self.min_conf_delete = self._json_delete
        self.min_conf_redirect = self._json_redirect
        self.wait_ms = self._json_wait
        self.strict_delete_on_guard = False
        self.gemini_lucky_thr = 0.65
        self.debug = False

        # Immediate refresh at boot
        self._last_refresh = 0.0
        self._refresh_env(force=True)

        # Print boot line (may still show defaults if env not ready yet)
        log.warning("[lpg] guard_channels=%s redirect=%s wait_ms=%s delete>=%.2f redirect>=%.2f strict_on_guard=%s gem_thr=%.2f",
                    sorted(self.guard_channels), self.redirect_channel, self.wait_ms,
                    self.min_conf_delete, self.min_conf_redirect,
                    self.strict_delete_on_guard, self.gemini_lucky_thr)

        # Schedule a post-ready refresh + log to show final values after env_admin loaded
        bot.loop.create_task(self._post_ready_log())

    async def _post_ready_log(self):
        try:
            await self.bot.wait_until_ready()
            await asyncio.sleep(1.0)
            self._refresh_env(force=True)
            log.warning("[lpg:env] (post-ready) wait_ms=%s delete>=%.2f redirect>=%.2f strict_on_guard=%s gem_thr=%.2f",
                        self.wait_ms, self.min_conf_delete, self.min_conf_redirect,
                        self.strict_delete_on_guard, self.gemini_lucky_thr)
        except Exception:
            pass

    def _refresh_env(self, force: bool = False):
        now = time.monotonic()
        if not force and now - self._last_refresh < 5.0:
            return
        self._last_refresh = now
        # Thresholds
        self.min_conf_delete = _cfg_float("LUCKYPULL_DELETE_THRESHOLD", self._json_delete)
        self.min_conf_redirect = _cfg_float("LUCKYPULL_REDIRECT_THRESHOLD", self._json_redirect)
        # Wait (clamped)
        self.wait_ms = int(_cfg_float("LUCKYPULL_MAX_LATENCY_MS", float(self._json_wait)))
        if self.wait_ms > 2000: self.wait_ms = 2000
        if self.wait_ms < 0: self.wait_ms = 0
        # Strict + Gemini lucky threshold
        self.strict_delete_on_guard = (_cfg_str("LUCKYPULL_DELETE_ON_GUARD") in ("1","true","yes","on"))
        self.gemini_lucky_thr = _cfg_float("GEMINI_LUCKY_THRESHOLD", 0.65)
        # Debug
        self.debug = _cfg_str("LUCKYPULL_DEBUG") in ("1","true","yes","on")

    @commands.Cog.listener("on_message")
    async def _on_message(self, msg: discord.Message):
        try:
            if not self.enable or msg.author.bot or not msg.attachments:
                return
            if self.guard_channels and msg.channel.id not in self.guard_channels:
                return

            # Ensure env is fresh for decisions
            self._refresh_env()

            images = [a for a in msg.attachments if _is_image(a)]
            if not images:
                return

            # Pull Gemini auto-hint from cache (populated by lucky_pull_auto)
            cache = getattr(self.bot, "_lp_auto", None)
            gem_label = None
            gem_conf = None
            if cache and msg.id in cache:
                hint = cache.pop(msg.id)
                gem_label = hint.get("label")
                gem_conf = float(hint.get("conf", 0.0))

            best_conf = 0.0
            per_file = []
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
