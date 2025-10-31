# nixe/cogs/lpg_whitelist_thread_manager.py
from __future__ import annotations
import logging, os, json
import discord
from discord.ext import commands

log = logging.getLogger("nixe.cogs.lpg_whitelist_thread_manager")

def _cfg() -> dict:
    path = os.getenv("RUNTIME_ENV_PATH") or "nixe/config/runtime_env.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _bool(v, d=True):
    if v is None: return d
    return str(v).strip().lower() in ("1","true","yes","on")

class LPGWhitelistThreadManager(commands.Cog):
    """Ensures a thread for LPG whitelist exists under a parent channel.
    If LPG_NEG_THREAD_ID is provided, it will just verify its existence.
    Otherwise, the cog will create/find by name under LPG_NEG_PARENT_CHANNEL_ID.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = _cfg()
        self.parent_chan_id = int(os.getenv("LPG_NEG_PARENT_CHANNEL_ID") or self.cfg.get("LPG_NEG_PARENT_CHANNEL_ID") or 0)
        self.thread_name = os.getenv("LPG_NEG_THREAD_NAME") or self.cfg.get("LPG_NEG_THREAD_NAME") or "Whitelist LPG (FP)"
        self.thread_id = int(os.getenv("LPG_NEG_THREAD_ID") or self.cfg.get("LPG_NEG_THREAD_ID") or 0)

    async def _ensure_thread(self):
        if self.thread_id:
            th = self.bot.get_channel(self.thread_id) or await self.bot.fetch_channel(self.thread_id)
            if isinstance(th, (discord.Thread,)):
                log.info("[lpg-wl] using existing thread id=%s name=%s", th.id, th.name)
                return
            else:
                log.warning("[lpg-wl] configured thread id not found: %s", self.thread_id)
        if not self.parent_chan_id:
            log.warning("[lpg-wl] LPG_NEG_PARENT_CHANNEL_ID not set; skip ensure.")
            return
        parent = self.bot.get_channel(self.parent_chan_id) or await self.bot.fetch_channel(self.parent_chan_id)
        if not isinstance(parent, (discord.TextChannel,)):
            log.warning("[lpg-wl] parent channel invalid: %s", self.parent_chan_id)
            return
        # Try find by name
        try:
            async for th in parent.threads():
                if str(th.name).lower() == self.thread_name.lower():
                    self.thread_id = th.id
                    log.info("[lpg-wl] found thread id=%s name=%s", th.id, th.name)
                    return
        except Exception:
            pass
        # Create
        try:
            th = await parent.create_thread(name=self.thread_name, auto_archive_duration=10080)  # 7d
            self.thread_id = th.id
            log.warning("[lpg-wl] created whitelist thread id=%s name=%s under parent=%s", th.id, th.name, parent.id)
        except Exception as e:
            log.exception("[lpg-wl] failed to create thread: %r", e)

    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        try:
            await self._ensure_thread()
        except Exception:
            log.exception("[lpg-wl] ensure thread failed at on_ready")

async def setup(bot: commands.Bot):
    await bot.add_cog(LPGWhitelistThreadManager(bot))
