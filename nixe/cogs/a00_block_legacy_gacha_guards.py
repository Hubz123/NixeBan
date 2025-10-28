from __future__ import annotations
import logging
from discord.ext import commands

log = logging.getLogger(__name__)

LEGACY_EXTS = [
    "nixe.cogs.gacha_luck_guard",
    "nixe.cogs.gacha_luck_guard_v1",
    "nixe.cogs.gacha_guard",
    "nixe.cogs.gacha_redirect_guard",
]

class BlockLegacyGachaGuards(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_connect")
    async def _on_connect(self):
        # try to unload legacy extensions if already loaded by autodiscover/loader
        to_unload = [m for m in LEGACY_EXTS if m in self.bot.extensions]
        for m in to_unload:
            try:
                await self.bot.unload_extension(m)
                log.warning("[legacy-guard-block] unloaded extension: %s", m)
            except Exception as e:
                log.warning("[legacy-guard-block] failed to unload %s: %s", m, e)

async def setup(bot: commands.Bot):
    await bot.add_cog(BlockLegacyGachaGuards(bot))
