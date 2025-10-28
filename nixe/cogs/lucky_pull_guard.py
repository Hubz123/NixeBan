# -*- coding: utf-8 -*-
from __future__ import annotations
import json, pathlib, logging
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
                                "dm_user_on_delete": False}}

class LuckyPullGuard(commands.Cog):
    """Random-only persona (soft/agro/sharp). Super conservative delete policy.
    Never deletes unless >= min_confidence_delete. <= redirect threshold ⇒ forward only. Below ⇒ ignore.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = _load_cfg().get("lucky_guard", {})
        self.enable = bool(self.cfg.get("enable", True))
        self.guard_channels = {int(x) for x in self.cfg.get("guard_channels", [])}
        self.redirect_channel = int(self.cfg.get("redirect_channel", 0)) or None
        self.min_conf_delete = float(self.cfg.get("min_confidence_delete", 0.85))
        self.min_conf_redirect = float(self.cfg.get("min_confidence_redirect", 0.60))
        self.dm_user_on_delete = bool(self.cfg.get("dm_user_on_delete", False))

    @commands.Cog.listener("on_message")
    async def _on_message(self, msg: discord.Message):
        if not self.enable or msg.author.bot:
            return
        if not msg.attachments:
            return
        if self.guard_channels and msg.channel.id not in self.guard_channels:
            return

        images = [a for a in msg.attachments if (a.content_type or "").startswith("image/")]
        if not images:
            return

        best_conf = 0.0
        for a in images:
            meta = classify_image_meta(filename=a.filename)  # optional gemini hints can be passed by other cogs
            best_conf = max(best_conf, float(meta.get("confidence", 0.0)))

        try:
            if best_conf >= self.min_conf_delete:
                reason = "deteksi lucky pull (random-only)"
                user_mention = msg.author.mention
                channel_name = f"#{msg.channel.name}"
                line = yandere(user=user_mention, channel=channel_name, reason=reason)
                await msg.delete()
                await msg.channel.send(line, delete_after=10)
                if self.dm_user_on_delete:
                    try:
                        await msg.author.send(f"Kontenmu di {channel_name} dihapus: {reason}")
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

            if best_conf >= self.min_conf_redirect and self.redirect_channel:
                try:
                    target = msg.guild.get_channel(self.redirect_channel) or await self.bot.fetch_channel(self.redirect_channel)
                    files = [await a.to_file() for a in images]
                    await target.send(content=f"{msg.author.mention} kontenmu dipindah (uncertain).", files=files)
                except Exception:
                    pass
                return

            # best_conf < redirect threshold ⇒ no action (avoid false positives)
        except discord.Forbidden:
            return
        except Exception:
            return

async def setup(bot: commands.Bot):
    if bot.get_cog("LuckyPullGuard"):
        return
    try:
        await bot.add_cog(LuckyPullGuard(bot))
    except Exception:
        pass
