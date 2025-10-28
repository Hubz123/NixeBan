# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, pathlib, logging, asyncio
from typing import Set

import discord
from discord.ext import commands

from nixe.helpers.persona import yandere
from nixe.helpers.lucky_classifier import classify_image_meta

log = logging.getLogger(__name__)
CFG_PATH = pathlib.Path(__file__).resolve().parents[1] / "config" / "gacha_guard.json"

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
    """Yandere persona (soft/agro/sharp), random-only.
    Strict delete on guard channels when enabled via ENV (LUCKYPULL_DELETE_ON_GUARD=1).
    Waits for Gemini hint up to LUCKYPULL_MAX_LATENCY_MS (clamped <= 2000 ms).
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        cfg = _load_cfg().get("lucky_guard", {})
        self.enable = bool(cfg.get("enable", True))

        # Base channels from JSON + ENV override/additions
        base_json = {int(x) for x in cfg.get("guard_channels", []) if str(x).isdigit()}
        env_main = _parse_id_list(_cfg_str("LUCKYPULL_GUARD_CHANNELS"))
        env_extra = _parse_id_list(_cfg_str("LUCKYPULL_GUARD_CHANNELS_EXTRA"))
        self.guard_channels: Set[int] = base_json | env_main | env_extra

        self.redirect_channel = int(cfg.get("redirect_channel", 0)) or None

        # thresholds (JSON first, can be overridden by ENV)
        self.min_conf_delete = float(cfg.get("min_confidence_delete", 0.85))
        self.min_conf_redirect = float(cfg.get("min_confidence_redirect", 0.60))
        self.min_conf_delete = _cfg_float("LUCKYPULL_DELETE_THRESHOLD", self.min_conf_delete)
        self.min_conf_redirect = _cfg_float("LUCKYPULL_REDIRECT_THRESHOLD", self.min_conf_redirect)

        # Gemini hint threshold
        self.gemini_lucky_thr = _cfg_float("GEMINI_LUCKY_THRESHOLD", 0.65)

        # Gemini wait (respect <= 2000ms hard cap)
        g = cfg.get("gemini", {}) or {}
        wait_default = int(g.get("timeout_ms", 1200)) if bool(g.get("enable", False)) else 0
        self.wait_ms = int(_cfg_float("LUCKYPULL_MAX_LATENCY_MS", float(wait_default)))
        if self.wait_ms > 2000:
            self.wait_ms = 2000
        if self.wait_ms < 0:
            self.wait_ms = 0

        # Strict delete toggle (from ENV) - applies to ALL guard channels when "1"
        self.strict_delete_on_guard = (_cfg_str("LUCKYPULL_DELETE_ON_GUARD") in ("1","true","yes","on"))

        # Debug
        self.debug = _cfg_str("LUCKYPULL_DEBUG") in ("1","true","yes","on")

        log.warning("[lpg] guard_channels=%s redirect=%s wait_ms=%s delete>=%.2f redirect>=%.2f strict_on_guard=%s gem_thr=%.2f",
                    sorted(self.guard_channels), self.redirect_channel, self.wait_ms,
                    self.min_conf_delete, self.min_conf_redirect,
                    self.strict_delete_on_guard, self.gemini_lucky_thr)

    async def _pull_auto_hint(self, msg_id: int) -> dict:
        cache = getattr(self.bot, "_lp_auto", None)
        if cache and msg_id in cache:
            return cache.pop(msg_id)
        if self.wait_ms <= 0:
            return {}
        remain = self.wait_ms/1000.0
        step = 0.05
        while remain > 0:
            await asyncio.sleep(step)
            remain -= step
            cache = getattr(self.bot, "_lp_auto", None)
            if cache and msg_id in cache:
                return cache.pop(msg_id)
        return {}

    @commands.Cog.listener("on_message")
    async def _on_message(self, msg: discord.Message):
        try:
            if not self.enable or msg.author.bot or not msg.attachments:
                return
            if self.guard_channels and msg.channel.id not in self.guard_channels:
                return

            images = [a for a in msg.attachments if (a.content_type or "").startswith("image/")]
            if not images:
                return

            hint = await self._pull_auto_hint(msg.id)
            gem_label = hint.get("label") if hint else None
            gem_conf = float(hint.get("conf", 0.0)) if hint else None

            best_conf = 0.0
            per_file = []
            for a in images:
                meta = classify_image_meta(filename=a.filename, gemini_label=gem_label, gemini_conf=gem_conf)
                c = float(meta.get("confidence", 0.0))
                per_file.append((a.filename, c))
                best_conf = max(best_conf, c)

            # Decision
            action = "none"

            # If strict-on-guard: escalate delete when redirect threshold is met OR gemini says lucky with conf >= gem_thr
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
                log.warning("[lpg:debug] chan=%s(%s) best=%.3f files=%s gem_hint=(%s, %.3f) action=%s",
                            msg.channel.id, getattr(msg.channel, "name", "?"),
                            best_conf, per_file, gem_label, gem_conf or 0.0, action)

            if action == "delete":
                reason = "deteksi lucky pull"
                user_mention = msg.author.mention
                channel_name = f"#{getattr(msg.channel, 'name', '?')}"
                line = yandere(user=user_mention, channel=channel_name, reason=reason)
                await msg.delete()
                await msg.channel.send(line, delete_after=10)
                if self.redirect_channel:
                    try:
                        target = msg.guild.get_channel(self.redirect_channel) or await self.bot.fetch_channel(self.redirect_channel)
                        files = [await a.to_file() for a in images]
                        await target.send(content=f"{user_mention} dipindah ke sini karena {reason}.", files=files)
                    except Exception:
                        pass
                return

            if action == "redirect":
                try:
                    target = msg.guild.get_channel(self.redirect_channel) or await self.bot.fetch_channel(self.redirect_channel)
                    files = [await a.to_file() for a in images]
                    await target.send(content=f"{msg.author.mention} kontenmu dipindah (uncertain).", files=files)
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
