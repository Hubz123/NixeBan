# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, pathlib, logging, asyncio
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
        return {"lucky_guard": {"enable": True, "guard_channels": [], "redirect_channel": 0,
                                "min_confidence_delete": 0.85, "min_confidence_redirect": 0.60,
                                "dm_user_on_delete": False, "gemini": {"enable": False, "timeout_ms": 800}}}

def _env_int(name: str, default: int) -> int:
    try:
        from nixe.config.runtime_env import cfg_str
        v = cfg_str(name, None)
        if v is not None:
            return int(str(v))
    except Exception:
        pass
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default

class LuckyPullGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        cfg = _load_cfg().get("lucky_guard", {})
        self.enable = bool(cfg.get("enable", True))
        self.guard_channels = {int(x) for x in cfg.get("guard_channels", [])}
        self.redirect_channel = int(cfg.get("redirect_channel", 0)) or None
        self.min_conf_delete = float(cfg.get("min_confidence_delete", 0.85))
        self.min_conf_redirect = float(cfg.get("min_confidence_redirect", 0.60))
        self.dm_user_on_delete = bool(cfg.get("dm_user_on_delete", False))

        g = cfg.get("gemini", {}) or {}
        if bool(g.get("enable", False)):
            # Prefer env wait; fallback JSON
            self.wait_ms = _env_int("LUCKYPULL_MAX_LATENCY_MS", int(g.get("timeout_ms", 800)))
        else:
            self.wait_ms = 0

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
        for a in images:
            meta = classify_image_meta(filename=a.filename, gemini_label=gem_label, gemini_conf=gem_conf)
            best_conf = max(best_conf, float(meta.get("confidence",0.0)))

        try:
            if best_conf >= self.min_conf_delete:
                reason = "deteksi lucky pull (gemini+heur)"
                user_mention = msg.author.mention
                channel_name = f"#{msg.channel.name}"
                line = yandere(user=user_mention, channel=channel_name, reason=reason)
                await msg.delete()
                await msg.channel.send(line, delete_after=10)
                if self.dm_user_on_delete:
                    try: await msg.author.send(f"Kontenmu di {channel_name} dihapus: {reason}")
                    except Exception: pass
                if self.redirect_channel:
                    try:
                        target = msg.guild.get_channel(self.redirect_channel) or await self.bot.fetch_channel(self.redirect_channel)
                        files = [await a.to_file() for a in images]
                        await target.send(content=f"{user_mention} dipindah ke sini karena {reason}.", files=files)
                    except Exception: pass
                return

            if best_conf >= self.min_conf_redirect and self.redirect_channel:
                try:
                    target = msg.guild.get_channel(self.redirect_channel) or await self.bot.fetch_channel(self.redirect_channel)
                    files = [await a.to_file() for a in images]
                    await target.send(content=f"{msg.author.mention} kontenmu dipindah (uncertain).", files=files)
                except Exception: pass
                return
            # else no action
        except discord.Forbidden:
            return
        except Exception:
            return

async def setup(bot: commands.Bot):
    if bot.get_cog("LuckyPullGuard"): return
    try:
        await bot.add_cog(LuckyPullGuard(bot))
    except Exception:
        pass
