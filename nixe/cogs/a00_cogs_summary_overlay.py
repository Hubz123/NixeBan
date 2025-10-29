from __future__ import annotations
import os, logging
from discord.ext import commands

log = logging.getLogger(__name__)

class CogsSummaryOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        flag = os.getenv("COGS_DEBUG_LIST", "0").lower() in ("1","true","yes","y","on")
        if not flag:
            return
        try:
            names = sorted(list(self.bot.cogs.keys()))
            log.info("[cogs-summary] loaded=%d names=%s", len(names), names)
        except Exception as e:
            log.warning("[cogs-summary] failed: %r", e)

async def setup(bot):
    await bot.add_cog(CogsSummaryOverlay(bot))
