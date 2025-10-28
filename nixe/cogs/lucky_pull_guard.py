# -*- coding: utf-8 -*-
from __future__ import annotations
import logging, asyncio, time, os
from typing import Set, Tuple, List, Optional

import discord
from discord.ext import commands

try:
    from nixe.helpers.dotenv_autoload import autoload as _dotenv_autoload
    _dotenv_autoload()
except Exception:
    pass

from nixe.helpers.persona import yandere
from nixe.helpers.lucky_classifier import classify_image_meta
from nixe.helpers.gemini_bridge import classify_lucky_pull

log = logging.getLogger(__name__)

IMAGE_EXTS = ('.png','.jpg','.jpeg','.webp','.gif','.bmp','.heic','.heif','.tiff','.tif')
def _is_image(att):
    ct = (getattr(att, 'content_type', None) or '').lower()
    if ct.startswith('image/'): return True
    name = (getattr(att, 'filename', '') or '').lower()
    return name.endswith(IMAGE_EXTS)

def _cfg_pull_raw(name: str):
    import json, pathlib
    origin = "helper"
    v = None
    try:
        from nixe.config.runtime_env import cfg_str as _c
        v = _c(name, None)
    except Exception:
        pass
    if v in (None, "", "null", "None"):
        origin = "osenv"
        v = os.getenv(name, None)
    if v in (None, "", "null", "None"):
        origin = "json"
        p = pathlib.Path(__file__).resolve().parents[1] / "config" / "runtime_env.json"
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            v = data.get(name)
        except Exception:
            v = None
    return v, origin

def _cfg_str(name: str, default: Optional[str]=None):
    v, _ = _cfg_pull_raw(name)
    return default if v in (None, "", "null", "None") else str(v)

def _cfg_bool(name: str, default: bool=False):
    v, _ = _cfg_pull_raw(name)
    if v is None: return default
    s = str(v).strip().lower()
    if s in ("1","true","yes","on"): return True
    if s in ("0","false","no","off"): return False
    return default

def _cfg_float(name: str, default: float):
    v, _ = _cfg_pull_raw(name)
    try: return float(v)
    except Exception: return default

def _cfg_origin(name: str):
    _, o = _cfg_pull_raw(name); return o

def _parse_id_list(s: str | None) -> Set[int]:
    out: Set[int] = set()
    if not s: return out
    for tok in str(s).replace(";", ",").split(","):
        tok = tok.strip()
        if not tok: continue
        tok = tok.strip("<#> ").replace("_","")
        if tok.isdigit():
            out.add(int(tok))
    return out

def _norm_label(s: Optional[str]) -> Optional[str]:
    if not s: return None
    t = str(s).strip().lower()
    syn = ("lucky_pull","lucky","gacha","warp","wish","summon","roll","pull","banner","tenpull","ten-pull","multi-pull","multi","star rail","warp screen")
    for k in syn:
        if k in t:
            return "lucky_pull"
    if t in ("other","non_gacha","not_gacha","none"):
        return "other"
    return t

class LuckyPullGuard(commands.Cog):
    """Lucky pull guard with forced inline Gemini run (no-Pro), normalized labels, strict latency budget."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guard_channels: Set[int] = _parse_id_list(_cfg_str("LUCKYPULL_GUARD_CHANNELS"))
        redir = _cfg_str("LUCKYPULL_REDIRECT_CHANNEL_ID", "0") or "0"
        try: self.redirect_channel = int(float(redir))
        except Exception: self.redirect_channel = 0
        if self.redirect_channel == 0: self.redirect_channel = None

        self.min_conf_delete = _cfg_float("LUCKYPULL_DELETE_THRESHOLD", 0.85)
        self.min_conf_redirect = _cfg_float("LUCKYPULL_REDIRECT_THRESHOLD", 0.70)
        self.strict_delete_on_guard = _cfg_bool("LUCKYPULL_DELETE_ON_GUARD", False)
        self.debug = _cfg_bool("LUCKYPULL_DEBUG", False)

        self.total_wait_ms = int(_cfg_float("LUCKYPULL_MAX_LATENCY_MS", 1200))
        self.concurrent = _cfg_bool("LUCKYPULL_CONCURRENT", True)

        self.gem_enable = _cfg_bool("LUCKYPULL_GEMINI_ENABLE", False)
        self.gem_thr = _cfg_float("GEMINI_LUCKY_THRESHOLD", 0.75)
        self.gem_model = _cfg_str("GEMINI_MODEL", "gemini-2.5-flash")
        self.gem_key = _cfg_str("GEMINI_API_KEY", None)

        key_mask = (("*"*6) + (self.gem_key or "")[-4:]) if self.gem_key else "<none>"
        log.warning("[lpg] guard_channels=%s redirect=%s wait=%sms strict_on_guard=%s del>=%.2f redir>=%.2f gem_thr=%.2f model=%s key=%s gem_enable=%s",
                    sorted(self.guard_channels), self.redirect_channel, self.total_wait_ms, self.strict_delete_on_guard,
                    self.min_conf_delete, self.min_conf_redirect, self.gem_thr, self.gem_model, key_mask, self.gem_enable)

        bot.loop.create_task(self._post_ready())

    async def _post_ready(self):
        await self.bot.wait_until_ready()
        log.warning("[lpg:env] (post-ready) wait=%sms del>=%.2f redir>=%.2f strict_on_guard=%s gem_thr=%.2f model=%s",
                    self.total_wait_ms, self.min_conf_delete, self.min_conf_redirect, self.strict_delete_on_guard, self.gem_thr, self.gem_model)
        log.warning("[lpg:envsrc] del_thr=%s redir_thr=%s wait=%s gem_thr=%s model=%s",
                    _cfg_origin("LUCKYPULL_DELETE_THRESHOLD"),
                    _cfg_origin("LUCKYPULL_REDIRECT_THRESHOLD"),
                    _cfg_origin("LUCKYPULL_MAX_LATENCY_MS"),
                    _cfg_origin("GEMINI_LUCKY_THRESHOLD"),
                    _cfg_origin("GEMINI_MODEL"))

    async def _cached_hint(self, msg_id: int, deadline: float) -> Tuple[Optional[str], Optional[float]]:
        while time.monotonic() < deadline:
            cache = getattr(self.bot, "_lp_auto", None)
            if cache and msg_id in cache:
                hint = cache.pop(msg_id)
                lab = _norm_label(hint.get("label"))
                try: conf = float(hint.get("conf", 0.0))
                except: conf = 0.0
                return lab, conf
            await asyncio.sleep(0.03)
        cache = getattr(self.bot, "_lp_auto", None)
        if cache and msg_id in cache:
            hint = cache.pop(msg_id)
            lab = _norm_label(hint.get("label"))
            try: conf = float(hint.get("conf", 0.0))
            except: conf = 0.0
            return lab, conf
        return None, None

    async def _inline_gemini(self, images: List[discord.Attachment], timeout_ms: int) -> Tuple[Optional[str], Optional[float], str]:
        if not self.gem_enable:
            if self.debug: log.warning("[lpg:inline] skip reason=gemini_disabled")
            return None, None, "skip"
        if not self.gem_key:
            if self.debug: log.warning("[lpg:inline] skip reason=missing_key")
            return None, None, "skip"
        if timeout_ms <= 0:
            if self.debug: log.warning("[lpg:inline] skip reason=no_budget")
            return None, None, "skip"
        try:
            datas = []
            for a in images[:3]:
                try:
                    # for older discord.py, .read() has no use_cached arg; call without it
                    try:
                        b = await a.read(use_cached=True)
                    except TypeError:
                        b = await a.read()
                    datas.append(b)
                except Exception:
                    pass
            if not datas:
                if self.debug: log.warning("[lpg:inline] skip reason=noimg")
                return None, None, "noimg"
            if self.debug:
                log.warning("[lpg:inline] starting gemini model=%s budget=%dms imgs=%d", self.gem_model, timeout_ms, len(datas))
            res = await asyncio.wait_for(
                classify_lucky_pull(datas, api_key=self.gem_key, model=self.gem_model, timeout_ms=timeout_ms, hints="guard-inline"),
                timeout=timeout_ms/1000.0 + 0.05
            )
            lab = _norm_label(res.get("label") or None)
            try: conf = float(res.get("confidence", 0.0))
            except: conf = 0.0
            if self.debug:
                log.warning("[lpg:inline] result label=%s conf=%.3f", lab, conf)
            return lab, conf, "ok"
        except asyncio.TimeoutError as e:
            if self.debug:
                log.warning("[lpg:inline] timeout (%s)", type(e).__name__)
            return None, None, "timeout"
        except Exception as e:
            if self.debug:
                log.warning("[lpg:inline] error (%s): %s", type(e).__name__, e)
            return None, None, "error"

    @commands.Cog.listener("on_message")
    async def _on_message(self, msg: discord.Message):
        try:
            if msg.author.bot or not msg.attachments:
                return
            if self.guard_channels and msg.channel.id not in self.guard_channels:
                return

            images = [a for a in msg.attachments if _is_image(a)]
            if not images:
                return

            deadline = time.monotonic() + (self.total_wait_ms/1000.0)

            # Start tasks; DO NOT cancel inline gemini to ensure it actually runs & logs
            t_hint = asyncio.create_task(self._cached_hint(msg.id, deadline))
            t_gem = None
            if self.gem_enable:
                t_gem = asyncio.create_task(self._inline_gemini(images, int(self.total_wait_ms*0.9)))

            # Wait for both or until deadline
            await asyncio.wait([t for t in (t_hint, t_gem) if t is not None], timeout=self.total_wait_ms/1000.0, return_when=asyncio.ALL_COMPLETED)

            # Collect results
            gem_label = None; gem_conf = None
            try:
                lab, conf = t_hint.result()
                if lab is not None:
                    gem_label, gem_conf = lab, conf
            except Exception:
                pass
            if t_gem:
                try:
                    lab2, conf2, _ = t_gem.result()
                    # choose best confidence if both exist
                    if lab2 is not None and (gem_conf is None or (conf2 or 0.0) >= (gem_conf or 0.0)):
                        gem_label, gem_conf = lab2, conf2
                except Exception:
                    pass

            best_conf = 0.0; per_file = []
            for a in images:
                meta = classify_image_meta(filename=a.filename, gemini_label=gem_label, gemini_conf=gem_conf)
                c = float(meta.get("confidence", 0.0))
                per_file.append((a.filename, c))
                best_conf = max(best_conf, c)

            action = "none"
            has_gem = (gem_label == "lucky_pull" and (gem_conf or 0.0) >= self.gem_thr)
            if self.strict_delete_on_guard and (best_conf >= self.min_conf_redirect or has_gem):
                action = "delete"
            elif best_conf >= self.min_conf_delete:
                action = "delete"
            elif (best_conf >= self.min_conf_redirect or has_gem) and self.redirect_channel:
                action = "redirect"

            if self.debug:
                log.warning("[lpg:debug] chan=%s(%s) best=%.3f files=%s gem_hint=(%s, %.3f) action=%s thr(del=%.2f redir=%.2f gem=%.2f) wait=%sms",
                            msg.channel.id, getattr(msg.channel, 'name', '?'), best_conf, per_file, gem_label, gem_conf or 0.0, action,
                            self.min_conf_delete, self.min_conf_redirect, self.gem_thr, self.total_wait_ms)

            if action == "delete":
                reason = "deteksi lucky pull"
                user_mention = msg.author.mention
                channel_name = f"#{getattr(msg.channel, 'name', '?')}"
                line = yandere(user=user_mention, channel=channel_name, reason=reason)
                try:
                    await msg.delete()
                except discord.Forbidden:
                    return
                except Exception:
                    pass
                try:
                    await msg.channel.send(line, delete_after=10)
                except Exception:
                    pass
                if self.redirect_channel:
                    try:
                        target = msg.guild.get_channel(self.redirect_channel) or await self.bot.fetch_channel(self.redirect_channel)
                        files = [await a.to_file() for a in images]
                        await target.send(content=f"{user_mention} dipindah ke sini karena {reason}.", files=files)
                    except Exception:
                        pass
                return

            if action == "redirect" and self.redirect_channel:
                try:
                    target = msg.guild.get_channel(self.redirect_channel) or await self.bot.fetch_channel(self.redirect_channel)
                    files = [await a.to_file() for a in images]
                    await target.send(content=f"{msg.author.mention} kontenmu dipindah (uncertain).", files=files)
                except Exception:
                    pass
        except Exception as e:
            if self.debug:
                log.warning("[lpg:debug] exception (%s): %s", type(e).__name__, e)

async def setup(bot: commands.Bot):
    if bot.get_cog("LuckyPullGuard"): return
    try:
        await bot.add_cog(LuckyPullGuard(bot))
    except Exception:
        pass
