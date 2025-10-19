# nixe/cogs/banlog_redirect_shim.py
from __future__ import annotations
import logging
from discord.ext import commands
from ..helpers.banlog import get_ban_log_channel as nixe_get, ensure_ban_thread as nixe_ensure

log = logging.getLogger(__name__)

class BanlogRedirectShim(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        try:
            import satpambot.bot.modules.discord_bot.helpers.banlog_thread as leina_banlog  # type: ignore
        except Exception as e:
            log.info("[banlog-redirect] Leina helper not found; using NIXE-only.")
            return
        try:
            leina_banlog.get_log_channel = lambda guild: nixe_get(guild)  # type: ignore
            leina_banlog.ensure_ban_thread = lambda ch: nixe_ensure(ch)   # type: ignore
            log.info("[banlog-redirect] Patched Leina banlog helper -> NIXE config")
        except Exception as e:
            log.warning("[banlog-redirect] Patch failed: %s", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(BanlogRedirectShim(bot))
