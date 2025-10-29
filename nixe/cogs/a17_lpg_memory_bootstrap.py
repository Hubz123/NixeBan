from __future__ import annotations
import asyncio
from discord.ext import commands, tasks
from nixe.helpers import lpg_memory as LPM

class LpgMemoryBootstrap(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._load = asyncio.create_task(LPM.load())
        self._save.start()

    @tasks.loop(minutes=5)
    async def _save(self):
        if LPM.S.dirty:
            await LPM.save()

    @_save.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(LpgMemoryBootstrap(bot))
