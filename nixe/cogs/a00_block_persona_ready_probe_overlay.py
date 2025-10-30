# -*- coding: utf-8 -*-
import logging, asyncio
from discord.ext import commands

log = logging.getLogger("nixe.cogs.a00_block_persona_ready_probe_overlay")

TARGETS = ["nixe.cogs.a00_persona_ready_probe"]

class BlockPersonaReadyProbe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _try_unload(self, mod):
        try:
            res = self.bot.unload_extension(mod)
            if asyncio.iscoroutine(res):
                await res
            log.warning("[persona-block] unloaded extension: %s", mod)
            return True
        except Exception as e:
            log.debug("[persona-block] cannot unload %s: %r", mod, e)
            return False

    @commands.Cog.listener("on_connect")
    async def _on_connect(self):
        # give the loader a brief moment to finish loading all cogs
        await asyncio.sleep(0.2)
        for m in TARGETS:
            await self._try_unload(m)

async def setup(bot):
    await bot.add_cog(BlockPersonaReadyProbe(bot))
