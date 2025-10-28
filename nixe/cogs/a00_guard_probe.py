from __future__ import annotations
import logging
from discord.ext import commands

log = logging.getLogger(__name__)

WATCH_PREFIXES = ("nixe.cogs.gacha", "nixe.cogs.lucky")

class GuardProbe(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _snapshot(self):
        active = [name for name in self.bot.extensions.keys() if name.startswith(WATCH_PREFIXES)]
        return sorted(active)

    @commands.Cog.listener("on_ready")
    async def _on_ready(self):
        active = self._snapshot()
        log.warning("[guard-probe] active guard-like extensions: %s", ", ".join(active) or "<none>")

async def setup(bot: commands.Bot):
    await bot.add_cog(GuardProbe(bot))
